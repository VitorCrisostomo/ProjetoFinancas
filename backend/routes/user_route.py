from flask import Blueprint, request, jsonify
from services.user_service import UserService
from exceptions import APIError
from flask_jwt_extended import create_access_token

user_routes = Blueprint("users", __name__)

user_service = UserService()

@user_routes.errorhandler(APIError)
def handle_api_error(error):
    
    return jsonify({"message": error.message}), error.status_code

@user_routes.route("/create_users", methods=["POST"])
def create_user():
    data = request.json
    user = user_service.create_user(data)

    return jsonify(user.to_json()), 201

@user_routes.route("/users", methods=["GET"])
def get_users():
    users = user_service.get_all_users()

    return jsonify({"users": [user.to_json() for user in users]})

@user_routes.route("/update_users/<int:user_id>", methods=["PATCH"])
def update_user(user_id):
    data = request.json
    user = user_service.update_user(user_id, data)

    return jsonify(user.to_json()), 200

@user_routes.route("/delete_users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
        user_service.delete_user(user_id)

        return jsonify({"message": "User deleted successfully"}), 200

from flask import request, jsonify

from flask import request, jsonify
from flask_jwt_extended import create_access_token # 1. Adicione este import no topo do arquivo

@user_routes.route("/login", methods=["POST"])
def login():
    data = request.json
    
    if not data:
        return jsonify({"message": "Nenhum dado recebido"}), 400

    user = user_service.authenticate_user(data)

    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "message": "Login realizado com sucesso!",
        "access_token": access_token, # O frontend vai ler isso aqui!
        "user": user.to_json()
    }), 200

@user_routes.route("/verify_email", methods=["POST"])
def verify_email():
    data = request.json
    # Chama a função que acabamos de criar no Service
    user = user_service.verify_account(data)
    
    return jsonify({"message": "E-mail verificado com sucesso! Agora você pode fazer login."}), 200