from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

from flask_jwt_extended import JWTManager
from exceptions.api_errors import APIError

app = Flask(__name__)
jwt = JWTManager(app)
CORS(app)

app.config["JWT_SECRET_KEY"] = "REVOKED_JWT_SECRET"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydatabase.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

@app.errorhandler(APIError)
def handle_api_error(error):
    return jsonify({
        "error": error.message
    }), error.status_code