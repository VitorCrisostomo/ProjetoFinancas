from config import app, db
from routes.user_route import user_routes
from routes.transaction_route import transaction_routes

app.register_blueprint(user_routes)
app.register_blueprint(transaction_routes)


if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(debug=True)