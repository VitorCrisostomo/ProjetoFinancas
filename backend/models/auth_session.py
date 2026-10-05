"""Estado persistente de sessões, tentativas de login e identidade bancária."""

from uuid import uuid4

from config import db


class AuthSession(db.Model):
    """Uma sessão pode ser revogada independentemente do navegador."""

    __tablename__ = "auth_sessions"

    jti = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    expires_at = db.Column(db.BigInteger, nullable=False, index=True)
    credential_digest = db.Column(db.String(64), nullable=False)
    revoked = db.Column(db.Boolean, nullable=False, default=False)


class LoginAttempt(db.Model):
    """Falhas recentes, sem e-mail, endereço IP ou senha em claro."""

    __tablename__ = "login_attempts"

    id = db.Column(db.Integer, primary_key=True)
    email_key = db.Column(db.String(64), nullable=False, index=True)
    address_key = db.Column(db.String(64), nullable=False, index=True)
    occurred_at = db.Column(db.BigInteger, nullable=False, index=True)


class UserSecurity(db.Model):
    """Referência estável; um ID numérico reutilizado não herda conexões."""

    __tablename__ = "user_security"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    pluggy_reference = db.Column(
        db.String(36), nullable=False, unique=True, default=lambda: str(uuid4())
    )
