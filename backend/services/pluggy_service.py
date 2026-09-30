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