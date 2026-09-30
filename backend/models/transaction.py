from config import db
from datetime import datetime

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(100), unique=True, nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=True)
    value = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    type = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def to_json(self):
        return {
            "id": self.id,
            "external_id": self.external_id,
            "account_id": self.account_id,
            "value": float(self.value),
            "date": self.date.isoformat() if self.date else None,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "type": self.type,
            "user_id": self.user_id
        }