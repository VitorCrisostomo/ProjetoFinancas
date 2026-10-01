"""Consulta e persiste usuários utilizando a sessão do SQLAlchemy."""

from config import db
from models.user import User


class UserRepository:
    """Operações de usuários; cada escrita confirma a sessão atual."""

    def get_all(self):
        return User.query.all()

    def get_by_username(self, username):
        return User.query.filter_by(username=username).first()

    def get_by_id(self, user_id):
        return User.query.get(user_id)

    def get_by_email(self, email):
        return User.query.filter_by(email=email).first()

    def create(self, user):
        db.session.add(user)
        db.session.commit()
        return user

    def update(self, user):
        db.session.commit()
        return user

    def delete(self, user):
        db.session.delete(user)
        db.session.commit()
