from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from services.pluggy_service import PluggyService
from exceptions.api_errors import APIError

pluggy_routes = Blueprint("pluggy", __name__)
pluggy_service = PluggyService()

@pluggy_routes.errorhandler(APIError)
def handle_api_error(error):
    return jsonify({"message": error.message}), error.status_code

@pluggy_routes.route("/pluggy/connect_token", methods=["GET"])
@jwt_required()
def generate_connect_token():
    token = pluggy_service.get_connect_token()
    return jsonify({"connectToken": token}), 200