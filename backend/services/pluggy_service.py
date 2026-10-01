"""Comunica o backend com a API da Pluggy."""

import os
from calendar import monthrange
from datetime import date

import requests

from exceptions.api_errors import APIError, ValidationError


class PluggyService:
    """Autenticação e consulta de dados na API externa da Pluggy."""

    def __init__(self):
        self.client_id = os.getenv("PLUGGY_CLIENT_ID")
        self.client_secret = os.getenv("PLUGGY_CLIENT_SECRET")
        self.base_url = "https://api.pluggy.ai"

    def _get_api_key(self):
        """Autentica as credenciais configuradas e retorna a chave da API."""
        url = f"{self.base_url}/auth"
        payload = {"clientId": self.client_id, "clientSecret": self.client_secret}

        try:
            response = requests.post(url, json=payload, timeout=30)
        except requests.RequestException as error:
            raise APIError("Falha de conexão ao autenticar com a Pluggy.", 502) from error

        if response.status_code != 200:
            print(" ERRO DA PLUGGY:", response.text)
            raise APIError("Falha ao autenticar com a API da Pluggy.", status_code=500)

        return response.json().get("apiKey")

    def get_connect_token(self):
        """Solicita o token utilizado pelo widget Pluggy Connect."""
        api_key = self._get_api_key()
        url = f"{self.base_url}/connect_token"

        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

        response = requests.post(url, headers=headers)

        if response.status_code != 200:
            raise APIError("Falha ao gerar o Connect Token da Pluggy.", status_code=500)

        return response.json().get("accessToken")

    def get_accounts_from_item(self, item_id):
        """Busca todas as contas atreladas a uma conexão (itemId) na Pluggy."""
        api_key = self._get_api_key()

        url = f"{self.base_url}/accounts?itemId={item_id}"

        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise APIError("Falha ao buscar contas na API da Pluggy.", status_code=500)

        return response.json().get("results", [])

    def sync_item_accounts(self, item_id, user_id, account_service):
        """Busca contas do item e delega sua persistência ao serviço de contas."""
        if not item_id:
            raise APIError("O itemId é obrigatório.", status_code=400)

        pluggy_accounts_data = self.get_accounts_from_item(item_id)

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
