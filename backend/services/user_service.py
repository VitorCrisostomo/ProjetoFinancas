"""Cadastro administrativo, login e alterações do próprio perfil."""

import re

from werkzeug.security import check_password_hash, generate_password_hash

from config import db
from exceptions.api_errors import APIError, NotFoundError, ValidationError
from models.account import Account
from models.auth_session import AuthSession, UserSecurity
from models.category import Category, Subcategory
from models.transaction import Transaction
from models.transaction_sync_protection import TransactionSyncProtection
from models.user import User
from repositories.user_repository import UserRepository
from services.auth_service import AuthService

_DUMMY_PASSWORD_HASH = generate_password_hash("unused-password-for-timing-only")


class UserService:
    def __init__(self):
        self.repository = UserRepository()

    @staticmethod
    def normalize_email(email):
        if not isinstance(email, str) or len(email) > 120:
            raise ValidationError("Informe um e-mail válido.")
        email = email.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValidationError("Informe um e-mail válido.")
        return email

    @staticmethod
    def validate_password(password):
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            raise ValidationError("A senha deve ter entre 12 e 128 caracteres.")
        return password

    @staticmethod
    def validate_name(name):
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
            raise ValidationError("Informe um nome entre 1 e 100 caracteres.")
        return name.strip()

    def authenticate_user(self, data):
        if not isinstance(data, dict):
            raise ValidationError("Informe e-mail e senha.")
        email = self.normalize_email(data.get("email"))
        password = data.get("password")
        if not isinstance(password, str) or not 1 <= len(password) <= 128:
            raise ValidationError("Informe e-mail e senha.")
        user = self.repository.get_by_email(email)
        valid = check_password_hash(user.password if user else _DUMMY_PASSWORD_HASH, password)
        if not user or not valid or not user.is_verified:
            raise APIError("E-mail ou senha incorretos.", 401)
        return user

    def create_user(self, data, commit=True):
        """Usado somente pelo comando local do administrador, sem rota pública."""
        if not isinstance(data, dict):
            raise ValidationError("Informe os dados do usuário.")
        name = self.validate_name(data.get("name"))
        email = self.normalize_email(data.get("email"))
        password = self.validate_password(data.get("password"))
        if self.repository.get_by_email(email):
            raise ValidationError("Este e-mail já está em uso.")
        return self.repository.create(
            User(
                name=name,
                email=email,
                password=generate_password_hash(password),
                is_verified=True,
                verification_code=None,
            ),
            commit=commit,
        )

    def get_own_user(self, user_id, current_user_id):
        if user_id != current_user_id:
            raise NotFoundError("Usuário não encontrado.")
        user = self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("Usuário não encontrado.")
        return user

    @staticmethod
    def require_current_password(user, data):
        password = data.get("current_password")
        if (
            not isinstance(password, str)
            or not 1 <= len(password) <= 128
            or not check_password_hash(user.password, password)
        ):
            raise APIError("Confirme sua senha atual para esta operação.", 403)

    def update_user(self, user_id, data, current_user_id):
        user = self.get_own_user(user_id, current_user_id)
        if not isinstance(data, dict) or not data:
            raise ValidationError("Informe os campos que deseja alterar.")
        if set(data) - {"name", "firstName", "password", "current_password"}:
            raise ValidationError("Campos de atualização não permitidos.")
        self.require_current_password(user, data)
        name = data.get("name", data.get("firstName"))
        if "name" in data or "firstName" in data:
            name = self.validate_name(name)
        password = self.validate_password(data["password"]) if "password" in data else None
        if name is None and password is None:
            raise ValidationError("Informe um nome ou uma nova senha.")
        if name is not None:
            user.name = name
        if password is not None:
            user.password = generate_password_hash(password)
            AuthService.revoke_user_sessions(user_id)
        return self.repository.update(user)

    def delete_user(self, user_id, data, current_user_id):
        """Exclui apenas o próprio perfil e seus dependentes, em uma operação."""
        user = self.get_own_user(user_id, current_user_id)
        if not isinstance(data, dict):
            raise ValidationError("Confirme sua senha atual.")
        self.require_current_password(user, data)
        try:
            category_ids = db.session.query(Category.id).filter_by(user_id=user_id)
            Subcategory.query.filter(Subcategory.category_id.in_(category_ids)).delete(
                synchronize_session=False
            )
            Category.query.filter_by(user_id=user_id).delete()
            TransactionSyncProtection.query.filter_by(user_id=user_id).delete()
            Transaction.query.filter_by(user_id=user_id).delete()
            Account.query.filter_by(user_id=user_id).delete()
            AuthSession.query.filter_by(user_id=user_id).delete()
            UserSecurity.query.filter_by(user_id=user_id).delete()
            self.repository.delete(user)
        except Exception:
            db.session.rollback()
            raise
