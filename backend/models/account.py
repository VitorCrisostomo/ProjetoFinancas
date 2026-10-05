"""Contas com saldos, dados bancários e dados pessoais criptografados."""

from config import db
from models.encrypted_record import EncryptedRecord, encrypted_field, register_encryption_events


class Account(EncryptedRecord, db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    itemId = db.Column(db.String(36), nullable=False)

    _binding_fields = ("id", "user_id", "itemId")
    _number_fields = ("balance",)
    _json_fields = ("bankData", "creditData")
    _required_fields = ("type", "subtype", "number", "name", "balance", "currencyCode")
    _defaults = {
        "type": None,
        "subtype": None,
        "number": None,
        "name": None,
        "marketingName": None,
        "owner": None,
        "taxNumber": None,
        "balance": 0.0,
        "currencyCode": "BRL",
        "bankData": None,
        "creditData": None,
    }

    type = encrypted_field("type")
    subtype = encrypted_field("subtype")
    number = encrypted_field("number")
    name = encrypted_field("name")
    marketingName = encrypted_field("marketingName")
    owner = encrypted_field("owner")
    taxNumber = encrypted_field("taxNumber")
    balance = encrypted_field("balance")
    currencyCode = encrypted_field("currencyCode")
    bankData = encrypted_field("bankData")
    creditData = encrypted_field("creditData")

    def to_json(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "itemId": self.itemId,
            **{name: getattr(self, name) for name in self._defaults},
        }


register_encryption_events(Account)
