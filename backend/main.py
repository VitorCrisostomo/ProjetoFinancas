"""Inicializa as rotas e executa o servidor de desenvolvimento."""

from config import app, db
from routes.account_routes import account_routes
from routes.pluggy_route import pluggy_routes
from routes.transaction_route import transaction_routes
from routes.user_route import user_routes

app.register_blueprint(user_routes)
app.register_blueprint(transaction_routes)
app.register_blueprint(pluggy_routes)
app.register_blueprint(account_routes)

if __name__ == "__main__":
    # Os imports registram os modelos no metadata antes da criação das tabelas.
    from models.account import Account  # noqa: F401
    from models.transaction import Transaction  # noqa: F401
    from models.user import User  # noqa: F401

    with app.app_context():
        db.create_all()

    app.run(debug=True)
