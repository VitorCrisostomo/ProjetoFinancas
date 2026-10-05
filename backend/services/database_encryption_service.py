"""Migração SQLite offline, backup criptografado e verificação dos registros."""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import click
from flask import current_app
from sqlalchemy import inspect

from config import db
from models.account import Account
from models.transaction import Transaction
from services.data_encryption import DataEncryptionError, get_data_cipher, write_private_file

FINANCIAL_MODELS = {"accounts": Account, "transactions": Transaction}
BACKUP_CONTEXT = {"purpose": "sqlite-backup", "format": 1}


def ensure_encrypted_schema():
    """Não aceita iniciar a versão nova sobre tabelas financeiras antigas."""
    inspector = inspect(db.engine)
    for table, model in FINANCIAL_MODELS.items():
        if not inspector.has_table(table):
            continue
        columns = {column["name"] for column in inspector.get_columns(table)}
        if columns != {column.name for column in model.__table__.columns}:
            raise RuntimeError(
                "O banco precisa da migração de criptografia. Com a aplicação parada, "
                "execute: python -m flask --app main encrypt-data"
            )


def _fingerprint(row, fields):
    document = json.dumps(
        {"metadata": row, "fields": fields},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(document).digest()


def _encode_legacy_row(model, raw):
    bindings = {name: raw[name] for name in model._binding_fields}
    bindings["id"] = raw["id"]
    record = model(**bindings)
    for name, default in model._defaults.items():
        value = raw.get(name, default)
        if name == "date" and isinstance(value, str):
            value = datetime.fromisoformat(value)
        if name in model._json_fields and isinstance(value, str):
            value = json.loads(value)
        setattr(record, name, value)
    record.encrypt_for_storage()
    row = {column.name: getattr(record, column.name) for column in model.__table__.columns}
    # Usa apenas metadados de vínculo; contextos aleatórios não mudam o conteúdo histórico.
    fingerprint = _fingerprint(bindings, record._financial_fields())
    return row, fingerprint


def _decode_stored_row(model, row):
    record = model(**dict(row))
    fields = record._financial_fields()
    bindings = {name: row[name] for name in model._binding_fields}
    bindings["id"] = row["id"]
    return _fingerprint(bindings, fields)


def _table_columns(connection, table):
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _create_replacement_table(connection, table):
    if table == "accounts":
        connection.execute("""
            CREATE TABLE accounts__encrypted (
                id VARCHAR(36) PRIMARY KEY NOT NULL,
                user_id INTEGER NOT NULL REFERENCES users(id),
                itemId VARCHAR(36) NOT NULL,
                encrypted_data TEXT NOT NULL,
                encryption_context VARCHAR(36) NOT NULL UNIQUE
            )
        """)
    else:
        connection.execute("""
            CREATE TABLE transactions__encrypted (
                id INTEGER PRIMARY KEY NOT NULL,
                external_id VARCHAR(100) UNIQUE,
                account_id VARCHAR(36) REFERENCES accounts(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                encrypted_data TEXT NOT NULL,
                encryption_context VARCHAR(36) NOT NULL UNIQUE
            )
        """)


def _migrate_tables(connection):
    connection.row_factory = sqlite3.Row
    tables = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    changed = []
    counts = {}
    baseline_foreign_keys = {tuple(row) for row in connection.execute("PRAGMA foreign_key_check")}
    for table, model in FINANCIAL_MODELS.items():
        if table not in tables:
            counts[table] = 0
            continue
        columns = _table_columns(connection, table)
        expected_columns = {column.name for column in model.__table__.columns}
        rows = connection.execute(f'SELECT * FROM "{table}"').fetchall()
        counts[table] = len(rows)
        if "encrypted_data" in columns:
            if columns != expected_columns:
                raise RuntimeError("O banco contém uma estrutura financeira não suportada.")
            for row in rows:
                _decode_stored_row(model, row)
            continue
        expected_legacy = {"id", *model._binding_fields, *model._defaults}
        if table == "transactions":
            expected_legacy.discard("subcategory")  # A coluna era opcional nas versões antigas.
        if not expected_legacy.issubset(columns) or columns - (expected_legacy | {"subcategory"}):
            raise RuntimeError(
                "A estrutura financeira antiga precisa de revisão antes da migração."
            )
        custom_objects = connection.execute(
            "SELECT name FROM sqlite_master WHERE tbl_name=? AND type IN ('trigger', 'index') "
            "AND sql IS NOT NULL",
            (table,),
        ).fetchall()
        if custom_objects:
            raise RuntimeError(
                "Há índices ou gatilhos personalizados; revise-os antes da migração."
            )
        dependent_views = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='view'"
        ).fetchall()
        if any(table in (row[0] or "").lower() for row in dependent_views):
            raise RuntimeError("Há views financeiras personalizadas; revise-as antes da migração.")
        _create_replacement_table(connection, table)
        fingerprints = {}
        for legacy in rows:
            encrypted, fingerprint = _encode_legacy_row(model, dict(legacy))
            names = tuple(encrypted)
            quoted = ", ".join(f'"{name}"' for name in names)
            parameters = ", ".join("?" for _ in names)
            connection.execute(
                f'INSERT INTO "{table}__encrypted" ({quoted}) VALUES ({parameters})',
                tuple(encrypted[name] for name in names),
            )
            fingerprints[encrypted["id"]] = fingerprint
        stored = connection.execute(f'SELECT * FROM "{table}__encrypted"').fetchall()
        if len(stored) != len(rows) or any(
            _decode_stored_row(model, row) != fingerprints[row["id"]] for row in stored
        ):
            raise RuntimeError("A verificação dos dados migrados falhou; nada foi confirmado.")
        changed.append(table)
    # Filhos são substituídos antes do pai; nenhuma tabela de usuários/proteção é removida.
    for table in ("transactions", "accounts"):
        if table in changed:
            connection.execute(f'DROP TABLE "{table}"')
    for table in ("accounts", "transactions"):
        if table in changed:
            connection.execute(f'ALTER TABLE "{table}__encrypted" RENAME TO "{table}"')
            connection.execute(f'CREATE INDEX "ix_{table}_user_id" ON "{table}" (user_id)')
    if not {tuple(row) for row in connection.execute("PRAGMA foreign_key_check")}.issubset(
        baseline_foreign_keys
    ):
        raise RuntimeError("A migração alterou vínculos do banco; nada foi confirmado.")
    return counts, bool(changed)


def read_encrypted_backup(path):
    return get_data_cipher().decrypt(Path(path).read_text(encoding="ascii"), BACKUP_CONTEXT)


def encrypt_database(backup_directory):
    """Exige manutenção offline; nenhum backup em claro é escrito em disco."""
    if db.engine.dialect.name != "sqlite":
        raise RuntimeError("A migração automática foi preparada para SQLite.")
    if db.engine.url.database in (None, "", ":memory:"):
        raise RuntimeError("Informe um banco SQLite em arquivo para a migração.")
    database_path = Path(db.engine.url.database).resolve()
    if not database_path.is_file():
        raise RuntimeError("O banco configurado não foi encontrado.")
    if database_path.stat().st_size > 512 * 1024 * 1024:
        raise RuntimeError("Bancos acima de 512 MiB precisam de migração em lotes.")
    db.session.remove()
    db.engine.dispose()
    connection = sqlite3.connect(database_path, timeout=5, isolation_level=None)
    backup_path = None
    confirmed = False
    try:
        # Não deixa um WAL antigo contendo páginas financeiras em claro.
        checkpoint = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if checkpoint and checkpoint[0]:
            raise RuntimeError("O banco está em uso. Pare a aplicação antes de migrar.")
        mode = connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
        if mode.lower() != "delete":
            raise RuntimeError("Não foi possível retirar o banco do modo WAL.")
        connection.execute("PRAGMA secure_delete=ON")
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN EXCLUSIVE")
        tables = [table for table in FINANCIAL_MODELS if _table_columns(connection, table)]
        legacy = any("encrypted_data" not in _table_columns(connection, table) for table in tables)
        if legacy:
            snapshot = connection.serialize()
            envelope = get_data_cipher().encrypt(snapshot, BACKUP_CONTEXT)
            if get_data_cipher().decrypt(envelope, BACKUP_CONTEXT) != snapshot:
                raise RuntimeError("Não foi possível verificar o backup.")
            backup_path = write_private_file(
                Path(backup_directory) / f"before-encryption-{uuid4().hex}.fhbackup",
                envelope.encode("ascii"),
            )
        counts, changed = _migrate_tables(connection)
        connection.execute("COMMIT")
        confirmed = True
        # secure_delete apaga páginas descartadas; VACUUM remove espaço livre e resíduos.
        connection.execute("VACUUM")
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("A verificação física do banco falhou; preserve o backup.")
        return {"counts": counts, "changed": changed, "backup": backup_path}
    except Exception as error:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        if confirmed:
            raise RuntimeError(
                "Os dados foram convertidos, mas a limpeza ou verificação final falhou. "
                "Preserve o backup e execute encrypt-data novamente com a aplicação parada."
            ) from error
        raise
    finally:
        connection.close()
        db.engine.dispose()


def verify_encrypted_database():
    ensure_encrypted_schema()
    counts = {}
    for table, model in FINANCIAL_MODELS.items():
        if not inspect(db.engine).has_table(table):
            counts[table] = 0
            continue
        rows = db.session.execute(model.__table__.select()).mappings().all()
        for row in rows:
            _decode_stored_row(model, row)
        counts[table] = len(rows)
    return counts


def restore_encrypted_backup(backup_path, output_path):
    """Restaura para um arquivo novo, já com as tabelas financeiras criptografadas."""
    connection = sqlite3.connect(":memory:", isolation_level=None)
    try:
        connection.deserialize(read_encrypted_backup(backup_path))
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("PRAGMA secure_delete=ON")
        connection.execute("BEGIN EXCLUSIVE")
        _migrate_tables(connection)
        connection.execute("COMMIT")
        connection.execute("VACUUM")
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("O backup não passou na verificação de integridade.")
        return write_private_file(output_path, connection.serialize())
    finally:
        connection.close()


def register_encryption_commands(app):
    @app.cli.command("encrypt-data")
    def encrypt_data_command():
        """Migra contas e transações com a aplicação parada."""
        try:
            result = encrypt_database(Path(current_app.root_path) / "backups")
        except (RuntimeError, sqlite3.Error, DataEncryptionError, ValueError) as error:
            raise click.ClickException(str(error)) from error
        if result["backup"]:
            click.echo(f"Backup criptografado: {result['backup']}")
        click.echo(
            "Migração verificada."
            if result["changed"]
            else "Dados já criptografados e verificados."
        )

    @app.cli.command("verify-encrypted-data")
    def verify_encrypted_data_command():
        try:
            counts = verify_encrypted_database()
        except (RuntimeError, DataEncryptionError) as error:
            raise click.ClickException(str(error)) from error
        click.echo(
            f"Verificados: {counts['transactions']} transações e {counts['accounts']} contas."
        )

    @app.cli.command("restore-encrypted-backup")
    @click.option("--backup", required=True, type=click.Path(exists=True, dir_okay=False))
    @click.option("--output", required=True, type=click.Path(dir_okay=False))
    def restore_backup_command(backup, output):
        try:
            restore_encrypted_backup(backup, output)
        except (OSError, RuntimeError, sqlite3.Error, DataEncryptionError) as error:
            raise click.ClickException(str(error)) from error
        click.echo("Backup restaurado em um arquivo novo, com dados financeiros criptografados.")
