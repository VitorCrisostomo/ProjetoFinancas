"""Inicializa as rotas e executa o servidor de desenvolvimento."""

from flask import jsonify

from config import app, db, jwt
from repositories.transaction_repository import TransactionRepository
from routes.account_routes import account_routes
from routes.category_routes import category_routes
from routes.pluggy_route import pluggy_routes
from routes.transaction_route import transaction_routes
from routes.user_route import user_routes
from services.admin_commands import register_admin_commands
from services.auth_service import configure_authentication
from services.category_service import CategoryService
from services.database_encryption_service import (
    ensure_encrypted_schema,
    register_encryption_commands,
)

app.register_blueprint(user_routes)
app.register_blueprint(transaction_routes)
app.register_blueprint(pluggy_routes)
app.register_blueprint(account_routes)
app.register_blueprint(category_routes)
configure_authentication(app, jwt)
register_admin_commands(app)
register_encryption_commands(app)


@app.before_request
def require_encrypted_storage():
    """Também impede WSGI de atender antes da migração financeira."""
    if not app.config.get("FINANCIAL_SCHEMA_READY", False):
        try:
            ensure_encrypted_schema()
        except RuntimeError:
            return jsonify(
                {"message": "Banco em manutenção. Execute a migração de criptografia."}
            ), 503
        app.config["FINANCIAL_SCHEMA_READY"] = True


def initialize_database():
    """Inicialização explícita e idempotente, também disponível para WSGI."""
    with app.app_context():
        ensure_encrypted_schema()
        TransactionRepository.initialize_sync_protection()
        db.create_all()
        TransactionRepository.initialize_subcategory_column()
        CategoryService().migrate_leisure_category()


@app.cli.command("init-db")
def init_db_command():
    initialize_database()


if __name__ == "__main__":
    # Os imports registram os modelos no metadata antes da criação das tabelas.
    from models.account import Account  # noqa: F401
    from models.transaction import Transaction  # noqa: F401
    from models.user import User  # noqa: F401

    initialize_database()
    app.run(debug=app.config.get("DEBUG", False))
