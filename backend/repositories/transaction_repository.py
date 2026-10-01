"""Consulta e persiste transações utilizando a sessão do SQLAlchemy."""

from config import db
from models.transaction import Transaction


class TransactionRepository:
    """Operações de transações; cada escrita confirma a sessão atual."""

    def get_all(self):
        return Transaction.query.all()

    def get_by_user_id(self, user_id):
        return Transaction.query.filter_by(user_id=user_id).all()

    def get_by_id(self, contact_id):
        return Transaction.query.get(contact_id)

    def create(self, contact):
        db.session.add(contact)
        db.session.commit()
        return contact

    def update(self, contact):
        db.session.commit()
        return contact

    def delete(self, contact):
        db.session.delete(contact)
        db.session.commit()
