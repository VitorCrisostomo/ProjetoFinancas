"""Configura Flask, banco de dados, JWT, CORS e erros da API."""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy

from exceptions.api_errors import APIError
from services.data_encryption import DataCipher

load_dotenv()

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
if not app.config["JWT_SECRET_KEY"] or len(app.config["JWT_SECRET_KEY"]) < 32:
    raise RuntimeError("Configure JWT_SECRET_KEY com pelo menos 32 caracteres aleatórios.")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"hide_parameters": True}
app.config["PLUGGY_ENV_FILE"] = str(Path(__file__).resolve().parent / ".env")
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

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app, origins=app.config["AUTH_ALLOWED_ORIGINS"], supports_credentials=True)


@app.errorhandler(APIError)
def handle_api_error(error):
    """Converte erros do serviço em mensagem JSON e status HTTP."""
    return jsonify({"message": error.message}), error.status_code
