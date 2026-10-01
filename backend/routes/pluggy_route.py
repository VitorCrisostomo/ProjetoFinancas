from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.pluggy_service import PluggyService
from services.account_service import AccountService
from services.transaction_service import TransactionService
from models.account import Account
from exceptions.api_errors import APIError
from datetime import datetime, timedelta

pluggy_routes = Blueprint("pluggy", __name__)
pluggy_service = PluggyService()
account_service = AccountService()
transaction_service = TransactionService()

@pluggy_routes.errorhandler(APIError)
def handle_api_error(error):
    return jsonify({"message": error.message}), error.status_code

@pluggy_routes.route("/pluggy/connect_token", methods=["GET"])
@jwt_required()
def generate_connect_token():
    token = pluggy_service.get_connect_token()
    return jsonify({"connectToken": token}), 200

@pluggy_routes.route("/pluggy/accounts/sync", methods=["POST"])
@jwt_required()
def sync_pluggy_accounts():
    data = request.get_json()
    item_id = data.get("itemId")
    current_user_id = int(get_jwt_identity())
    
    synced_accounts = pluggy_service.sync_item_accounts(
        item_id=item_id, 
        user_id=current_user_id, 
        account_service=account_service
    )
        
    return jsonify({
        "message": "Contas sincronizadas com sucesso!",
        "accounts": synced_accounts
    }), 200


@pluggy_routes.route("/pluggy/transactions/sync", methods=["POST"])
@jwt_required()
def sync_pluggy_transactions():
    current_user_id = int(get_jwt_identity())
    
    
    user_accounts = Account.query.filter_by(user_id=current_user_id).all()
    
    total_synced = 0
    synced_transactions = []
    
    for account in user_accounts:
        pluggy_account_id = account.id 
        
        if not pluggy_account_id:
            continue
            
        # Busca TODAS as transações na Pluggy usando o UUID da conta (sem passar from_date)
        pluggy_txs = pluggy_service.get_transactions_for_account(pluggy_account_id)
        
        for tx_data in pluggy_txs:
            saved_tx = transaction_service.sync_transaction(
                tx_data=tx_data, 
                internal_account_id=account.id, 
                user_id=current_user_id
            )
            synced_transactions.append(saved_tx.to_json())
            total_synced += 1
            
    return jsonify({
        "message": f"{total_synced} transações sincronizadas com sucesso!",
        "transactions": synced_transactions
    }), 200