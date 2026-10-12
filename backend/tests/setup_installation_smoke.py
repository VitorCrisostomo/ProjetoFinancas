"""Validação opcional da instalação real em uma cópia temporária, sem dados do checkout."""

import os
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT = Path(__file__).resolve().parents[2]


def main():
    with TemporaryDirectory(prefix="financehub-setup-smoke-") as directory:
        project = Path(directory) / "app"
        project.mkdir()
        (project / "backend").mkdir()
        (project / "frontend").mkdir()
        (project / "deploy").mkdir()
        for name in ("requirements.txt",):
            shutil.copyfile(PROJECT / name, project / name)
        for name in (
            "config.py",
            "main.py",
            "server.py",
            ".env.example",
            "requirements-production.txt",
            "requirements-dev.txt",
        ):
            shutil.copyfile(PROJECT / "backend" / name, project / "backend" / name)
        for name in ("exceptions", "models", "repositories", "routes", "services"):
            shutil.copytree(
                PROJECT / "backend" / name,
                project / "backend" / name,
                ignore=lambda source, names: [name for name in names if not name.endswith(".py")],
            )
        for name in ("setup.py", "configure_local.py", "run_local.py"):
            shutil.copyfile(PROJECT / "deploy" / name, project / "deploy" / name)
        shutil.copyfile(PROJECT / "frontend/.env.example", project / "frontend/.env.example")
        environment = os.environ.copy()
        for name in (
            "FINANCEHUB_ENV_FILE",
            "FINANCEHUB_FILE_ACCESS_SID",
            "PYTHONPATH",
            "PYTHONHOME",
        ):
            environment.pop(name, None)
        command = [
            sys.executable,
            "-B",
            str(project / "deploy/setup.py"),
            "install",
            "--skip-frontend",
            "--runtime-only",
        ]
        subprocess.run(command, cwd=project, env=environment, check=True)
        environment_file = project / "backend/.env"
        key = project / "backend/.secrets/financial-data-keys.json"
        from dotenv import dotenv_values

        values = dotenv_values(environment_file, interpolate=False)
        database = project / "backend/instance/financehub.db"
        assert len(values["JWT_SECRET_KEY"]) >= 64
        assert key.is_file() and database.is_file()
        original_environment = environment_file.read_bytes()
        original_key = key.read_bytes()
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("CREATE TABLE setup_fixture (marker TEXT)")
            connection.execute("INSERT INTO setup_fixture VALUES ('preservado')")
            connection.commit()
        subprocess.run(command, cwd=project, env=environment, check=True)
        assert environment_file.read_bytes() == original_environment
        assert key.read_bytes() == original_key
        with closing(sqlite3.connect(database)) as connection:
            assert connection.execute("SELECT marker FROM setup_fixture").fetchone() == (
                "preservado",
            )
        print(
            "Instalação real e repetição verificadas em cópia temporária; configurações, chave e dados preservados."
        )


if __name__ == "__main__":
    main()
