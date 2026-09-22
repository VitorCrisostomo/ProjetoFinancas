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

    def create_user(self, first_name, password):

        if not first_name:
            raise ValidationError("First name is required")

        if not password:
            raise ValidationError("Password is required")

        password_hash = generate_password_hash(password)

        user = User(
            first_name=first_name,
            password=password_hash
        )

        return self.repository.create(user)

    def check_password(self, user, password):
        return check_password_hash(user.password, password)
    
    def update_user(self, user_id, data):

        first_name = data.get("firstName")
        password = data.get("password")

        if not first_name:
            raise ValidationError("First name is required")

        if not password:
            raise ValidationError("Password is invalid")

        user = self.repository.get_by_id(user_id)

        if not user:
            raise NotFoundError("User not found")

        user.first_name = first_name
        user.password = password

        return self.repository.update(user)

    def delete_user(self, user_id):
        user = self.repository.get_by_id(user_id)

        if not user:
            raise NotFoundError("User not found")

        self.repository.delete(user)
    