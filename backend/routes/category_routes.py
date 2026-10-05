"""Catálogo e criação de categorias autenticadas."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from exceptions.api_errors import APIError
from services.category_service import CategoryService

category_routes = Blueprint("categories", __name__)
category_service = CategoryService()


@category_routes.errorhandler(APIError)
def handle_api_error(error):
    return jsonify({"message": error.message}), error.status_code


@category_routes.route("/categories", methods=["GET"])
@jwt_required()
def list_categories():
    categories = category_service.list_categories(int(get_jwt_identity()))
    return jsonify([category.to_json() for category in categories]), 200


@category_routes.route("/categories", methods=["POST"])
@jwt_required()
def create_category():
    category = category_service.create_category(
        int(get_jwt_identity()), request.get_json(silent=True)
    )
    return jsonify(category.to_json()), 201


@category_routes.route("/categories/<int:category_id>/subcategories", methods=["POST"])
@jwt_required()
def create_subcategory(category_id):
    category = category_service.create_subcategory(
        int(get_jwt_identity()), category_id, request.get_json(silent=True)
    )
    return jsonify(category.to_json()), 201
