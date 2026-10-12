"""Prepara configurações locais preservando arquivos, credenciais, bancos e chaves existentes."""

import argparse
import os
import re
import secrets
import subprocess
import sys
from io import StringIO
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values
from dotenv.parser import parse_stream
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "backend"))

from services.data_encryption import (  # noqa: E402
    DataCipher,
    generate_key_file,
    write_private_file,
)

CRITICAL_BINDINGS = {
    "JWT_SECRET_KEY",
    "DATABASE_URI",
    "DATA_ENCRYPTION_KEY_FILE",
    "APP_ENV",
    "DEPLOYMENT_MODE",
    "AUTH_COOKIE_SECURE",
    "AUTH_ALLOWED_ORIGINS",
    "BACKUP_DIRECTORY",
    "VITE_API_URL",
}
SQLITE_NAME = re.compile(r"\.(?:db|sqlite|sqlite3)(?:-wal|-shm|-journal)?$", re.IGNORECASE)


def parse_environment(content):
    bindings = list(parse_stream(StringIO(content)))
    if any(binding.error for binding in bindings):
        raise ValueError("Corrija a sintaxe da configuração existente antes de instalar.")
    seen = set()
    for binding in bindings:
        name = binding.key
        if name in CRITICAL_BINDINGS or (name or "").startswith("PLUGGY_USER_"):
            if name in seen:
                raise ValueError("A configuração contém variáveis críticas repetidas.")
            seen.add(name)
            if "${" in (binding.value or ""):
                raise ValueError("Use valores literais nas variáveis de configuração, sem ${...}.")
    return dotenv_values(stream=StringIO(content), interpolate=False), bindings


def _read_environment(path):
    if not path.is_file():
        raise ValueError("A configuração selecionada precisa ser um arquivo existente.")
    return path.read_bytes().decode("utf-8")


def _resolve_configuration(values, backend):
    secret = values.get("JWT_SECRET_KEY")
    if not secret or len(secret) < 32:
        raise ValueError(
            "Configure uma JWT_SECRET_KEY válida no arquivo existente; ela não será substituída."
        )
    uri = values.get("DATABASE_URI")
    if not uri:
        raise ValueError("Configure DATABASE_URI antes de instalar.")
    try:
        url = make_url(uri)
    except ArgumentError:
        raise ValueError("Corrija DATABASE_URI na configuração existente.") from None
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("A instalação local exige um banco SQLite persistente.")
    if url.query:
        raise ValueError("A instalação local exige um caminho SQLite sem parâmetros especiais.")
    database = Path(url.database)
    if not database.is_absolute():
        database = backend / "instance" / database
    database = database.resolve()
    key_value = values.get("DATA_ENCRYPTION_KEY_FILE")
    key = Path(key_value) if key_value else backend / ".secrets/financial-data-keys.json"
    if not key.is_absolute():
        # Os comandos Flask são executados pelo instalador com cwd=backend.
        key = backend / key
    key = key.resolve()
    backup_value = values.get("BACKUP_DIRECTORY")
    backups = Path(backup_value) if backup_value else backend / "backups"
    if not backups.is_absolute():
        backups = backend / backups
    environment = values.get("APP_ENV", "development")
    mode = values.get("DEPLOYMENT_MODE", "native")
    secure = values.get("AUTH_COOKIE_SECURE", "true")
    if environment not in {"development", "production"} or mode not in {"native", "docker"}:
        raise ValueError("Corrija APP_ENV e DEPLOYMENT_MODE na configuração existente.")
    if secure is None or secure.lower() not in {"true", "false"}:
        raise ValueError("AUTH_COOKIE_SECURE deve ser true ou false.")
    if environment == "production":
        origins = [
            origin.strip().rstrip("/")
            for origin in (values.get("AUTH_ALLOWED_ORIGINS") or "").split(",")
            if origin.strip()
        ]
        parsed = [urlsplit(origin) for origin in origins]
        if (
            secure.lower() != "true"
            or not origins
            or any(
                origin.scheme != "https"
                or not origin.hostname
                or origin.hostname.startswith(".")
                or origin.username
                or origin.password
                or origin.path
                or origin.query
                or origin.fragment
                or "*" in origin.netloc
                for origin in parsed
            )
        ):
            raise ValueError("Produção exige cookies Secure e origens HTTPS exatas.")
        if (
            not Path(url.database).is_absolute()
            or not key_value
            or not Path(key_value).is_absolute()
            or not backup_value
            or not Path(backup_value).is_absolute()
        ):
            raise ValueError("Produção exige caminhos explícitos e absolutos para banco e chaves.")
    return database, key, backups.resolve()


def _existing_state(project, database=None, backups=None):
    if database is not None and any(
        Path(str(database) + suffix).exists() for suffix in ("", "-wal", "-shm", "-journal")
    ):
        return True
    backend = project / "backend"
    for directory in (backend, backend / "instance"):
        if directory.is_dir():
            paths = directory.iterdir() if directory == backend else directory.rglob("*")
            if any(path.is_file() and SQLITE_NAME.search(path.name) for path in paths):
                return True
    directories = {backend / "backups", project / "backups"}
    if backups is not None:
        directories.add(backups)
    return any(
        directory.is_dir()
        and any(
            path.is_file()
            and (
                path.suffix.lower() in {".fhbackup", ".backup", ".bak"}
                or SQLITE_NAME.search(path.name)
            )
            for path in directory.rglob("*")
        )
        for directory in directories
    )


def configure(project=PROJECT, environment_file=None, local=False):
    """Retorna a configuração efetiva para FINANCEHUB_ENV_FILE dos comandos seguintes."""
    project = Path(project).resolve()
    backend = project / "backend"
    frontend = project / "frontend"
    explicit = environment_file or os.getenv("FINANCEHUB_ENV_FILE")
    target = Path(explicit).resolve() if explicit else backend / ".env"
    existing = target.exists()
    if explicit and not existing:
        raise ValueError(
            "Restaure o FINANCEHUB_ENV_FILE selecionado; não haverá configuração local."
        )
    if not existing and _existing_state(project):
        raise ValueError(
            "Restaure o .env original antes de instalar: há banco ou backup existente."
        )
    source = target if existing else backend / ".env.example"
    content = _read_environment(source)
    values, bindings = parse_environment(content)
    if not existing:
        values["JWT_SECRET_KEY"] = secrets.token_hex(32)
        values["DATA_ENCRYPTION_KEY_FILE"] = str(
            (backend / ".secrets/financial-data-keys.json").resolve()
        )
        generated = {"JWT_SECRET_KEY", "DATA_ENCRYPTION_KEY_FILE"}
        content = "".join(
            binding.original.string for binding in bindings if binding.key not in generated
        )
        if content and not content.endswith("\n"):
            content += "\n"
        for name in sorted(generated):
            value = values[name].replace("\\", "\\\\").replace("'", "\\'")
            content += f"{name}='{value}'\n"
    database, key, backups = _resolve_configuration(values, backend)
    if local:
        origins = {
            value.strip().rstrip("/")
            for value in values.get(
                "AUTH_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if value.strip()
        }
        if (
            values.get("APP_ENV", "development") != "development"
            or values.get("DEPLOYMENT_MODE", "native") != "native"
            or values.get("AUTH_COOKIE_SECURE", "true").lower() != "false"
            or not origins
            or not origins.issubset({"http://localhost:5173", "http://127.0.0.1:5173"})
        ):
            raise ValueError(
                "O instalador local exige desenvolvimento, cookies HTTP e origens localhost:5173. "
                "Para produção, use production ou o guia de atualização."
            )
    if not existing and _existing_state(project, database, backups):
        raise ValueError(
            "Restaure o .env original antes de instalar: há banco ou backup existente."
        )
    if key.exists():
        DataCipher.from_key_file(key)
    elif explicit or _existing_state(project, database, backups):
        raise ValueError(
            "Restaure o arquivo original de chaves; uma chave nova não recupera dados existentes."
        )
    frontend_target = frontend / ".env"
    frontend_source = frontend_target if frontend_target.exists() else frontend / ".env.example"
    frontend_content = _read_environment(frontend_source)
    parse_environment(frontend_content)
    # Só começa a escrever depois de validar as duas configurações e as chaves existentes.
    if not key.exists():
        key.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        generate_key_file(key)
    if not existing:
        write_private_file(target, content.encode("utf-8"))
    if not frontend_target.exists():
        write_private_file(frontend_target, frontend_content.encode("utf-8"))
    return target.resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=PROJECT)
    parser.add_argument("--env-file")
    parser.add_argument("--local", action="store_true")
    args = parser.parse_args()
    try:
        configure(args.project, args.env_file, local=args.local)
    except ValueError as error:
        parser.exit(1, f"Configuração não concluída: {error}\n")
    except (OSError, RuntimeError, TypeError, subprocess.SubprocessError):
        parser.exit(
            1,
            "Configuração falhou. Confira sintaxe, JWT, caminhos e arquivos originais; "
            "não substitua chaves perdidas nem apague bancos existentes.\n",
        )
    print("Configuração validada; arquivos existentes e chaves foram preservados.")


if __name__ == "__main__":
    main()
