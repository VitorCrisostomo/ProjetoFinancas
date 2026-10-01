"""Define os dados persistidos das contas integradas à Pluggy."""

from config import db


class Account(db.Model):
    """Conta bancária ou cartão identificado pelo UUID externo."""

    __tablename__ = "accounts"

    # Identificador único (UUID) fornecido pela API externa
    id = db.Column(db.String(36), primary_key=True)

    # Relação com o seu usuário interno do FinanceHub
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Campos principais e de classificação
    type = db.Column(db.String(50), nullable=False)  # Ex: BANK, CREDIT
    subtype = db.Column(db.String(50), nullable=False)  # Ex: CHECKING_ACCOUNT, CREDIT_CARD
    itemId = db.Column(db.String(36), nullable=False)  # ID do item de conexão

    # Detalhes da conta
    number = db.Column(db.String(50), nullable=False)  # Conta ou últimos 4 dígitos do cartão
    name = db.Column(db.String(100), nullable=False)
    marketingName = db.Column(db.String(100), nullable=True)
    owner = db.Column(db.String(100), nullable=True)
    taxNumber = db.Column(db.String(30), nullable=True)  # CPF/CNPJ

    # Valores financeiros
    balance = db.Column(db.Float, nullable=False, default=0.0)
    currencyCode = db.Column(db.String(10), nullable=False, default="BRL")

    # Campos JSON para armazenar dados dinâmicos dependendo do tipo da conta
    bankData = db.Column(db.JSON, nullable=True)
    creditData = db.Column(db.JSON, nullable=True)

    def to_json(self):
        """Retorna os campos utilizados nas respostas JSON da API."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "subtype": self.subtype,
            "number": self.number,
            "name": self.name,
            "marketingName": self.marketingName,
            "balance": self.balance,
            "itemId": self.itemId,
            "taxNumber": self.taxNumber,
            "owner": self.owner,
            "currencyCode": self.currencyCode,
            "bankData": self.bankData,
            "creditData": self.creditData,
        }
