from config import app, db

from routes.user_route import user_routes
from routes.transaction_route import transaction_routes
from routes.pluggy_route import pluggy_routes
from routes.account_routes import account_routes


app.register_blueprint(user_routes)
app.register_blueprint(transaction_routes)
app.register_blueprint(pluggy_routes)
app.register_blueprint(account_routes)

if __name__ == "__main__":
    
    from models.user import User
    from models.account import Account
    from models.transaction import Transaction

    with app.app_context():
        db.create_all()

    app.run(debug=True)