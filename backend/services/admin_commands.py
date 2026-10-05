"""Provisiona acessos pelo terminal local do administrador do servidor."""

import click
from werkzeug.security import generate_password_hash

from config import db
from exceptions.api_errors import APIError
from services.auth_service import AuthService
from services.pluggy_credentials import PluggyCredentialsStore
from services.user_service import UserService


def prompt_pluggy_credentials():
    # Também oculta o identificador para não expor o par nos registros do terminal.
    client_id = click.prompt("Pluggy Client ID", hide_input=True)
    client_secret = click.prompt("Pluggy Client Secret", hide_input=True, confirmation_prompt=True)
    return PluggyCredentialsStore.validate(client_id, client_secret)


def find_user(email):
    service = UserService()
    user = service.repository.get_by_email(service.normalize_email(email))
    if not user:
        raise click.ClickException("Usuário não encontrado.")
    return user


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
            client_id, client_secret = prompt_pluggy_credentials()
            user = UserService().create_user(
                {"name": name, "email": email, "password": password}, commit=False
            )
            reference = AuthService.get_pluggy_reference(user.id, commit=False)
            with PluggyCredentialsStore().change(reference, client_id, client_secret):
                db.session.commit()
        except APIError as error:
            db.session.rollback()
            raise click.ClickException(error.message) from error
        except Exception:
            db.session.rollback()
            raise click.ClickException(
                "Não foi possível criar o acesso e salvar a integração."
            ) from None
        click.echo("Acesso criado. Credenciais individuais da Pluggy salvas no .env.")

    @app.cli.command("reset-password")
    @click.option("--email", prompt="E-mail")
    def reset_password(email):
        """Recupera acesso localmente e revoga todas as sessões anteriores."""
        try:
            user = find_user(email)
            password = click.prompt("Nova senha", hide_input=True, confirmation_prompt=True)
            UserService.validate_password(password)
            change_credentials = click.confirm(
                "Alterar também as credenciais da Pluggy?", default=False
            )
            credentials = prompt_pluggy_credentials() if change_credentials else None
            user.password = generate_password_hash(password)
            user.is_verified = True
            user.verification_code = None
            AuthService.revoke_user_sessions(user.id)
            if credentials:
                reference = AuthService.get_pluggy_reference(user.id, commit=False)
                with PluggyCredentialsStore().change(reference, *credentials):
                    db.session.commit()
            else:
                db.session.commit()
        except APIError as error:
            db.session.rollback()
            raise click.ClickException(error.message) from error
        except click.ClickException:
            db.session.rollback()
            raise
        except Exception:
            db.session.rollback()
            raise click.ClickException(
                "Não foi possível atualizar o acesso e a integração."
            ) from None
        click.echo("Senha redefinida. Todas as sessões anteriores foram encerradas.")
        if credentials:
            click.echo("Credenciais individuais da Pluggy atualizadas no .env.")

    @app.cli.command("configure-pluggy")
    @click.option("--email", prompt="E-mail")
    def configure_pluggy(email):
        """Configura ou troca as chaves individuais sem alterar a senha do usuário."""
        try:
            user = find_user(email)
            credentials = prompt_pluggy_credentials()
            reference = AuthService.get_pluggy_reference(user.id, commit=False)
            with PluggyCredentialsStore().change(reference, *credentials):
                db.session.commit()
        except APIError as error:
            db.session.rollback()
            raise click.ClickException(error.message) from error
        except click.ClickException:
            db.session.rollback()
            raise
        except Exception:
            db.session.rollback()
            raise click.ClickException("Não foi possível salvar a integração no .env.") from None
        click.echo("Credenciais individuais da Pluggy atualizadas no .env.")
