from models.transaction import Transaction
from exceptions.api_errors import NotFoundError, ValidationError
from repositories.transaction_repository import TransactionRepository


class TransactionService:

    def __init__(self):
        self.repository = TransactionRepository()

    def get_all_transactions(self):
        return self.repository.get_all()

    def create_transaction(self, data):
        value = data.get("value")
        date = data.get("date")
        name = data.get("name")
        category = data.get("category")
        description = data.get("description")
        user_id = data.get("user_id")

        if not value:
            raise ValidationError("Value is required")

        if not date:
            raise ValidationError("Date is required")

        if not name:
            raise ValidationError("Name is required")

        if not user_id:
            raise ValidationError("UserId is required")

        if not category:
            category = "Others"

        if not description:
            description = ""

        transaction = Transaction(
            user_id=user_id,
            value=value,
            date=date,
            name=name,
            category=category,
            description=description
        )

        return self.repository.create(transaction)
    
    def update_transaction(self, transaction_id, data):

        value = data.get("value")
        date = data.get("date")
        name = data.get("name")
        category = data.get("category")
        description = data.get("description")
        user_id = data.get("user_id")

        if not value:
            raise ValidationError("Value is required")

        if not date:
            raise ValidationError("Date is required")

        if not name:
            raise ValidationError("Name is required")

        if not user_id:
            raise ValidationError("UserId is required")

        if not category:
            category = "Others"

        if not description:
            description = ""

        transaction = self.repository.get_by_id(transaction_id)

        if not transaction:
            raise NotFoundError("Transaction not found")

        transaction.value = value
        transaction.date = date
        transaction.name = name
        transaction.category = category
        transaction.description = description
        transaction.user_id = user_id

        return self.repository.update(transaction)

    def delete_transaction(self, transaction_id):
        transaction = self.repository.get_by_id(transaction_id)

        if not transaction:
            raise NotFoundError("Transaction not found")

        self.repository.delete(transaction)
    