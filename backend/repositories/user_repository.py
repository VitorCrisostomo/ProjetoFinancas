"""Consulta e persiste usuários utilizando a sessão do SQLAlchemy."""

from sqlalchemy import func

from config import db
from models.user import User


class UserRepository:
    """Operações de usuários; cada escrita confirma a sessão atual."""

    def get_by_id(self, user_id):
        return db.session.get(User, user_id)

    def get_by_email(self, email):
        return User.query.filter(func.lower(User.email) == email.lower()).first()

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
