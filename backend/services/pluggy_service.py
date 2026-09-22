import os
import requests
from dotenv import load_dotenv

load_dotenv()


class PluggyService:

    BASE_URL = "https://api.pluggy.ai"

    def get_api_key(self):
        client_id = os.getenv("PLUGGY_CLIENT_ID")
        client_secret = os.getenv("PLUGGY_CLIENT_SECRET")

        response = requests.post(
            f"{self.BASE_URL}/auth",
            json={
                "clientId": client_id,
                "clientSecret": client_secret
            }
        )

        response.raise_for_status()

        return response.json()["apiKey"]

    def create_connect_token(self, client_user_id=None):

        api_key = self.get_api_key()

        payload = {
            "options": {
                "avoidDuplicates": True
            }
        }

        if client_user_id:
            payload["options"]["clientUserId"] = str(client_user_id)

        response = requests.post(
            f"{self.BASE_URL}/connect_token",
            headers={
                "Content-Type": "application/json",
                "X-API-KEY": api_key
            },
            json=payload
        )

        response.raise_for_status()

        return response.json()["accessToken"]