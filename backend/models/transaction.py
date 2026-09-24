from config import db


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    description = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def to_json(self):
        return {
            "id": self.id,
            "value": float(self.value),
            "date": self.date.isoformat() if self.date else None,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "type": self.type,
            "user_id": self.user_id
        }
