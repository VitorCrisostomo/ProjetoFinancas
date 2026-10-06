"""Snapshots SQLite consistentes, configuração criptografada e retenção verificável."""

import base64
import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import click
from flask import current_app

from config import db
from exceptions.api_errors import APIError
from services.data_encryption import get_data_cipher, write_private_file
from services.database_encryption_service import _migrate_tables
from services.pluggy_credentials import PluggyCredentialsStore

BACKUP_CONTEXT = {"purpose": "production-backup", "format": 1}
BACKUP_NAME = re.compile(r"^scheduled-\d{8}T\d{12}Z-[a-f0-9]{32}\.fhbackup$")
MAX_DATABASE_BYTES = 512 * 1024 * 1024


def _validate_snapshot(snapshot, revoke_sessions=False):
    if snapshot[:16] != b"SQLite format 3\x00" or len(snapshot) > MAX_DATABASE_BYTES:
        raise RuntimeError("O snapshot SQLite não é válido ou excede o limite de tamanho.")
    # A API backup inclui os dados confirmados no WAL, mas serialize conserva seu
    # cabeçalho. Um snapshot independente não usa arquivos WAL e precisa do modo
    # rollback para deserialize conseguir abri-lo em memória.
    if snapshot[18:20] == b"\x02\x02":
        snapshot = snapshot[:18] + b"\x01\x01" + snapshot[20:]
    with closing(sqlite3.connect(":memory:", isolation_level=None)) as connection:
        connection.deserialize(snapshot)
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("O snapshot não passou na verificação de integridade.")
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise RuntimeError("O snapshot contém vínculos inconsistentes.")
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN")
        # Valida todos os payloads e vínculos; backups periódicos nunca migram a origem.
        _counts, changed = _migrate_tables(connection)
        if changed:
            raise RuntimeError("Migre o banco offline antes de criar backups de produção.")
        if revoke_sessions:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='auth_sessions'"
            ).fetchone()
            if exists:
                connection.execute("UPDATE auth_sessions SET revoked=1")
        connection.execute("COMMIT")
        return connection.serialize()


def _read_backup(path):
    path = Path(path)
    if path.stat().st_size > MAX_DATABASE_BYTES * 3:
        raise RuntimeError("Backup acima do limite de restauração em memória.")
    plaintext = get_data_cipher().decrypt(path.read_text(encoding="ascii"), BACKUP_CONTEXT)
    document = json.loads(plaintext)
    if (
        not isinstance(document, dict)
        or document.get("format") != 1
        or not isinstance(document.get("environment"), str)
        or not isinstance(document.get("database"), str)
        or not isinstance(document.get("created_at"), str)
    ):
        raise RuntimeError("Formato de backup não suportado.")
    try:
        created_at = datetime.fromisoformat(document["created_at"])
        if created_at.utcoffset() is None:
            raise ValueError
        created_at = created_at.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise RuntimeError("O backup precisa conter uma data de criação válida com fuso.") from None
    snapshot = base64.b64decode(document["database"], validate=True)
    if len(snapshot) > MAX_DATABASE_BYTES:
        raise RuntimeError("Banco acima do limite de restauração em memória.")
    snapshot = _validate_snapshot(snapshot)
    return snapshot, document["environment"], created_at


def read_backup(path):
    snapshot, environment, _created_at = _read_backup(path)
    return snapshot, environment


def create_backup(directory=None, keep=30):
    """A configuração é bloqueada antes do banco, como nos comandos administrativos."""
    if keep < 1:
        raise ValueError("A retenção precisa preservar pelo menos um backup.")
    if db.engine.dialect.name != "sqlite" or db.engine.url.database in (None, "", ":memory:"):
        raise RuntimeError("Backups periódicos exigem SQLite em arquivo.")
    database = Path(db.engine.url.database).resolve()
    if not database.is_file():
        raise RuntimeError("O banco configurado não existe; inicialize-o antes do backup.")
    root = Path(directory or current_app.config["BACKUP_DIRECTORY"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with PluggyCredentialsStore().snapshot() as environment:
        if not environment:
            raise RuntimeError("O arquivo de configuração precisa existir para o backup.")
        with closing(
            sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=30)
        ) as source:
            size = (
                source.execute("PRAGMA page_count").fetchone()[0]
                * source.execute("PRAGMA page_size").fetchone()[0]
            )
            if size > MAX_DATABASE_BYTES:
                raise RuntimeError("Bancos acima de 512 MiB precisam de backup em lotes.")
            with closing(sqlite3.connect(":memory:")) as destination:
                source.backup(destination)
                snapshot = destination.serialize()
        snapshot = _validate_snapshot(snapshot)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = root / f"scheduled-{timestamp}-{uuid4().hex}.fhbackup"
        temporary = root / f".{uuid4().hex}.tmp"
        document = json.dumps(
            {
                "format": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "database": base64.b64encode(snapshot).decode("ascii"),
                "environment": environment,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        envelope = get_data_cipher().encrypt(document, BACKUP_CONTEXT)
        try:
            write_private_file(temporary, envelope.encode("ascii"))
            stored_snapshot, stored_environment = read_backup(temporary)
            if snapshot != stored_snapshot or environment != stored_environment:
                raise RuntimeError("O backup gravado não corresponde ao snapshot.")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    # Só remove backups desta rotina depois de confirmar a recuperação do novo arquivo.
    owned = sorted(
        entry
        for entry in root.iterdir()
        if entry.is_file() and not entry.is_symlink() and BACKUP_NAME.fullmatch(entry.name)
    )
    for expired in owned[:-keep]:
        expired.unlink()
    return path


def restore_backup(path, output_directory):
    """Recupera para uma pasta nova; nunca sobrescreve o banco ou as chaves atuais."""
    destination = Path(output_directory).resolve()
    if destination.exists():
        raise RuntimeError("Escolha uma pasta de restauração que ainda não exista.")
    snapshot, environment = read_backup(path)
    snapshot = _validate_snapshot(snapshot, revoke_sessions=True)
    destination.mkdir(parents=True)
    try:
        write_private_file(destination / "financehub.db", snapshot)
        write_private_file(destination / "app.env", environment.encode("utf-8"))
    except Exception:
        # Uma saída parcial nunca é apresentada como restauração concluída.
        raise RuntimeError(
            "Restauração incompleta; preserve a origem e use uma nova pasta."
        ) from None
    return destination


def check_backup(directory=None, max_age_hours=26):
    root = Path(directory or current_app.config["BACKUP_DIRECTORY"]).resolve()
    owned = sorted(
        entry
        for entry in root.glob("scheduled-*.fhbackup")
        if entry.is_file() and not entry.is_symlink() and BACKUP_NAME.fullmatch(entry.name)
    )
    if not owned:
        raise RuntimeError("Nenhum backup periódico encontrado.")
    latest = owned[-1]
    timestamp = datetime.strptime(latest.name.split("-")[1], "%Y%m%dT%H%M%S%fZ").replace(
        tzinfo=timezone.utc
    )
    now = datetime.now(timezone.utc)
    age = (now - timestamp).total_seconds() / 3600
    if age < 0 or age > max_age_hours:
        raise RuntimeError("O backup periódico está atrasado; confira o agendamento.")
    _snapshot, _environment, created_at = _read_backup(latest)
    # O nome auxilia a retenção, mas pode ser renomeado. A idade do conteúdo
    # criptografado também precisa estar dentro da janela do agendamento.
    authenticated_age = (now - created_at).total_seconds() / 3600
    if authenticated_age < 0 or authenticated_age > max_age_hours:
        raise RuntimeError("O backup periódico está atrasado; confira o agendamento.")
    return latest


def register_backup_commands(app):
    def safely(action):
        try:
            return action()
        except (OSError, RuntimeError, ValueError, KeyError, sqlite3.Error, APIError):
            # Não imprime conteúdo de configuração ou de registros em mensagens de falha.
            raise click.ClickException(
                "Operação de backup falhou. Confira arquivo de chaves, configuração, "
                "esquema, espaço em disco, permissões e idade do backup."
            ) from None

    @app.cli.command("backup-data")
    @click.option("--keep", default=30, type=click.IntRange(min=1), show_default=True)
    def backup_data_command(keep):
        path = safely(lambda: create_backup(keep=keep))
        click.echo(f"Backup criptografado e recuperação verificada: {path.name}")

    @app.cli.command("verify-backup")
    @click.option("--max-age-hours", default=26, type=click.IntRange(min=1))
    def verify_backup_command(max_age_hours):
        safely(lambda: check_backup(max_age_hours=max_age_hours))
        click.echo("Backup recente e recuperação verificável.")

    @app.cli.command("restore-production-backup")
    @click.option("--backup", required=True, type=click.Path(exists=True, dir_okay=False))
    @click.option("--output-dir", required=True, type=click.Path(file_okay=False))
    def restore_production_backup_command(backup, output_dir):
        safely(lambda: restore_backup(backup, output_dir))
        click.echo("Banco e configuração recuperados em pasta nova; sessões antigas revogadas.")
