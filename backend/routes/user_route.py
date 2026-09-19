from flask import Blueprint, request, jsonify

from services.user_service import UserService

from exceptions import APIError

# Registrando o interceptador global para este Blueprint


user_routes = Blueprint("users", __name__)

user_service = UserService()

@user_routes.errorhandler(APIError)
def handle_api_error(error):
    return jsonify({"message": error.message}), error.status_code

@user_routes.route("/users", methods=["GET"])
def get_users():

    users = user_service.get_all_users()

    return jsonify({
        "users": [user.to_json() for user in users]
    })

@user_routes.route("/update_users/<int:user_id>", methods=["PATCH"])
def update_user(user_id):
    data = request.json
    user = user_service.update_user(user_id, data)
    return jsonify(user.to_json()), 200



@user_routes.route("/create_users", methods=["POST"])
def create_user():
    data = request.json
    user = user_service.create_user(data)
    return jsonify(user.to_json()), 201



@user_routes.route("/delete_users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    try:
        user_service.delete_user(user_id)
        return jsonify({"message": "User deleted successfully"}), 200
    except ValueError as e:
        return jsonify({
            "message": str(e)
        }), 404