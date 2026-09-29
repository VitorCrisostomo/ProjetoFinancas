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