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


@transaction_routes.route("/create_transactions", methods=["POST"])
@jwt_required()
def create_transaction():
    """Cria um lançamento com o usuário identificado pelo JWT."""
    data = request.get_json()
    current_user_id = get_jwt_identity()
    data["user_id"] = int(current_user_id)
    transaction = transaction_service.create_transaction(data)
    return jsonify(transaction.to_json()), 201


@transaction_routes.route("/transactions/import", methods=["POST"])
@jwt_required()
def import_transactions():
    """Importa o arquivo CSV recebido no campo multipart file."""
    if "file" not in request.files:
        return jsonify({"message": "Nenhum arquivo enviado no formulário."}), 400

    file = request.files["file"]
    current_user_id = int(get_jwt_identity())
    imported_count = transaction_service.import_csv(file, current_user_id)

    return jsonify(
        {"message": "Importação concluída com sucesso!", "imported_count": imported_count}
    ), 201


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
    transaction = transaction_service.update_transaction(transaction_id, data)

    return jsonify(transaction.to_json()), 200


@transaction_routes.route("/transactions/associate", methods=["POST"])
@jwt_required()
def associate_transaction():
    """Associa dois lançamentos pertencentes ao usuário autenticado."""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    keep_id = data.get("keep_id")
    remove_id = data.get("remove_id")
    updated_data = data.get("updated_data")

    if not keep_id or not remove_id or not updated_data:
        return jsonify({"message": "Dados incompletos para associação."}), 400

    updated_transaction = transaction_service.associate_transaction(
        current_user_id, keep_id, remove_id, updated_data
    )

    return jsonify(updated_transaction.to_json()), 200


@transaction_routes.route("/transactions/<int:transaction_id>", methods=["DELETE"])
@jwt_required()
def delete_transaction(transaction_id):
    """Exclui a transação indicada no caminho da requisição."""
    transaction_service.delete_transaction(transaction_id)

    return jsonify({"message": "Transaction deleted successfully"}), 200
