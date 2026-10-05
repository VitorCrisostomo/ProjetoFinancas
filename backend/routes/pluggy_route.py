"""Expõe geração de token e sincronização de dados bancários."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from exceptions.api_errors import APIError
from models.account import Account
from services.account_service import AccountService
from services.pluggy_service import PluggyService
from services.transaction_service import TransactionService

pluggy_routes = Blueprint("pluggy", __name__)
account_service = AccountService()
transaction_service = TransactionService()


@pluggy_routes.errorhandler(APIError)
def handle_api_error(error):
    """Converte erros do serviço em mensagem JSON e status HTTP."""
    return jsonify({"message": error.message}), error.status_code


@pluggy_routes.route("/pluggy/connect_token", methods=["POST"])
@jwt_required()
def generate_connect_token():
    """Retorna o token necessário para abrir o widget bancário."""
    current_user_id = int(get_jwt_identity())
    token = PluggyService(current_user_id).get_connect_token(current_user_id)
    return jsonify({"connectToken": token}), 200


@pluggy_routes.route("/pluggy/accounts/sync", methods=["POST"])
@jwt_required()
def sync_pluggy_accounts():
    """Sincroniza as contas do itemId recebido para o usuário autenticado."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise APIError("Informe o itemId da conexão.", 400)
    item_id = data.get("itemId")
    current_user_id = int(get_jwt_identity())
    pluggy_service = PluggyService(current_user_id)

    synced_accounts = pluggy_service.sync_item_accounts(
        item_id=item_id, user_id=current_user_id, account_service=account_service
    )

    return jsonify(
        {"message": "Contas sincronizadas com sucesso!", "accounts": synced_accounts}
    ), 200


@pluggy_routes.route("/pluggy/transactions/sync", methods=["POST"])
@jwt_required()
def sync_pluggy_transactions():
    """Consulta e persiste as transações das contas do usuário autenticado."""
    current_user_id = int(get_jwt_identity())
    pluggy_service = PluggyService(current_user_id)
    options = request.get_json() if request.is_json else None
    date_from, date_to = pluggy_service.get_sync_date_range(options)

    user_accounts = Account.query.filter_by(user_id=current_user_id).all()

    # Consulta apenas dados e saldos das contas; as transações seguem restritas ao mês pedido.
    latest_accounts = {}
    for item_id in {account.itemId for account in user_accounts}:
        pluggy_service.verify_item_owner(item_id, current_user_id)
        item_accounts = pluggy_service.get_accounts_from_item(item_id)
        pluggy_service.validate_item_accounts(item_accounts, item_id, current_user_id)
        for data in item_accounts:
            latest_accounts[data.get("id")] = data
    for account in user_accounts:
        if account.id not in latest_accounts or latest_accounts[account.id].get("balance") is None:
            raise APIError("Não foi possível obter o saldo atual de uma conta conectada.", 502)

    total_synced = 0
    synced_transactions = []

    for account in user_accounts:
        pluggy_account_id = account.id

        if not pluggy_account_id:
            continue

        pluggy_txs = pluggy_service.get_transactions_for_account(
            pluggy_account_id, date_from=date_from, date_to=date_to
        )

        for tx_data in pluggy_txs:
            saved_tx = transaction_service.sync_transaction(
                tx_data=tx_data, internal_account_id=account.id, user_id=current_user_id
            )
            if saved_tx is not None:
                synced_transactions.append(saved_tx.to_json())
                total_synced += 1

        # Recalcula o ajuste somente após importar todas as páginas desta conta.
        account_service.sync_account(latest_accounts[account.id], current_user_id)

    return jsonify(
        {
            "message": f"{total_synced} transações sincronizadas com sucesso!",
            "transactions": synced_transactions,
        }
    ), 200
