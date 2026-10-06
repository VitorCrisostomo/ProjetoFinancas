"""Configura Flask, banco de dados, JWT, CORS e erros da API."""

import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine import make_url

from exceptions.api_errors import APIError
from services.data_encryption import DataCipher

environment_file = Path(
    os.getenv("FINANCEHUB_ENV_FILE") or Path(__file__).resolve().parent / ".env"
).resolve()
# Um arquivo externo explícito é a fonte de configuração da instalação, inclusive
# nos comandos administrativos executados por shells com variáveis antigas.
load_dotenv(environment_file, override=bool(os.getenv("FINANCEHUB_ENV_FILE")))

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
if not app.config["JWT_SECRET_KEY"] or len(app.config["JWT_SECRET_KEY"]) < 32:
    raise RuntimeError("Configure JWT_SECRET_KEY com pelo menos 32 caracteres aleatórios.")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"hide_parameters": True}
if (app.config["SQLALCHEMY_DATABASE_URI"] or "").startswith("sqlite:"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"]["connect_args"] = {"timeout": 30}
app.config["PLUGGY_ENV_FILE"] = str(environment_file)
app.config["APP_ENV"] = os.getenv("APP_ENV", "development")
app.config["BACKUP_DIRECTORY"] = os.getenv("BACKUP_DIRECTORY") or str(
    Path(__file__).resolve().parent / "backups"
)
app.config["DATA_ENCRYPTION_KEY_FILE"] = os.getenv("DATA_ENCRYPTION_KEY_FILE") or str(
    Path(__file__).resolve().parent / ".secrets" / "financial-data-keys.json"
)
app.extensions["financial_data_cipher"] = DataCipher.from_key_file(
    app.config["DATA_ENCRYPTION_KEY_FILE"]
)
cookie_secure = os.getenv("AUTH_COOKIE_SECURE", "true").lower()
if cookie_secure not in {"true", "false"}:
    raise RuntimeError("AUTH_COOKIE_SECURE deve ser true ou false.")
app.config.update(
    JWT_TOKEN_LOCATION=["cookies"],
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=8),
    JWT_COOKIE_SECURE=cookie_secure == "true",
    JWT_COOKIE_SAMESITE="Lax",
    JWT_COOKIE_CSRF_PROTECT=True,
    JWT_CSRF_IN_COOKIES=False,
    AUTH_ALLOWED_ORIGINS=[
        origin.strip().rstrip("/")
        for origin in os.getenv(
            "AUTH_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ],
    AUTH_LOGIN_WINDOW_SECONDS=900,
    AUTH_LOGIN_EMAIL_LIMIT=5,
    AUTH_LOGIN_ADDRESS_LIMIT=20,
    MAX_CONTENT_LENGTH=1024 * 1024,
)

if app.config["APP_ENV"] not in {"development", "production"}:
    raise RuntimeError("APP_ENV deve ser development ou production.")
if app.config["APP_ENV"] == "production":
    origins = app.config["AUTH_ALLOWED_ORIGINS"]
    parsed_origins = [urlsplit(origin) for origin in origins]
    if (
        not app.config["JWT_COOKIE_SECURE"]
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
            for origin in parsed_origins
        )
    ):
        raise RuntimeError("Produção exige cookies Secure e origens HTTPS exatas.")
    if not environment_file.is_file() or not os.getenv("DATA_ENCRYPTION_KEY_FILE"):
        raise RuntimeError("Produção exige arquivo de configuração e caminho explícito das chaves.")
    database_url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
    if (
        database_url.get_backend_name() != "sqlite"
        or not database_url.database
        or not Path(database_url.database).is_absolute()
        or not Path(app.config["DATA_ENCRYPTION_KEY_FILE"]).is_absolute()
        or not Path(app.config["BACKUP_DIRECTORY"]).is_absolute()
    ):
        raise RuntimeError("Produção exige SQLite, chaves e backups com caminhos absolutos.")
    app.config["TRUSTED_HOSTS"] = [origin.hostname for origin in parsed_origins]
    app.config["DEBUG"] = False

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app, origins=app.config["AUTH_ALLOWED_ORIGINS"], supports_credentials=True)


@app.errorhandler(APIError)
def handle_api_error(error):
    """Converte erros do serviço em mensagem JSON e status HTTP."""
    return jsonify({"message": error.message}), error.status_code
