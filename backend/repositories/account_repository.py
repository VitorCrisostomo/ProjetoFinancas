"""Consulta e persiste contas utilizando a sessão do SQLAlchemy."""

from config import db
from models.account import Account


class AccountRepository:
    """Operações de contas; cada escrita confirma a sessão atual."""

    def create(self, account: Account, commit=True) -> Account:
        db.session.add(account)
        if commit:
            db.session.commit()
        return account

    def get_by_id(self, account_id: str) -> Account:
        return Account.query.get(account_id)

    def get_by_user_id(self, user_id: int) -> list:
        return Account.query.filter_by(user_id=user_id).all()

    def get_by_item_id(self, item_id: str) -> list:
        return Account.query.filter_by(itemId=item_id).all()

    def update(self, account: Account, commit=True) -> Account:
        if commit:
            db.session.commit()
        return account

    def delete(self, account: Account) -> None:
        db.session.delete(account)
        db.session.commit()
