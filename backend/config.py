"""Configura Flask, banco de dados, JWT, CORS e erros da API."""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy

from exceptions.api_errors import APIError

load_dotenv()

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)


@app.errorhandler(APIError)
def handle_api_error(error):
    """Converte erros do serviço em mensagem JSON e status HTTP."""
    return jsonify({"message": error.message}), error.status_code
