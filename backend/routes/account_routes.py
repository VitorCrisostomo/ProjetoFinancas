from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.account_service import AccountService
from exceptions.api_errors import APIError

account_routes = Blueprint("accounts", __name__)
account_service = AccountService()

@account_routes.errorhandler(APIError)
def handle_api_error(error):
    return jsonify({"message": error.message}), error.status_code

@account_routes.route("/accounts", methods=["GET"])
@jwt_required()
def list_accounts():
    """Retorna todas as contas do usuário logado."""
    current_user_id = int(get_jwt_identity())
    
    accounts = account_service.get_accounts_by_user_id(current_user_id)
    
    return jsonify([account.to_json() for account in accounts]), 200

@account_routes.route("/accounts/sync", methods=["POST"])
@jwt_required()
def sync_account():
    data = request.get_json()
    
    if not data:
        return jsonify({"message": "Nenhum dado fornecido"}), 400

    current_user_id = int(get_jwt_identity())
    
    account = account_service.sync_account(data, current_user_id)
    
    return jsonify(account.to_json()), 200

@account_routes.route("/accounts/<string:account_id>", methods=["DELETE"])
@jwt_required()
def delete_account(account_id):
    current_user_id = int(get_jwt_identity())
    
    account_service.delete_account(account_id, current_user_id)
    
    return jsonify({"message": "Conta removida com sucesso"}), 200