from flask import Blueprint, request, jsonify
from services.transaction_service import TransactionService
from exceptions import APIError

# Registrando o interceptador global para este Blueprint


transaction_routes = Blueprint("transactions", __name__)

transaction_service = TransactionService()

@transaction_routes.errorhandler(APIError)
def handle_api_error(error):
    return jsonify({"message": error.message}), error.status_code


@transaction_routes.route("/create_transactions", methods=["POST"])
def create_transaction():
    data = request.json
    transaction = transaction_service.create_transaction(data)
    
    return jsonify(transaction.to_json()), 201


@transaction_routes.route("/transactions", methods=["GET"])
def get_transactions():
    transactions = transaction_service.get_all_transactions()

    return jsonify({"transactions": [transaction.to_json() for transaction in transactions]})

@transaction_routes.route("/update_transactions/<int:transaction_id>", methods=["PATCH"])
def update_transaction(transaction_id):
    data = request.json
    transaction = transaction_service.update_transaction(transaction_id, data)

    return jsonify(transaction.to_json()), 200


@transaction_routes.route("/transactions/<int:transaction_id>",methods=["DELETE"])
def delete_transaction(transaction_id):
    transaction_service.delete_transaction(transaction_id)

    return jsonify({"message": "Transaction deleted successfully"}), 200