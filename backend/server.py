"""Execução WSGI explícita; o banco é preparado antes de iniciar o serviço."""

import ipaddress
import os

from sqlalchemy import inspect
from waitress import serve

from config import db
from main import app
from services.database_encryption_service import verify_encrypted_database


def run():
    if app.config["APP_ENV"] != "production":
        raise RuntimeError("Configure APP_ENV=production antes de iniciar o servidor.")
    proxy = os.getenv("TRUSTED_PROXY", "127.0.0.1")
    proxy_address = ipaddress.ip_address(proxy)
    host = os.getenv("SERVER_HOST", "127.0.0.1")
    address = ipaddress.ip_address(host)
    if app.config.get("DEPLOYMENT_MODE", "native") == "docker":
        if host != "0.0.0.0" or not isinstance(proxy_address, ipaddress.IPv4Address):
            raise RuntimeError("Docker exige bind IPv4 interno e proxy concreto do serviço web.")
        if (
            not proxy_address.is_private
            or proxy_address.is_loopback
            or proxy_address.is_unspecified
        ):
            raise RuntimeError("Docker exige o IP privado específico do serviço web.")
        if proxy != os.getenv("FINANCEHUB_DOCKER_PROXY"):
            raise RuntimeError("O proxy da configuração deve corresponder à rede do Compose.")
    elif not address.is_loopback:
        raise RuntimeError("O servidor interno deve escutar apenas em loopback.")
    with app.app_context():
        if not set(db.metadata.tables).issubset(inspect(db.engine).get_table_names()):
            raise RuntimeError("Inicialize o banco com flask --app main init-db antes de iniciar.")
        verify_encrypted_database()
    serve(
        app,
        host=host,
        port=int(os.getenv("SERVER_PORT", "8000")),
        threads=4,
        max_request_body_size=app.config["MAX_CONTENT_LENGTH"],
        trusted_proxy=proxy,
        trusted_proxy_count=1,
        trusted_proxy_headers={"x-forwarded-for", "x-forwarded-proto", "x-forwarded-host"},
        clear_untrusted_proxy_headers=True,
    )


if __name__ == "__main__":
    run()
