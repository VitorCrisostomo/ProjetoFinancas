"""Preserva identificadores externos editados ou incorporados em associações."""

from config import db


class TransactionSyncProtection(db.Model):
    """O registro permanece mesmo se o lançamento associado for excluído."""

    __tablename__ = "transaction_sync_protections"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    external_id = db.Column(db.String(100), primary_key=True)
