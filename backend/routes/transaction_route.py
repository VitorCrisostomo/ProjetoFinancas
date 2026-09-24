from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.transaction_service import TransactionService
from exceptions import APIError

# Registrando o interceptador global para este Blueprint


transaction_routes = Blueprint("transactions", __name__)

transaction_service = TransactionService()

@transaction_routes.errorhandler(APIError)
def handle_api_error(error):
    return jsonify({"message": error.message}), error.status_code


@transaction_routes.route("/create_transactions", methods=["POST"])
@jwt_required()
def create_transaction():
    data = request.get_json()
    current_user_id = get_jwt_identity() 
    data['user_id'] = int(current_user_id)
    transaction = transaction_service.create_transaction(data)
    return jsonify(transaction.to_json()), 201

@transaction_routes.route("/transactions", methods=["GET"])
@jwt_required()
def list_transactions():

    current_user_id = get_jwt_identity()

    user_id_int = int(current_user_id)

    transactions = transaction_service.get_transactions_by_user_id(user_id_int)
    
    return jsonify([t.to_json() for t in transactions]), 200

@transaction_routes.route("/update_transactions/<int:transaction_id>", methods=["PATCH"])
@jwt_required()
def update_transaction(transaction_id):
    data = request.get_json()
    transaction = transaction_service.update_transaction(transaction_id, data)

    return jsonify(transaction.to_json()), 200


@transaction_routes.route("/transactions/<int:transaction_id>",methods=["DELETE"])
@jwt_required()
def delete_transaction(transaction_id):
    transaction_service.delete_transaction(transaction_id)

    return jsonify({"message": "Transaction deleted successfully"}), 200