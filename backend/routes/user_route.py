"""Login, logout e operações autenticadas sobre o próprio perfil."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    current_user,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)

from exceptions.api_errors import APIError
from services.auth_service import AuthService
from services.user_service import UserService

user_routes = Blueprint("users", __name__)
user_service = UserService()
auth_service = AuthService()


@user_routes.errorhandler(APIError)
def handle_api_error(error):
    return jsonify({"message": error.message}), error.status_code


@user_routes.route("/create_users", methods=["POST"])
@user_routes.route("/verify_email", methods=["POST"])
def closed_registration():
    return jsonify({"message": "Solicite seu acesso ao administrador do servidor."}), 403


@user_routes.route("/users", methods=["GET"])
@jwt_required()
def get_users():
    """Mantém o formato anterior, limitado ao próprio usuário."""
    return jsonify({"users": [current_user.to_json()]}), 200


@user_routes.route("/auth/session", methods=["GET"])
@jwt_required()
def get_session():
    return jsonify({"user": current_user.to_json(), "csrf_token": get_jwt()["csrf"]}), 200


@user_routes.route("/update_users/<int:user_id>", methods=["PATCH"])
@jwt_required()
def update_user(user_id):
    data = request.get_json(silent=True)
    user = user_service.update_user(user_id, data, int(get_jwt_identity()))
    response = jsonify(user.to_json())
    if "password" in data:
        unset_jwt_cookies(response)
    return response, 200


@user_routes.route("/delete_users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    user_service.delete_user(user_id, request.get_json(silent=True), int(get_jwt_identity()))
    response = jsonify({"message": "Perfil e dados removidos com sucesso."})
    unset_jwt_cookies(response)
    return response, 200


@user_routes.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"message": "Informe e-mail e senha."}), 400
    email = user_service.normalize_email(data.get("email"))
    address = request.remote_addr or "unknown"
    auth_service.check_login_limit(email, address)
    try:
        user = user_service.authenticate_user(data)
    except APIError:
        auth_service.record_login_failure(email, address)
        raise
    token, csrf = auth_service.create_session(user)
    response = jsonify({"user": user.to_json(), "csrf_token": csrf})
    set_access_cookies(response, token)
    return response, 200


@user_routes.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    auth_service.revoke_session(get_jwt()["jti"])
    response = jsonify({"message": "Sessão encerrada."})
    unset_jwt_cookies(response)
    return response, 200
