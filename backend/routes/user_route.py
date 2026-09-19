from flask import Blueprint, request, jsonify

from services.user_service import UserService


user_routes = Blueprint("users", __name__)

user_service = UserService()


@user_routes.route("/users", methods=["GET"])
def get_users():

    users = user_service.get_all_users()

    return jsonify({
        "users": [user.to_json() for user in users]
    })


@user_routes.route("/users", methods=["POST"])
def create_user():

    data = request.json

    user = user_service.create_user(data)

    return jsonify(user.to_json()), 201