from flask import Blueprint, request, jsonify

from services.user_service import UserService

from exceptions import APIError

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

@user_routes.route("/login", methods=["POST"])
def login():
    # Isso vai imprimir imediatamente o que chegou do React
    print("\n=== REQUISIÇÃO RECEBIDA ===", flush=True)
    print("Cabeçalhos:", request.headers.get("Content-Type"), flush=True)
    print("Dados JSON:", request.json, flush=True)
    print("===========================\n", flush=True)

    data = request.json
    
    # Se o data vier vazio, já sabemos que o React não enviou certo
    if not data:
        return jsonify({"message": "Nenhum dado recebido"}), 400

    user = user_service.authenticate_user(data)

    return jsonify({
        "message": "Login realizado com sucesso!",
        "user": user.to_json()
    }), 200