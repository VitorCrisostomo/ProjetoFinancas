from models.user import User
from models.transaction import Transaction
from config import db


class TransactionRepository:

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