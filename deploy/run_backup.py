"""Entrada portável para Agendador de Tarefas, systemd timer ou contêiner."""

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def copy_external(source, directory):
    from services.backup_service import BACKUP_NAME

    directory = Path(directory).resolve(strict=True)
    if not directory.is_dir() or directory == source.parent.resolve():
        raise ValueError("O destino externo precisa ser uma pasta disponível e distinta.")
    destination = directory / source.name

    def digest(path):
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").digest()

    if destination.exists():
        if destination.is_symlink() or digest(source) != digest(destination):
            raise RuntimeError("A cópia externa existente não corresponde ao backup.")
    else:
        temporary = directory / f".{uuid4().hex}.tmp"
        try:
            shutil.copyfile(source, temporary)
            if digest(source) != digest(temporary):
                raise RuntimeError("A cópia externa não passou na verificação.")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    owned = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and not path.is_symlink() and BACKUP_NAME.fullmatch(path.name)
    )
    for expired in owned[:-90]:
        expired.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--external-directory")
    args = parser.parse_args()
    root = Path(args.state_dir).resolve()
    os.environ["FINANCEHUB_ENV_FILE"] = str(root / "config/app.env")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    status = {"checked_at": datetime.now(timezone.utc).isoformat(), "success": False}
    try:
        from main import app
        from services.backup_service import check_backup, create_backup
        from services.data_encryption import write_private_file

        with app.app_context():
            path = create_backup(keep=30)
            check_backup()
            if args.external_directory:
                copy_external(path, args.external_directory)
            status.update(success=True, external_copy=bool(args.external_directory))
    except Exception:
        # Logs operacionais não recebem registros financeiros nem valores de configuração.
        print(
            "Backup falhou; confira permissões, chave, espaço e disponibilidade do destino.",
            file=sys.stderr,
        )
    try:
        from services.data_encryption import write_private_file

        target = root / "logs/backup-status.json"
        temporary = target.with_name(f".{uuid4().hex}.tmp")
        try:
            write_private_file(temporary, json.dumps(status).encode("utf-8"))
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    except Exception:
        status["success"] = False
        print("Não foi possível registrar o estado do backup.", file=sys.stderr)
    return 0 if status["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
