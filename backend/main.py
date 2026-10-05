"""Inicializa as rotas e executa o servidor de desenvolvimento."""

from config import app, db
from repositories.transaction_repository import TransactionRepository
from routes.account_routes import account_routes
from routes.category_routes import category_routes
from routes.pluggy_route import pluggy_routes
from routes.transaction_route import transaction_routes
from routes.user_route import user_routes
from services.category_service import CategoryService

app.register_blueprint(user_routes)
app.register_blueprint(transaction_routes)
app.register_blueprint(pluggy_routes)
app.register_blueprint(account_routes)
app.register_blueprint(category_routes)

if __name__ == "__main__":
    # Os imports registram os modelos no metadata antes da criação das tabelas.
    from models.account import Account  # noqa: F401
    from models.transaction import Transaction  # noqa: F401
    from models.user import User  # noqa: F401

    with app.app_context():
        TransactionRepository.initialize_sync_protection()
        db.create_all()
        TransactionRepository.initialize_subcategory_column()
        CategoryService().migrate_leisure_category()

    app.run(debug=True)
