import os
import requests
from exceptions.api_errors import APIError

class PluggyService:
    def __init__(self):
        self.client_id = os.getenv("PLUGGY_CLIENT_ID")
        self.client_secret = os.getenv("PLUGGY_CLIENT_SECRET")
        self.base_url = "https://api.pluggy.ai"

    def _get_api_key(self):
        url = f"{self.base_url}/auth"
        payload = {
            "clientId": self.client_id,
            "clientSecret": self.client_secret
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            print(" ERRO DA PLUGGY:", response.text)
            raise APIError("Falha ao autenticar com a API da Pluggy.", status_code=500)
            
        return response.json().get("apiKey")

    def get_connect_token(self):
        api_key = self._get_api_key()
        url = f"{self.base_url}/connect_token"
        
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers)
        
        if response.status_code != 200:
            raise APIError("Falha ao gerar o Connect Token da Pluggy.", status_code=500)
            
        return response.json().get("accessToken")

    def get_accounts_from_item(self, item_id):
        """Busca todas as contas atreladas a uma conexão (itemId) na Pluggy."""
        api_key = self._get_api_key()
        
        url = f"{self.base_url}/accounts?itemId={item_id}"
        
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            raise APIError("Falha ao buscar contas na API da Pluggy.", status_code=500)
            
        return response.json().get("results", [])

    def sync_item_accounts(self, item_id, user_id, account_service):
        if not item_id:
            raise APIError("O itemId é obrigatório.", status_code=400)
            
        pluggy_accounts_data = self.get_accounts_from_item(item_id)
        
        synced_accounts = []
        for acc_data in pluggy_accounts_data:
            synced_acc = account_service.sync_account(acc_data, user_id)
            synced_accounts.append(synced_acc.to_json())
            
        return synced_accounts

    def get_transactions_for_account(self, pluggy_account_id):
        """Busca TODAS as transações de uma conta na Pluggy v2, lidando com paginação por cursor."""
        api_key = self._get_api_key()
        
        all_transactions = []
        url = f"{self.base_url}/v2/transactions?accountId={pluggy_account_id}"
        
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        
        # Loop para buscar todas as páginas usando o cursor da Pluggy v2
        while url:
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                print(f"🚨 ERRO DA PLUGGY (Transações): Status {response.status_code} - {response.text}")
                raise APIError(f"Falha ao buscar transações na API da Pluggy: {response.text}", status_code=500)
                
            data = response.json()
            results = data.get("results", [])
            all_transactions.extend(results)
            
            # Verifica se existe uma próxima página (next cursor)
            # A Pluggy v2 costuma retornar 'next' ou 'totalPages'/'cursor' na resposta de paginação
            # Verifique a estrutura exata da v2 da Pluggy ou utilize o campo de paginação retornado:
            next_cursor = data.get("next")
            if next_cursor:
                # Se 'next' vier como URL completa ou token, ajustamos:
                if next_cursor.startswith("http"):
                    url = next_cursor
                else:
                    url = f"{self.base_url}/v2/transactions?accountId={pluggy_account_id}&cursor={next_cursor}"
            else:
                url = None
                
        return all_transactions