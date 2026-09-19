from models.user import User
from exceptions.api_errors import NotFoundError, ValidationError
from repositories.user_repository import UserRepository
from validators.email_validator import is_valid_email


class UserService:

    def __init__(self):
        self.repository = UserRepository()

    def get_all_users(self):
        return self.repository.get_all()

    def create_user(self, data):

        first_name = data.get("firstName")
        last_name = data.get("lastName")
        email = data.get("email")

        if not first_name:
            raise ValidationError("First name is required")

        if not last_name:
            raise ValidationError("Last name is required")

        if not is_valid_email(email):
            raise ValidationError("Invalid email")

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email
        )

        return self.repository.create(user)
    def update_user(self, user_id, data):

        first_name = data.get("firstName")
        last_name = data.get("lastName")
        email = data.get("email")

        if not first_name:
            raise ValidationError("First name is required")

        if not last_name:
            raise ValidationError("Last name is required")

        if not is_valid_email(email):
            raise ValidationError("Invalid email")

        user = self.repository.get_by_id(user_id)

        if not user:
            raise NotFoundError("User not found")

        user.first_name = first_name
        user.last_name = last_name
        user.email = email

        return self.repository.update(user)

    def delete_user(self, user_id):
        user = self.repository.get_by_id(user_id)

        if not user:
            raise NotFoundError("User not found")

        self.repository.delete(user)
    