"""Serve API e frontend compilado em loopback, sem depender de Node no uso diário."""

import argparse
import sys
from pathlib import Path

from flask import Flask, send_from_directory
from waitress import serve
from werkzeug.exceptions import SecurityError
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.wrappers import Response
from werkzeug.wsgi import get_host

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "backend"))


class LocalHosts:
    """Valida Host também nas rotas da API, antes do DispatcherMiddleware."""

    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        try:
            get_host(environ, trusted_hosts=["localhost", "127.0.0.1"])
        except SecurityError:
            return Response("Host inválido.", status=421)(environ, start_response)
        return self.application(environ, start_response)


def application(api, directory):
    directory = Path(directory).resolve()
    if not (directory / "index.html").is_file():
        raise ValueError("Compile primeiro a interface com setup.bat build.")
    frontend = Flask("financehub_local", static_folder=None)

    @frontend.get("/", defaults={"path": ""})
    @frontend.get("/<path:path>")
    def page(path):
        candidate = (directory / path).resolve()
        if candidate != directory and directory not in candidate.parents:
            return Response("Caminho inválido.", status=404)
        if candidate.is_file():
            response = send_from_directory(directory, path)
        elif path.startswith("assets/"):
            return Response("Arquivo não encontrado.", status=404)
        else:
            response = send_from_directory(directory, "index.html")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-cache"
        return response

    return LocalHosts(DispatcherMiddleware(frontend, {"/api": api}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-only", action="store_true")
    parser.add_argument("--check", action="store_true", help="Validar sem iniciar o servidor.")
    args = parser.parse_args()
    from main import app

    if app.config["APP_ENV"] != "development" or app.config["DEPLOYMENT_MODE"] != "native":
        parser.exit(1, "Esta execução é local. Use os serviços Windows ou Docker para produção.\n")
    allowed = {"http://localhost:5173", "http://127.0.0.1:5173"}
    origins = set(app.config["AUTH_ALLOWED_ORIGINS"])
    if app.config["JWT_COOKIE_SECURE"] or not origins or not origins.issubset(allowed):
        parser.exit(
            1, "A configuração local exige as origens localhost/127.0.0.1:5173 e cookies HTTP.\n"
        )
    try:
        wsgi = LocalHosts(app) if args.api_only else application(app, PROJECT / "frontend/dist")
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    if args.check:
        return
    port = 5000 if args.api_only else 5173
    host = "localhost" if "http://localhost:5173" in origins else "127.0.0.1"
    print(f"FinanceHub disponível em http://{host}:{port}. Ctrl+C encerra o servidor.", flush=True)
    serve(
        wsgi,
        host="127.0.0.1",
        port=port,
        threads=4,
        max_request_body_size=1024 * 1024,
        clear_untrusted_proxy_headers=True,
    )


if __name__ == "__main__":
    main()
