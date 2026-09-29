from models.account import Account
from repositories.account_repository import AccountRepository
from exceptions.api_errors import NotFoundError, ValidationError

class AccountService:
    def __init__(self):
        self.repository = AccountRepository()

    def get_accounts_by_user_id(self, user_id):
        return self.repository.get_by_user_id(user_id)

    def get_account_by_id(self, account_id, user_id):
        account = self.repository.get_by_id(account_id)
        
        if not account or account.user_id != user_id:
            raise NotFoundError("Conta não encontrada.")
            
        return account

    def sync_account(self, data, user_id):
        account_id = data.get("id")
        
        if not account_id:
            raise ValidationError("O 'id' da conta (fornecido pela API externa) é obrigatório.")

        existing_account = self.repository.get_by_id(account_id)

        if existing_account:
            # Proteção de segurança: garante que o UUID da API não está sendo atrelado a outro usuário
            if existing_account.user_id != user_id:
                raise ValidationError("Esta conta já está vinculada a outro usuário.")
            
            # Atualiza apenas os campos que podem mudar no dia a dia
            existing_account.balance = data.get("balance", existing_account.balance)
            existing_account.name = data.get("name", existing_account.name)
            existing_account.bankData = data.get("bankData", existing_account.bankData)
            existing_account.creditData = data.get("creditData", existing_account.creditData)
            
            return self.repository.update(existing_account)
            
        else:
            # Criação de nova conta (Validação dos campos obrigatórios da API externa)
            required_fields = ["type", "subtype", "itemId", "number", "name", "balance"]
            for field in required_fields:
                if data.get(field) is None:
                    raise ValidationError(f"O campo '{field}' é obrigatório para sincronizar nova conta.")

            new_account = Account(
                id=account_id,
                user_id=user_id,
                type=data.get("type"),
                subtype=data.get("subtype"),
                itemId=data.get("itemId"),
                number=data.get("number"),
                name=data.get("name"),
                marketingName=data.get("marketingName"),
                owner=data.get("owner"),
                taxNumber=data.get("taxNumber"),
                balance=data.get("balance", 0.0),
                currencyCode=data.get("currencyCode", "BRL"),
                bankData=data.get("bankData"),
                creditData=data.get("creditData")
            )
            
            return self.repository.create(new_account)

    def delete_account(self, account_id, user_id):
        account = self.repository.get_by_id(account_id)

        if not account or account.user_id != user_id:
            raise NotFoundError("Conta não encontrada.")

        self.repository.delete(account)