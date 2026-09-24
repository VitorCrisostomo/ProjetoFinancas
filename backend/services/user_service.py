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
        # 1. Agora pegamos o email diretamente
        email = data.get("email") 
        password = data.get("password")

        if not email:
            raise ValidationError("Email is required")

        if not password:
            raise ValidationError("Password is required")

        user = self.repository.get_by_email(email) 

        if not user or not self.check_password(user, password):
            raise ValidationError("Email ou senha incorretos")

        return user

    def create_user(self, data):
        name = data.get("name")
        email = data.get("email") # 1. Pega o email
        password = data.get("password")

        if not name:
            raise ValidationError("Name is required")
        
        if not email:
            raise ValidationError("Email is required")
            
        if not password:
            raise ValidationError("Password is required")

        existing_user = self.repository.get_by_email(email)
        if existing_user:
            raise ValidationError("Este email já está em uso")

        hashed_password = generate_password_hash(password)

        # 4. Cria o usuário com o novo campo email
        user = User(
            name=name, 
            email=email, 
            password=hashed_password
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
    