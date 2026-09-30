from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.pluggy_service import PluggyService
from services.account_service import AccountService
from exceptions.api_errors import APIError

pluggy_routes = Blueprint("pluggy", __name__)
pluggy_service = PluggyService()
account_service = AccountService()

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