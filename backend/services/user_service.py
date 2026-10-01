"""Implementa cadastro, autenticação e verificação de usuários."""

import random

from werkzeug.security import check_password_hash, generate_password_hash

from exceptions.api_errors import NotFoundError, ValidationError
from models.user import User
from repositories.user_repository import UserRepository


class UserService:
    """Regras de cadastro, login e verificação de usuários."""

    def __init__(self):
        self.repository = UserRepository()

    def get_all_users(self):
        return self.repository.get_all()

    def authenticate_user(self, data):
        """Valida as credenciais e exige que o cadastro esteja verificado."""
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            raise ValidationError("Email e senha são obrigatórios")

        user = self.repository.get_by_email(email)

        if not user or not self.check_password(user, password):
            raise ValidationError("Email ou senha incorretos")

        if not user.is_verified:
            raise ValidationError("Por favor, verifique seu e-mail antes de fazer login.")

        return user

    def create_user(self, data):
        """Cria ou renova cadastro pendente e imprime o código no terminal."""
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        if not name or not email or not password:
            raise ValidationError("Preencha todos os campos")

        existing_user = self.repository.get_by_email(email)
        if existing_user:
            # Cadastros verificados não podem ser recriados com o mesmo e-mail.
            if existing_user.is_verified:
                raise ValidationError("Este email já está em uso")
            else:
                # Cadastros pendentes recebem novos dados e um novo código.

                code = str(random.randint(100000, 999999))
                existing_user.name = name
                existing_user.password = generate_password_hash(password)
                existing_user.verification_code = code

                self.repository.update(existing_user)

                print("\n" + "=" * 50)
                print(f"📧 NOVO EMAIL SIMULADO PARA: {email}")
                print(f"Seu novo código FinanceHub é: {code}")
                print("=" * 50 + "\n")

                return existing_user

        hashed_password = generate_password_hash(password)

        code = str(random.randint(100000, 999999))

        user = User(
            name=name,
            email=email,
            password=hashed_password,
            is_verified=False,
            verification_code=code,
        )

        created_user = self.repository.create(user)

        # O envio de e-mail é simulado pelo código impresso no terminal.
        print("\n" + "=" * 50)
        print(f"📧 EMAIL SIMULADO PARA: {email}")
        print(f"Seu código de verificação FinanceHub é: {code}")
        print("=" * 50 + "\n")

        return created_user

    def check_password(self, user, password):
        return check_password_hash(user.password, password)

    def update_user(self, user_id, data):

        username = data.get("firstName")
        password = data.get("password")

        if not username:
            raise ValidationError("First name is required")

        if not password:
            raise ValidationError("Password is invalid")

        user = self.repository.get_by_id(user_id)

        if not user:
            raise NotFoundError("User not found")

        user.username = username
        user.password = password

        return self.repository.update(user)

    def delete_user(self, user_id):
        user = self.repository.get_by_id(user_id)

        if not user:
            raise NotFoundError("User not found")

        self.repository.delete(user)

    def verify_account(self, data):
        """Confirma o código do cadastro e remove o código após a verificação."""
        email = data.get("email")
        code = data.get("code")

        user = self.repository.get_by_email(email)

        if not user:
            raise NotFoundError("Usuário não encontrado")

        if user.is_verified:
            raise ValidationError("Esta conta já está verificada")

        if user.verification_code != code:
            raise ValidationError("Código inválido. Tente novamente.")

        # O código é descartado após a confirmação do cadastro.
        user.is_verified = True
        user.verification_code = None
        self.repository.update(user)

        return user
