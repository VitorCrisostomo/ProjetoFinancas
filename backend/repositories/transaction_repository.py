"""Consulta e persiste transações utilizando a sessão do SQLAlchemy."""

from sqlalchemy import inspect, select, text

from config import db
from models.transaction import Transaction
from models.transaction_sync_protection import TransactionSyncProtection


class TransactionRepository:
    """Operações de transações; cada escrita confirma a sessão atual."""

    @staticmethod
    def initialize_subcategory_column():
        """Adiciona a classificação opcional aos bancos existentes sem alterar o histórico."""
        with db.engine.begin() as connection:
            inspector = inspect(connection)
            if not inspector.has_table(Transaction.__tablename__):
                return
            if "subcategory" not in {
                column["name"] for column in inspector.get_columns("transactions")
            }:
                connection.execute(
                    text("ALTER TABLE transactions ADD COLUMN subcategory VARCHAR(50)")
                )

    @staticmethod
    def initialize_sync_protection():
        """Cria a proteção e preserva o histórico existente somente na primeira execução."""
        with db.engine.begin() as connection:
            inspector = inspect(connection)
            table = TransactionSyncProtection.__table__
            if inspector.has_table(table.name):
                return
            db.metadata.create_all(connection)
            if inspector.has_table(Transaction.__tablename__):
                existing = (
                    select(Transaction.user_id, Transaction.external_id)
                    .where(Transaction.external_id.is_not(None))
                    .distinct()
                )
                connection.execute(table.insert().from_select(["user_id", "external_id"], existing))

    def protect_from_sync(self, transaction):
        """Prepara a proteção; a escrita é confirmada junto com a edição ou associação."""
        if transaction.external_id and not self.is_sync_protected(
            transaction.user_id, transaction.external_id
        ):
            db.session.add(
                TransactionSyncProtection(
                    user_id=transaction.user_id, external_id=transaction.external_id
                )
            )

    def is_sync_protected(self, user_id, external_id):
        return db.session.get(TransactionSyncProtection, (user_id, external_id)) is not None

    def get_all(self):
        return Transaction.query.all()

    def get_by_user_id(self, user_id):
        return Transaction.query.filter_by(user_id=user_id).all()

    def get_by_id(self, contact_id):
        return Transaction.query.get(contact_id)

    def create(self, contact):
        db.session.add(contact)
        db.session.commit()
        return contact

    def update(self, contact, commit=True):
        if commit:
            db.session.commit()
        return contact

    def delete(self, contact):
        db.session.delete(contact)
        db.session.commit()
