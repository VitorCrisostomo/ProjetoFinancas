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
    ipaddress.ip_address(proxy)  # Nunca aceita o curinga de confiança irrestrita.
    host = os.getenv("SERVER_HOST", "127.0.0.1")
    if not ipaddress.ip_address(host).is_loopback:
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
