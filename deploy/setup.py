"""Instalação e manutenção compartilhadas por setup.bat e Makefile."""

import argparse
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import venv
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit

PROJECT = Path(__file__).resolve().parents[1]
VENV = PROJECT / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
FRONTEND = PROJECT / "frontend"


def run(arguments, cwd=PROJECT, environment=None):
    if environment is None:
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
    subprocess.run([str(value) for value in arguments], cwd=cwd, env=environment, check=True)


def require_python():
    if sys.version_info < (3, 11):
        raise ValueError("Instale Python 3.11 ou superior.")
    with closing(sqlite3.connect(":memory:")) as connection:
        if not callable(getattr(connection, "serialize", None)):
            raise ValueError("Este Python precisa incluir SQLite com suporte a serialize().")


def npm():
    executable = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    node = shutil.which("node")
    if not executable or not node:
        raise ValueError("Instale Node.js 22.12 ou superior, com npm, para compilar a interface.")
    version = subprocess.check_output([node, "--version"], text=True).strip()
    major, minor, *_ = (int(part) for part in version.lstrip("v").split("."))
    if major < 22 or (major == 22 and minor < 12):
        raise ValueError("Atualize o Node.js para 22.12 ou superior.")
    return executable


def install_runtime(development=True):
    require_python()
    if not PYTHON.is_file():
        if VENV.exists():
            raise ValueError(
                "A pasta .venv está incompleta. Preserve-a e confira seu ambiente Python."
            )
        print("Criando ambiente Python isolado...", flush=True)
        venv.EnvBuilder(with_pip=True).create(VENV)
    requirements = (
        PROJECT
        / "backend"
        / ("requirements-dev.txt" if development else "requirements-production.txt")
    )
    print("Instalando as dependências Python do projeto...", flush=True)
    run(
        [
            PYTHON,
            "-B",
            "-c",
            "import sqlite3, sys; "
            "assert sys.version_info >= (3, 11), 'A .venv exige Python 3.11 ou superior'; "
            "connection = sqlite3.connect(':memory:'); "
            "assert callable(getattr(connection, 'serialize', None)), 'SQLite precisa oferecer serialize()'; "
            "connection.close()",
        ]
    )
    run([PYTHON, "-m", "pip", "install", "-r", requirements])
    run([PYTHON, "-m", "pip", "check"])


def require_runtime():
    if not PYTHON.is_file():
        raise ValueError("Execute primeiro setup.bat ou python3 deploy/setup.py install.")


def configure(environment_file=None, local=False):
    require_runtime()
    arguments = [PYTHON, "-B", PROJECT / "deploy/configure_local.py"]
    selected = environment_file or os.getenv("FINANCEHUB_ENV_FILE")
    if selected:
        selected = Path(selected).resolve()
        arguments.extend(["--env-file", selected])
    if local:
        arguments.append("--local")
    run(arguments)
    return Path(selected or PROJECT / "backend/.env").resolve()


def app_environment(environment_file):
    environment = os.environ.copy()
    for name in (
        "APP_ENV",
        "DEPLOYMENT_MODE",
        "JWT_SECRET_KEY",
        "DATABASE_URI",
        "DATA_ENCRYPTION_KEY_FILE",
        "BACKUP_DIRECTORY",
        "AUTH_COOKIE_SECURE",
        "AUTH_ALLOWED_ORIGINS",
        "SERVER_HOST",
        "SERVER_PORT",
        "TRUSTED_PROXY",
    ):
        environment.pop(name, None)
    environment["FINANCEHUB_ENV_FILE"] = str(environment_file)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    return environment


def flask(arguments, environment_file):
    run(
        [PYTHON, "-B", "-m", "flask", "--app", "main", *arguments],
        cwd=PROJECT / "backend",
        environment=app_environment(environment_file),
    )


def initialize(environment_file):
    # Conferir antes de init-db impede migrações com uma chave incompatível.
    flask(["verify-encrypted-data"], environment_file)
    flask(["init-db"], environment_file)
    flask(["verify-encrypted-data"], environment_file)


def build(install=False):
    executable = npm()
    if install:
        print("Instalando o frontend a partir das versões registradas...", flush=True)
        run([executable, "ci"], cwd=FRONTEND)
    environment = os.environ.copy()
    environment["VITE_API_URL"] = "/api"
    print("Compilando a interface...", flush=True)
    run([executable, "run", "build"], cwd=FRONTEND, environment=environment)


def production(args):
    if os.name != "nt":
        raise ValueError("Para produção no Linux, use make docker-setup ou deploy/docker/setup.sh.")
    root = Path(args.state_dir).resolve()
    origin = urlsplit(args.origin)
    if (
        origin.scheme != "https"
        or not origin.hostname
        or not origin.hostname.endswith(".ts.net")
        or not re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+ts\.net", origin.hostname)
        or origin.hostname == "servidor.sua-tailnet.ts.net"
        or origin.username
        or origin.password
        or origin.port
        or origin.path
        or origin.query
        or origin.fragment
        or "*" in origin.netloc
        or origin.hostname.startswith(".")
    ):
        raise ValueError(
            "Informe https:// seguido do hostname real *.ts.net, sem porta ou caminho."
        )
    if root == PROJECT or PROJECT in root.parents or root in PROJECT.parents:
        raise ValueError("Escolha uma pasta de estado dedicada, fora do checkout.")
    args.origin = "https://" + origin.hostname
    sources = [
        Path(value).resolve() if value else None
        for value in (args.source_env, args.source_key, args.source_database)
    ]
    for name in ("winsw", "caddy", "external_backups"):
        value = getattr(args, name)
        if value:
            setattr(args, name, str(Path(value).resolve()))
    if args.fresh and any(sources):
        raise ValueError("Escolha --fresh ou os três arquivos da instalação a importar.")
    if root.exists():
        raise ValueError("Estado já existente: use o guia de atualização; o setup não o substitui.")
    if not args.fresh and not all(sources):
        raise ValueError(
            "Escolha --fresh ou informe --source-env, --source-key e --source-database."
        )
    if any(sources) and not all(Path(value).is_file() for value in sources):
        raise ValueError(
            "Os três arquivos de origem precisam existir e pertencer à mesma instalação."
        )
    if bool(args.winsw) != bool(args.caddy):
        raise ValueError("Para preparar os serviços, informe --winsw e --caddy juntos.")
    for executable in (args.winsw, args.caddy):
        if executable and not Path(executable).is_file():
            raise ValueError("Confira os caminhos dos executáveis WinSW e Caddy.")
    if args.external_backups and not Path(args.external_backups).is_dir():
        raise ValueError("Crie primeiro o diretório externo de backups no destino escolhido.")
    if args.external_backups:
        external = Path(args.external_backups)
        if any(
            external == protected or protected in external.parents or external in protected.parents
            for protected in (PROJECT, root)
        ):
            raise ValueError(
                "O destino externo de backups precisa ficar separado do código e do estado."
            )
    npm()
    install_runtime(development=False)
    build(install=True)
    arguments = [
        PYTHON,
        "-B",
        PROJECT / "deploy/prepare_state.py",
        "--state-dir",
        root,
        "--origin",
        args.origin,
    ]
    if args.fresh:
        arguments.append("--fresh")
    else:
        for option, value in zip(("--source-env", "--source-key", "--source-database"), sources):
            arguments.extend([option, value])
    run(arguments, environment=app_environment(PROJECT / "backend/.env"))
    environment_file = root / "config/app.env"
    initialize(environment_file)
    shutil.copytree(FRONTEND / "dist", root / "www", dirs_exist_ok=True)
    if args.create_user:
        flask(["create-user"], environment_file)
    backup = [PYTHON, "-B", PROJECT / "deploy/run_backup.py", "--state-dir", root]
    if args.external_backups:
        backup.extend(["--external-directory", args.external_backups])
    run(backup, environment=app_environment(environment_file))
    if args.winsw:
        arguments = [
            "powershell.exe",
            "-NoProfile",
            "-File",
            PROJECT / "deploy/windows/Install-Services.ps1",
            "-ProjectPath",
            PROJECT,
            "-StatePath",
            root,
            "-AppHost",
            origin.hostname,
            "-WinSWPath",
            args.winsw,
            "-CaddyPath",
            args.caddy,
        ]
        if args.external_backups:
            arguments.extend(["-ExternalBackupPath", args.external_backups])
        run(arguments, environment=app_environment(environment_file))
    print("Produção preparada: configuração, chaves, banco, frontend e backup verificados.")
    print("Siga deploy/README.md para instalar os serviços e ativar o HTTPS privado do Tailscale.")
    print(f'Administração: setup.bat --env-file "{environment_file}" create-user')


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--env-file", help="Configuração existente escolhida para manutenção.")
    commands = result.add_subparsers(dest="command")
    install = commands.add_parser("install", help="Preparar instalação local completa (padrão).")
    install.add_argument("--env-file", default=argparse.SUPPRESS)
    install.add_argument(
        "--runtime-only", action="store_true", help="Excluir ferramentas de teste/lint."
    )
    install.add_argument(
        "--skip-frontend", action="store_true", help="Preparar somente a API local."
    )
    install.add_argument(
        "--create-user", action="store_true", help="Cadastrar primeiro acesso no final."
    )
    for name, description in (
        ("configure", "Criar/validar .env e .secrets sem substituir arquivos existentes."),
        ("run", "Servir o build e a API juntos somente em http://localhost:5173."),
        ("backend", "Executar apenas a API local na porta 5000."),
        ("frontend", "Executar Vite local para desenvolvimento na porta 5173."),
        ("build", "Compilar o frontend para local ou produção."),
        ("init-db", "Verificar criptografia e inicializar o banco configurado."),
        ("create-user", "Cadastrar usuário, senha e credenciais Pluggy pelo terminal."),
        ("reset-password", "Redefinir a senha de um usuário."),
        ("configure-pluggy", "Alterar as credenciais Pluggy individuais."),
        ("check", "Verificar lint, testes e build."),
        ("lint", "Verificar lint e formatação sem alterar arquivos."),
        ("test", "Executar os testes do backend e frontend."),
    ):
        child = commands.add_parser(name, help=description)
        child.add_argument("--env-file", default=argparse.SUPPRESS)
        if name in {"create-user", "reset-password", "configure-pluggy"}:
            child.add_argument("--email", help="E-mail do usuário (a senha continua oculta).")
            if name == "create-user":
                child.add_argument("--name", help="Nome do usuário.")
    admin = commands.add_parser("admin", help="Executar um comando Flask administrativo.")
    admin.add_argument("--env-file", default=argparse.SUPPRESS)
    admin.add_argument("arguments", nargs=argparse.REMAINDER)
    server = commands.add_parser("production", help="Preparar produção Windows, fora do checkout.")
    server.add_argument("--state-dir", required=True)
    server.add_argument("--origin", required=True)
    server.add_argument("--fresh", action="store_true")
    server.add_argument("--source-env")
    server.add_argument("--source-key")
    server.add_argument("--source-database")
    server.add_argument("--winsw")
    server.add_argument("--caddy")
    server.add_argument("--external-backups")
    server.add_argument("--create-user", action="store_true")
    return result


def main():
    cli = parser()
    arguments = sys.argv[1:] or ["install"]
    args = cli.parse_args(arguments)
    if args.command is None:
        args = cli.parse_args([*arguments, "install"])
    try:
        if args.command == "production":
            production(args)
            return
        if args.command == "install":
            selected = args.env_file or os.getenv("FINANCEHUB_ENV_FILE")
            if selected and Path(selected).resolve() != (PROJECT / "backend/.env").resolve():
                raise ValueError(
                    "install prepara o uso local. Para estado externo, use production ou o guia de atualização; "
                    "comandos administrativos aceitam --env-file."
                )
            if not args.skip_frontend:
                npm()
            install_runtime(development=not args.runtime_only)
            environment_file = configure(args.env_file, local=True)
            initialize(environment_file)
            if not args.skip_frontend:
                build(install=True)
            if args.create_user:
                flask(["create-user"], environment_file)
            print("Instalação concluída. Para criar seu acesso: setup.bat create-user")
            print("Para usar neste computador: setup.bat run (http://localhost:5173).")
            return
        if args.command in {"build", "frontend"}:
            if args.command == "build":
                build()
            else:
                run([npm(), "run", "dev", "--", "--host", "127.0.0.1"], cwd=FRONTEND)
            return
        require_runtime()
        if args.command in {"check", "lint", "test"}:
            if args.command in {"check", "lint"}:
                run(
                    [
                        PYTHON,
                        "-B",
                        "-m",
                        "ruff",
                        "check",
                        "backend",
                        "deploy",
                        "--config",
                        "backend/pyproject.toml",
                    ]
                )
                run(
                    [
                        PYTHON,
                        "-B",
                        "-m",
                        "ruff",
                        "format",
                        "--check",
                        "backend",
                        "deploy",
                        "--config",
                        "backend/pyproject.toml",
                    ]
                )
                run([npm(), "run", "lint"], cwd=FRONTEND)
            if args.command in {"check", "test"}:
                run(
                    [PYTHON, "-B", "-m", "unittest", "discover", "-s", "tests"],
                    cwd=PROJECT / "backend",
                )
                run([npm(), "test"], cwd=FRONTEND)
            if args.command == "check":
                build()
            return
        environment_file = configure(args.env_file)
        if args.command == "configure":
            return
        if args.command == "init-db":
            initialize(environment_file)
        elif args.command in {"run", "backend"}:
            local_arguments = [
                PYTHON,
                "-B",
                PROJECT / "deploy/run_local.py",
                *(["--api-only"] if args.command == "backend" else []),
            ]
            run(
                [*local_arguments, "--check"],
                cwd=PROJECT / "backend",
                environment=app_environment(environment_file),
            )
            initialize(environment_file)
            run(
                local_arguments,
                cwd=PROJECT / "backend",
                environment=app_environment(environment_file),
            )
        else:
            options = args.arguments if args.command == "admin" else [args.command]
            if args.command != "admin":
                for name in ("email", "name"):
                    value = getattr(args, name, None)
                    if value:
                        options.extend([f"--{name}", value])
            if not options:
                raise ValueError("Informe o comando após admin, por exemplo: admin -- --help.")
            if options[0] == "--":
                options = options[1:]
            flask(options, environment_file)
    except KeyboardInterrupt:
        print("\nExecução encerrada.")
    except ValueError as error:
        cli.exit(1, f"{error}\n")
    except subprocess.CalledProcessError:
        cli.exit(1, "A etapa anterior falhou; corrija o erro informado antes de continuar.\n")
    except OSError:
        cli.exit(1, "Não foi possível concluir a operação. Confira os caminhos e as permissões.\n")


if __name__ == "__main__":
    main()
