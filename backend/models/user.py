from config import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=False, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def to_json(self):
        return {
            "id": self.id,
            "username": self.username,
        }
 