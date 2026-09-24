import random

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
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        if not name or not email or not password:
            raise ValidationError("Preencha todos os campos")

        existing_user = self.repository.get_by_email(email)
        if existing_user:
            # Se já existir E já estiver verificado, aí sim damos erro
            if existing_user.is_verified:
                raise ValidationError("Este email já está em uso")
            else:
                # O usuário fechou a aba antes de verificar! 
                # Vamos atualizar a senha dele e gerar um NOVO código!
                code = str(random.randint(100000, 999999))
                existing_user.name = name
                existing_user.password = generate_password_hash(password)
                existing_user.verification_code = code
                
                self.repository.update(existing_user)
                
                print("\n" + "="*50)
                print(f"📧 NOVO EMAIL SIMULADO PARA: {email}")
                print(f"Seu novo código FinanceHub é: {code}")
                print("="*50 + "\n")
                
                return existing_user

        hashed_password = generate_password_hash(password)
        
        code = str(random.randint(100000, 999999))

        user = User(
            name=name, 
            email=email, 
            password=hashed_password,
            is_verified=False,
            verification_code=code
        )
        
        created_user = self.repository.create(user)
        
        # SIMULA O ENVIO DO EMAIL
        print("\n" + "="*50)
        print(f"📧 EMAIL SIMULADO PARA: {email}")
        print(f"Seu código de verificação FinanceHub é: {code}")
        print("="*50 + "\n")

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
        email = data.get("email")
        code = data.get("code")

        user = self.repository.get_by_email(email)
        
        if not user:
            raise NotFoundError("Usuário não encontrado")
            
        if user.is_verified:
            raise ValidationError("Esta conta já está verificada")
            
        if user.verification_code != code:
            raise ValidationError("Código inválido. Tente novamente.")
            
        # Se o código estiver certo, ativamos a conta e apagamos o código!
        user.is_verified = True
        user.verification_code = None
        self.repository.update(user)
        
        return user
    