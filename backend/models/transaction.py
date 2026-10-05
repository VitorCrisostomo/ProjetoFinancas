"""Lançamentos financeiros com conteúdo criptografado e vínculos indexáveis."""

from config import db
from models.encrypted_record import EncryptedRecord, encrypted_field, register_encryption_events


class Transaction(EncryptedRecord, db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(100), unique=True, nullable=True)
    account_id = db.Column(db.String(36), db.ForeignKey("accounts.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    _binding_fields = ("id", "user_id", "account_id", "external_id")
    _bind_generated_id = True
    _number_fields = ("value",)
    _json_fields = ()
    _required_fields = ("value", "date", "name", "type")
    _defaults = {
        "value": None,
        "date": None,
        "name": None,
        "category": None,
        "subcategory": None,
        "description": None,
        "type": None,
    }

    value = encrypted_field("value")
    date = encrypted_field("date")
    name = encrypted_field("name")
    category = encrypted_field("category")
    subcategory = encrypted_field("subcategory")
    description = encrypted_field("description")
    type = encrypted_field("type")

    @property
    def is_opening_balance(self):
        return bool(self.external_id and self.external_id.startswith("opening-balance:"))

    def to_json(self):
        return {
            "id": self.id,
            "external_id": self.external_id,
            "account_id": self.account_id,
            "value": float(self.value),
            "date": self.date.isoformat() if self.date else None,
            "name": self.name,
            "category": self.category,
            "subcategory": self.subcategory,
            "description": self.description,
            "type": self.type,
            "user_id": self.user_id,
            "is_opening_balance": self.is_opening_balance,
        }


register_encryption_events(Transaction)
