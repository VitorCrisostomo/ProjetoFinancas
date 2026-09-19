from config import db

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, unique=False, nullable=False)
    date = db.Column(db.DateTime, unique=False, nullable=False)
    name = db.Column(db.String(80), unique=False, nullable=False)
    category = db.Column(db.String(10), unique=False, nullable=False)
    description = db.Column(db.String(120), unique=False, nullable=False)

    def to_json(self):
        return {
            "id": self.id,
            "value": self.first_name,
            "date": self.last_name,
            "name": self.name,
            "category": self.category,
            "description": self.description
        }    