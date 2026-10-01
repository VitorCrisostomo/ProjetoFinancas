"""Expõe os endpoints de transações protegidos por JWT."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from exceptions import APIError
from services.transaction_service import TransactionService

transaction_routes = Blueprint("transactions", __name__)

transaction_service = TransactionService()


@transaction_routes.errorhandler(APIError)
def handle_api_error(error):
    """Converte erros do serviço em mensagem JSON e status HTTP."""
    return jsonify({"message": error.message}), error.status_code


@transaction_routes.route("/transactions", methods=["GET"])
@jwt_required()
def list_transactions():
    """Lista as transações do usuário autenticado."""
    current_user_id = get_jwt_identity()

    user_id_int = int(current_user_id)

    transactions = transaction_service.get_transactions_by_user_id(user_id_int)

    return jsonify([t.to_json() for t in transactions]), 200


@transaction_routes.route("/update_transactions/<int:transaction_id>", methods=["PATCH"])
@jwt_required()
def update_transaction(transaction_id):
    """Atualiza a transação indicada com os campos recebidos."""
    data = request.get_json()
    transaction = transaction_service.update_transaction(
        transaction_id, data, user_id=int(get_jwt_identity())
    )

    return jsonify(transaction.to_json()), 200


@transaction_routes.route("/transactions/associate", methods=["POST"])
@jwt_required()
def associate_transaction():
    """Associa os lançamentos selecionados pertencentes ao usuário autenticado."""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    keep_id = data.get("keep_id")
    remove_id = data.get("remove_id")
    updated_data = data.get("updated_data")

    if "transaction_ids" in data:
        updated_transaction = transaction_service.associate_transactions(
            current_user_id, data["transaction_ids"], data.get("updated_data", {})
        )
        return jsonify(updated_transaction.to_json()), 200

    if not keep_id or not remove_id or not updated_data:
        return jsonify({"message": "Dados incompletos para associação."}), 400

    updated_transaction = transaction_service.associate_transactions(
        current_user_id, [keep_id, remove_id], updated_data
    )

    return jsonify(updated_transaction.to_json()), 200
