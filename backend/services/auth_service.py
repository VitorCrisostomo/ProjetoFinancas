"""Emite e revoga sessões, valida usuários ativos e limita tentativas de login."""

import hashlib
import hmac
import time

from flask import current_app, jsonify, request
from flask_jwt_extended import create_access_token, decode_token
from sqlalchemy.exc import IntegrityError

from config import db
from exceptions.api_errors import APIError
from models.auth_session import AuthSession, LoginAttempt, UserSecurity
from models.user import User


class AuthService:
    @staticmethod
    def digest(value):
        return hmac.new(
            current_app.config["JWT_SECRET_KEY"].encode(), value.encode(), hashlib.sha256
        ).hexdigest()

    def create_session(self, user):
        token = create_access_token(identity=str(user.id))
        claims = decode_token(token)
        AuthSession.query.filter(AuthSession.expires_at <= int(time.time())).delete()
        db.session.add(
            AuthSession(
                jti=claims["jti"],
                user_id=user.id,
                expires_at=claims["exp"],
                credential_digest=self.digest(user.password),
            )
        )
        db.session.commit()
        return token, claims["csrf"]

    @staticmethod
    def revoke_session(jti):
        session = db.session.get(AuthSession, jti)
        if session:
            session.revoked = True
            db.session.commit()

    @staticmethod
    def revoke_user_sessions(user_id):
        """Participa da mesma confirmação da mudança de senha."""
        AuthSession.query.filter_by(user_id=user_id).update({"revoked": True})

    def check_login_limit(self, email, address):
        threshold = int(time.time()) - current_app.config["AUTH_LOGIN_WINDOW_SECONDS"]
        recent = LoginAttempt.query.filter(LoginAttempt.occurred_at > threshold)
        email_count = recent.filter_by(email_key=self.digest(email)).count()
        address_count = recent.filter_by(address_key=self.digest(address)).count()
        if (
            email_count >= current_app.config["AUTH_LOGIN_EMAIL_LIMIT"]
            or address_count >= current_app.config["AUTH_LOGIN_ADDRESS_LIMIT"]
        ):
            raise APIError("Muitas tentativas de login. Aguarde 15 minutos e tente novamente.", 429)

    def record_login_failure(self, email, address):
        now = int(time.time())
        LoginAttempt.query.filter(
            LoginAttempt.occurred_at <= now - current_app.config["AUTH_LOGIN_WINDOW_SECONDS"]
        ).delete()
        db.session.add(
            LoginAttempt(
                email_key=self.digest(email),
                address_key=self.digest(address),
                occurred_at=now,
            )
        )
        db.session.commit()

    @staticmethod
    def get_pluggy_reference(user_id, commit=True):
        security = db.session.get(UserSecurity, user_id)
        if not security:
            security = UserSecurity(user_id=user_id)
            db.session.add(security)
            if not commit:
                db.session.flush()
                return security.pluggy_reference
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                security = db.session.get(UserSecurity, user_id)
                if security is None:
                    raise
        return security.pluggy_reference


def configure_authentication(app, jwt):
    """Registra validação persistente para todas as rotas com jwt_required."""

    @jwt.token_in_blocklist_loader
    def is_revoked(_header, claims):
        identity = claims.get("sub")
        if not isinstance(identity, str) or not identity.isdecimal():
            return True
        session = db.session.get(AuthSession, claims["jti"])
        user = db.session.get(User, int(identity))
        return (
            session is None
            or session.revoked
            or session.expires_at <= int(time.time())
            or session.user_id != int(identity)
            or user is None
            or not user.is_verified
            or not hmac.compare_digest(session.credential_digest, AuthService.digest(user.password))
        )

    @jwt.user_lookup_loader
    def load_user(_header, claims):
        return db.session.get(User, int(claims["sub"]))

    def unauthorized(*_args):
        return jsonify({"message": "Sessão inválida ou expirada. Entre novamente."}), 401

    jwt.unauthorized_loader(unauthorized)
    jwt.invalid_token_loader(unauthorized)
    jwt.expired_token_loader(unauthorized)
    jwt.revoked_token_loader(unauthorized)
    jwt.user_lookup_error_loader(unauthorized)

    @app.before_request
    def check_request_origin():
        # CORS sozinho não impede o servidor de executar uma requisição indevida.
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("Origin")
            if origin and origin not in app.config["AUTH_ALLOWED_ORIGINS"]:
                return jsonify({"message": "Origem da requisição não autorizada."}), 403

    @app.after_request
    def protect_responses(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
