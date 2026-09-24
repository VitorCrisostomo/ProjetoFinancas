from werkzeug.security import generate_password_hash, check_password_hash

from models.user import User
from exceptions.api_errors import NotFoundError, ValidationError
from repositories.user_repository import UserRepository
from validators.email_validator import is_valid_email


class UserService:

    def __init__(self):
        self.repository = UserRepository()

    def get_all_users(self):
        return self.repository.get_all()

    def authenticate_user(self, data):
        # Agora ele aceita username, name OU email!
        username = data.get("username") or data.get("name") or data.get("email")
        password = data.get("password")

        if not username:
            raise ValidationError("Username (ou Email) is required")

        if not password:
            raise ValidationError("Password is required")

        # Atenção: verifique se o seu repositório busca por email ou username.
        # Se for email, talvez precise mudar de get_by_username para get_by_email
        user = self.repository.get_by_username(username) 

        if not user or not self.check_password(user, password):
            raise ValidationError("Nome ou senha incorretos")

        return user

    def create_user(self, username, password):

        if not username:
            raise ValidationError("UserName is required")

        if not password:
            raise ValidationError("Password is required")

        password_hash = generate_password_hash(password)

        user = User(
            username=username,
            password=password_hash
        )

        return self.repository.create(user)

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
    