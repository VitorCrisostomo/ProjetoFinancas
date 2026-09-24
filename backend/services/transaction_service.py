from models.transaction import Transaction
from exceptions.api_errors import NotFoundError, ValidationError
from repositories.transaction_repository import TransactionRepository
from datetime import datetime

class TransactionService:

    def __init__(self):
        self.repository = TransactionRepository()

    def get_all_transactions(self):
        return self.repository.get_all()

    def get_transactions_by_user_id(self, user_id):
        return self.repository.get_by_user_id(user_id)

    def create_transaction(self, data):
        value = data.get("value")
        date_str = data.get("date")
        name = data.get("name")
        category = data.get("category")
        description = data.get("description")
        user_id = data.get("user_id")
        
        # 👇 ADICIONADO AQUI: Pegar o tipo que o React enviou
        type_trans = data.get("type") 

        if not value:
            raise ValidationError("Value is required")
        if not date_str:
            raise ValidationError("Date is required")

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Formato de data inválido. Use YYYY-MM-DD")

        if not name:
            raise ValidationError("Name is required")
        if not user_id:
            raise ValidationError("UserId is required")
        if not category:
            raise ValidationError("Category is required")
            
        # Se por acaso não vier o tipo, assumimos que é despesa
        if not type_trans:
            type_trans = "expense"
            
        if not description:
            description = ""

        transaction = Transaction(
            user_id=user_id,
            value=value,
            date=date_obj,
            name=name,
            category=category,
            description=description,
            type=type_trans
        )

        return self.repository.create(transaction)
    
    def update_transaction(self, transaction_id, data):
        value = data.get("value")
        date_str = data.get("date") # 1. Pega a data como string
        name = data.get("name")
        category = data.get("category")
        description = data.get("description")
        user_id = data.get("user_id")
        
        type_trans = data.get("type")

        if not value:
            raise ValidationError("Value is required")

        if not date_str:
            raise ValidationError("Date is required")

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Formato de data inválido. Use YYYY-MM-DD")

        if not name:
            raise ValidationError("Name is required")

        if not user_id:
            raise ValidationError("UserId is required")

        if not category:
            raise ValidationError("Category is required")

        if not type_trans:
            type_trans = "expense"

        if not description:
            description = ""

        transaction = self.repository.get_by_id(transaction_id)

        if not transaction:
            raise NotFoundError("Transaction not found")

        transaction.value = value
        transaction.date = date_obj # Atualiza com a data convertida
        transaction.name = name
        transaction.category = category
        transaction.description = description
        transaction.user_id = user_id
        
        # 👇 3. Atualizamos a propriedade "type" no banco de dados!
        transaction.type = type_trans 

        return self.repository.update(transaction)

    def delete_transaction(self, transaction_id):
        transaction = self.repository.get_by_id(transaction_id)

        if not transaction:
            raise NotFoundError("Transaction not found")

        self.repository.delete(transaction)
    