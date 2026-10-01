"""Expõe cadastro, login, verificação e operações de usuários."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token

from exceptions import APIError
from services.user_service import UserService

user_routes = Blueprint("users", __name__)

user_service = UserService()


@user_routes.errorhandler(APIError)
def handle_api_error(error):
    """Converte erros do serviço em mensagem JSON e status HTTP."""
    return jsonify({"message": error.message}), error.status_code


@user_routes.route("/create_users", methods=["POST"])
def create_user():
    """Recebe os dados de cadastro e retorna o usuário criado."""
    data = request.json
    user = user_service.create_user(data)

    return jsonify(user.to_json()), 201


@user_routes.route("/users", methods=["GET"])
def get_users():
    """Lista os dados públicos serializados dos usuários cadastrados."""
    users = user_service.get_all_users()

    return jsonify({"users": [user.to_json() for user in users]})


@user_routes.route("/update_users/<int:user_id>", methods=["PATCH"])
def update_user(user_id):
    """Encaminha os campos recebidos para atualização do usuário."""
    data = request.json
    user = user_service.update_user(user_id, data)

    return jsonify(user.to_json()), 200


@user_routes.route("/delete_users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    """Exclui o usuário indicado no caminho da requisição."""
    user_service.delete_user(user_id)

    return jsonify({"message": "User deleted successfully"}), 200


@user_routes.route("/login", methods=["POST"])
def login():
    """Valida as credenciais e retorna o JWT com a identidade do usuário."""
    data = request.json

    if not data:
        return jsonify({"message": "Nenhum dado recebido"}), 400

    user = user_service.authenticate_user(data)

    access_token = create_access_token(identity=str(user.id))

    return jsonify(
        {
            "message": "Login realizado com sucesso!",
            "access_token": access_token,
            "user": user.to_json(),
        }
    ), 200


@user_routes.route("/verify_email", methods=["POST"])
def verify_email():
    """Verifica o código recebido e confirma o cadastro."""
    data = request.json
    user_service.verify_account(data)

    return jsonify({"message": "E-mail verificado com sucesso! Agora você pode fazer login."}), 200
