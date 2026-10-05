"""Provisiona acessos pelo terminal local do administrador do servidor."""

import click
from werkzeug.security import generate_password_hash

from config import db
from exceptions.api_errors import APIError
from services.auth_service import AuthService
from services.user_service import UserService


def register_admin_commands(app):
    @app.cli.command("create-user")
    @click.option("--name", prompt="Nome")
    @click.option("--email", prompt="E-mail")
    def create_user(name, email):
        """Cria acesso verificado; a senha não entra no histórico do terminal."""
        password = click.prompt(
            "Senha (mínimo 12 caracteres)", hide_input=True, confirmation_prompt=True
        )
        try:
            UserService().create_user({"name": name, "email": email, "password": password})
        except APIError as error:
            raise click.ClickException(error.message) from error
        click.echo("Acesso criado. O usuário já pode entrar na aplicação.")

    @app.cli.command("reset-password")
    @click.option("--email", prompt="E-mail")
    def reset_password(email):
        """Recupera acesso localmente e revoga todas as sessões anteriores."""
        service = UserService()
        try:
            user = service.repository.get_by_email(service.normalize_email(email))
            if not user:
                raise click.ClickException("Usuário não encontrado.")
            password = click.prompt("Nova senha", hide_input=True, confirmation_prompt=True)
            service.validate_password(password)
        except APIError as error:
            raise click.ClickException(error.message) from error
        user.password = generate_password_hash(password)
        user.is_verified = True
        user.verification_code = None
        AuthService.revoke_user_sessions(user.id)
        db.session.commit()
        click.echo("Senha redefinida. Todas as sessões anteriores foram encerradas.")
