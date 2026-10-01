"""Define usuários e o estado de verificação do cadastro."""

from config import db


class User(db.Model):
    """Usuário e dados de verificação; campos sensíveis não são serializados."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    is_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6), nullable=True)

    def to_json(self):
        """Retorna os campos utilizados nas respostas JSON da API."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_verified": self.is_verified,
        }
