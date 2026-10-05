"""Comunica o backend com a API da Pluggy."""

import re
from calendar import monthrange
from datetime import date

import requests

from exceptions.api_errors import APIError, ValidationError
from services.pluggy_credentials import PluggyCredentialsStore


class PluggyService:
    """Autenticação e consulta de dados na API externa da Pluggy."""

    def __init__(self, user_id=None):
        self.user_id = user_id
        self._credential_pair = None
        self._api_key = None
        self.base_url = "https://api.pluggy.ai"

    def _require_user(self, user_id=None):
        if type(self.user_id) is not int or self.user_id <= 0:
            raise APIError("A integração exige um usuário autenticado.", 403)
        if user_id is not None and user_id != self.user_id:
            raise APIError("Conexão bancária não autorizada.", 403)

    def _credentials(self):
        from services.auth_service import AuthService

        self._require_user()
        if self._credential_pair is None:
            reference = AuthService.get_pluggy_reference(self.user_id)
            self._credential_pair = PluggyCredentialsStore().get(reference)
        return self._credential_pair

    def _get_api_key(self):
        """Autentica as credenciais configuradas e retorna a chave da API."""
        if self._api_key is not None:
            return self._api_key
        url = f"{self.base_url}/auth"
        client_id, client_secret = self._credentials()
        payload = {"clientId": client_id, "clientSecret": client_secret}

        try:
            response = requests.post(url, json=payload, timeout=30)
        except requests.RequestException as error:
            raise APIError("Falha de conexão ao autenticar com a Pluggy.", 502) from error

        if response.status_code != 200:
            raise APIError("Falha ao autenticar com a API da Pluggy.", status_code=500)

        try:
            api_key = response.json().get("apiKey")
        except (ValueError, AttributeError) as error:
            raise APIError("Resposta bancária inválida.", 502) from error
        if not isinstance(api_key, str) or not api_key:
            raise APIError("Resposta bancária inválida.", 502)
        # Instância criada por requisição: o token nunca é compartilhado entre usuários.
        self._api_key = api_key
        return api_key

    def get_connect_token(self, user_id):
        """Vincula o token à identidade bancária estável do usuário autenticado."""
        from services.auth_service import AuthService

        self._require_user(user_id)
        reference = AuthService.get_pluggy_reference(user_id)
        api_key = self._get_api_key()
        url = f"{self.base_url}/connect_token"

        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

        try:
            response = requests.post(
                url, headers=headers, json={"options": {"clientUserId": reference}}, timeout=30
            )
        except requests.RequestException as error:
            raise APIError("Falha de conexão ao gerar o token da Pluggy.", 502) from error

        if response.status_code != 200:
            raise APIError("Falha ao gerar o Connect Token da Pluggy.", status_code=500)

        return response.json().get("accessToken")

    @staticmethod
    def validate_item_id(item_id):
        if not isinstance(item_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", item_id):
            raise ValidationError("Informe um itemId válido.")

    def get_item(self, item_id):
        """Consulta a identidade vinculada ao item diretamente no provedor."""
        self.validate_item_id(item_id)
        try:
            response = requests.get(
                f"{self.base_url}/items/{item_id}",
                headers={"X-API-KEY": self._get_api_key()},
                timeout=30,
            )
        except requests.RequestException as error:
            raise APIError("Falha de conexão ao verificar a conexão bancária.", 502) from error
        if response.status_code != 200:
            raise APIError("Não foi possível verificar a conexão bancária.", 502)
        try:
            data = response.json()
        except ValueError as error:
            raise APIError("Resposta bancária inválida.", 502) from error
        if not isinstance(data, dict) or data.get("id") != item_id:
            raise APIError("Resposta bancária inválida.", 502)
        return data

    def verify_item_owner(self, item_id, user_id):
        """Não aceita a posse de um UUID como prova de autorização."""
        from models.account import Account
        from models.auth_session import UserSecurity

        self._require_user(user_id)
        self.validate_item_id(item_id)
        existing = Account.query.filter_by(itemId=item_id).all()
        if any(account.user_id != user_id for account in existing):
            raise APIError("Conexão bancária não autorizada.", 403)
        item = self.get_item(item_id)
        reference = item.get("clientUserId")
        security = (
            UserSecurity.query.filter_by(pluggy_reference=reference).first() if reference else None
        )
        if security and security.user_id == user_id:
            return
        # Itens antigos sem referência opaca só continuam com o proprietário local.
        # Um item desconhecido ou excluído não pode ser reivindicado por essa exceção.
        if existing and reference in (None, "", str(user_id)):
            return
        raise APIError("Conexão bancária não autorizada. Conecte a conta novamente.", 403)

    def get_accounts_from_item(self, item_id):
        """Busca todas as contas atreladas a uma conexão (itemId) na Pluggy."""
        api_key = self._get_api_key()

        self.validate_item_id(item_id)
        url = f"{self.base_url}/accounts"

        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

        try:
            response = requests.get(url, headers=headers, params={"itemId": item_id}, timeout=30)
        except requests.RequestException as error:
            raise APIError("Falha de conexão ao consultar contas na Pluggy.", 502) from error

        if response.status_code != 200:
            raise APIError("Falha ao buscar contas na API da Pluggy.", status_code=500)

        try:
            data = response.json()
        except ValueError as error:
            raise APIError("Resposta bancária inválida.", 502) from error
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise APIError("Resposta bancária inválida.", 502)
        return data["results"]

    @staticmethod
    def validate_item_accounts(accounts, item_id, user_id):
        """Valida toda a resposta antes da primeira escrita."""
        from config import db
        from models.account import Account

        for data in accounts:
            if not isinstance(data, dict) or not data.get("id") or data.get("itemId") != item_id:
                raise APIError("A Pluggy retornou uma conta de uma conexão diferente.", 502)
            existing = db.session.get(Account, data["id"])
            if existing and (existing.user_id != user_id or existing.itemId != item_id):
                raise APIError("Conexão bancária não autorizada.", 403)

    def sync_item_accounts(self, item_id, user_id, account_service):
        """Busca contas do item e delega sua persistência ao serviço de contas."""
        self.verify_item_owner(item_id, user_id)
        pluggy_accounts_data = self.get_accounts_from_item(item_id)
        self.validate_item_accounts(pluggy_accounts_data, item_id, user_id)

        synced_accounts = []
        for acc_data in pluggy_accounts_data:
            synced_acc = account_service.sync_account(acc_data, user_id)
            synced_accounts.append(synced_acc.to_json())

        return synced_accounts

    @staticmethod
    def get_sync_date_range(options):
        """Valida a opção de sincronização e retorna as datas inclusivas do mês."""
        if options is None:
            options = {}
        if not isinstance(options, dict):
            raise ValidationError("As opções de sincronização devem ser um objeto JSON.")
        mode = options.get("mode")
        if mode != "month":
            raise ValidationError("Escolha um mês e ano para sincronizar.")
        year = options.get("year")
        month = options.get("month")
        if (
            type(year) is not int
            or type(month) is not int
            or not 1900 <= year <= 9999
            or not 1 <= month <= 12
        ):
            raise ValidationError("Informe um mês e ano válidos para sincronizar.")
        return (
            date(year, month, 1).isoformat(),
            date(year, month, monthrange(year, month)[1]).isoformat(),
        )

    def get_transactions_for_account(self, pluggy_account_id, date_from=None, date_to=None):
        """Busca todas as páginas da conta, opcionalmente dentro de um mês."""
        api_key = self._get_api_key()

        endpoint = f"{self.base_url}/v2/transactions"
        url = endpoint
        params = {"accountId": pluggy_account_id}
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to

        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

        transactions = []
        visited = set()
        while True:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
            except requests.RequestException as error:
                raise APIError("Falha de conexão ao buscar transações na Pluggy.", 502) from error
            if response.status_code != 200:
                raise APIError("Falha ao buscar transações na API da Pluggy.", status_code=502)
            try:
                data = response.json()
            except ValueError as error:
                raise APIError("A Pluggy retornou uma resposta inválida.", 502) from error
            if not isinstance(data, dict) or not isinstance(data.get("results"), list):
                raise APIError("A Pluggy retornou uma lista de transações inválida.", 502)
            transactions.extend(data["results"])
            next_page = data.get("next")
            if next_page is None:
                break
            if (
                not isinstance(next_page, str)
                or not next_page.startswith("?")
                or next_page in visited
            ):
                raise APIError("A Pluggy retornou uma paginação inválida.", 502)
            visited.add(next_page)
            # O cursor já inclui os filtros; não deve ser reconstruído ou decodificado.
            url = endpoint + next_page
            params = None
        return transactions
