"""Valida edições e associações e adapta dados da Pluggy."""

from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from config import db
from exceptions.api_errors import NotFoundError, ValidationError
from models.account import Account
from models.transaction import Transaction
from repositories.transaction_repository import TransactionRepository
from services.category_service import CategoryService


def _contains_reserve_reference(value):
    """Reconhece a referência em campos textuais, inclusive dados aninhados do banco."""
    if isinstance(value, str):
        return "RF RESERVA COFR" in " ".join(value.upper().split())
    if isinstance(value, dict):
        return any(_contains_reserve_reference(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_reserve_reference(item) for item in value)
    return False


class TransactionService:
    """Regras de edição, associação, saldo anterior e sincronização bancária."""

    def __init__(self):
        self.repository = TransactionRepository()

    def get_all_transactions(self):
        return self.repository.get_all()

    def get_transactions_by_user_id(self, user_id):
        return self.repository.get_by_user_id(user_id)

    def reconcile_opening_balance(self, account, commit=True, reference_date=None):
        """Reconcilia a conta com um único ajuste anterior ao histórico armazenado."""
        transactions = Transaction.query.filter_by(
            account_id=account.id, user_id=account.user_id
        ).all()
        movements = [
            transaction for transaction in transactions if not transaction.is_opening_balance
        ]
        opening = next(
            (transaction for transaction in transactions if transaction.is_opening_balance), None
        )
        cents = Decimal("0.01")
        net = sum(
            (
                Decimal(str(transaction.value)) * (1 if transaction.type == "income" else -1)
                for transaction in movements
            ),
            Decimal(0),
        )
        adjustment = (Decimal(str(account.balance)) - net).quantize(cents, rounding=ROUND_HALF_UP)
        if not adjustment.is_finite():
            raise ValidationError("O saldo da conta deve ser um valor válido.")

        # Sem lançamentos nesta conta, usa o início do histórico do usuário ou o mês atual.
        history = movements or [
            transaction
            for transaction in self.repository.get_by_user_id(account.user_id)
            if not transaction.is_opening_balance
        ]
        oldest = min(
            (transaction.date.date() for transaction in history if transaction.date),
            default=reference_date or date.today(),
        )
        opening_date = datetime.combine(oldest.replace(day=1) - timedelta(days=1), time.min)
        if opening is None:
            opening = Transaction(
                external_id=f"opening-balance:{account.id}",
                account_id=account.id,
                user_id=account.user_id,
            )
            db.session.add(opening)
        opening.value = float(abs(adjustment))
        opening.type = "income" if adjustment >= 0 else "expense"
        opening.date = opening_date
        opening.name = f"Saldo anterior — {account.name}"
        opening.category = "Saldo anterior"
        opening.description = (
            "Ajuste automático: saldo informado pela instituição menos as movimentações salvas. "
            "É uma estimativa com base no histórico disponível."
        )
        if commit:
            db.session.commit()
        return opening

    def update_transaction(self, transaction_id, data, user_id=None):
        """Permite editar nome, data e classificação, preservando os dados bancários."""
        if (
            not isinstance(data, dict)
            or not data
            or set(data) - {"name", "date", "category", "subcategory"}
        ):
            raise ValidationError(
                "Somente nome, data, categoria e subcategoria podem ser atualizados."
            )
        transaction = self.repository.get_by_id(transaction_id)
        if not transaction or (user_id is not None and transaction.user_id != user_id):
            raise NotFoundError("Transaction not found")
        return self._update_transaction(transaction_id, data)

    def _update_transaction(self, transaction_id, data, commit=True):
        """Atualiza os campos fornecidos de uma transação existente."""
        transaction = self.repository.get_by_id(transaction_id)

        if not transaction:
            raise NotFoundError("Transaction not found")

        if transaction.is_opening_balance:
            raise ValidationError("O saldo anterior automático é recalculado pela aplicação.")

        classification = None
        if "category" in data or "subcategory" in data:
            category = data.get("category", transaction.category)
            subcategory = data.get(
                "subcategory", transaction.subcategory if category == transaction.category else None
            )
            classification = CategoryService().validate_classification(
                transaction.user_id, category, subcategory
            )

        if "value" in data:
            if data["value"] is None or data["value"] == "" or isinstance(data["value"], bool):
                raise ValidationError("Value is required")
            transaction.value = data["value"]

        if "date" in data:
            if not data["date"]:
                raise ValidationError("Date is required")
            try:
                transaction.date = datetime.strptime(data["date"], "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError("Formato de data inválido. Use YYYY-MM-DD")

        if "name" in data:
            if not data["name"]:
                raise ValidationError("Name is required")
            transaction.name = data["name"]

        if classification is not None:
            transaction.category, transaction.subcategory = classification

        if "description" in data:
            transaction.description = data["description"]

        if "type" in data:
            if not data["type"]:
                transaction.type = "expense"
            else:
                transaction.type = data["type"]

        if any(
            key in data
            for key in ("value", "date", "name", "category", "subcategory", "description", "type")
        ):
            self.repository.protect_from_sync(transaction)
        return self.repository.update(transaction, commit=commit)

    def associate_transaction(self, user_id, keep_id, remove_id, updated_data):
        """Mantém compatibilidade com a associação anterior de dois lançamentos."""
        return self._associate_transactions(user_id, [keep_id, remove_id], updated_data)

    def associate_transactions(self, user_id, transaction_ids, updated_data):
        """Associa dois ou mais lançamentos e calcula seu saldo no backend."""
        return self._associate_transactions(user_id, transaction_ids, updated_data, calculate=True)

    def _associate_transactions(self, user_id, transaction_ids, updated_data, calculate=False):
        if (
            not isinstance(transaction_ids, list)
            or len(transaction_ids) < 2
            or any(type(transaction_id) is not int for transaction_id in transaction_ids)
            or len(set(transaction_ids)) != len(transaction_ids)
        ):
            raise ValidationError("Selecione pelo menos duas transações diferentes para associar.")
        if not isinstance(updated_data, dict):
            raise ValidationError("Informe os dados da associação.")
        transactions = [
            self.repository.get_by_id(transaction_id) for transaction_id in transaction_ids
        ]
        if any(
            transaction is None or transaction.user_id != user_id for transaction in transactions
        ):
            raise NotFoundError("Transações não encontradas ou não pertencem ao usuário")
        if any(transaction.is_opening_balance for transaction in transactions):
            raise ValidationError("O saldo anterior automático não pode ser associado.")
        kept = transactions[0]
        try:
            if calculate:
                requested_data = updated_data
                net = sum(
                    (
                        Decimal(str(transaction.value)).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                        * (1 if transaction.type == "income" else -1)
                        for transaction in transactions
                    ),
                    Decimal(0),
                )
                updated_data = {
                    "name": " / ".join(transaction.name for transaction in transactions)[:120],
                    "category": kept.category,
                    "subcategory": kept.subcategory,
                    "date": kept.date.strftime("%Y-%m-%d"),
                    **{
                        key: value
                        for key, value in updated_data.items()
                        if key in ("name", "category", "subcategory", "date")
                    },
                    "value": float(abs(net)),
                    "type": "income" if net >= 0 else "expense",
                }
                if (
                    updated_data["category"] != kept.category
                    and "subcategory" not in requested_data
                ):
                    updated_data["subcategory"] = None
            updated_transaction = self._update_transaction(kept.id, updated_data, commit=False)
            for transaction in transactions:
                self.repository.protect_from_sync(transaction)
            for transaction in transactions[1:]:
                db.session.delete(transaction)
            db.session.commit()
            return updated_transaction
        except Exception:
            db.session.rollback()
            raise

    def map_category(self, pluggy_category, transaction_type):
        """Mapeia a categoria externa; categorias desconhecidas retornam Extra."""
        category_map = {
            # Alimentação
            "Groceries": "Alimentação",
            "Food delivery": "Alimentação",
            "Eating out": "Alimentação",
            "Food and drinks": "Alimentação",
            # Moradia
            "Housing": "Moradia",
            "Houseware": "Moradia",
            "Services": "Moradia",
            # Transporte
            "Taxi and ride-hailing": "Transporte",
            "Gas stations": "Transporte",
            "Parking": "Transporte",
            "Automotive": "Transporte",
            "Vehicle maintenance": "Transporte",
            # Lazer
            "Shopping": "Compras",
            "Clothing": "Compras",
            "Tickets": "Lazer",
            "Leisure": "Lazer",
            "Cinema, theater and concerts": "Lazer",
            # Saúde
            "Pharmacy": "Saúde",
            "Pet supplies and vet": "Saúde",
            # Educação
            "Bookstore": "Educação",
            # Receitas
            "Entrepreneurial activities": "Extra",
            # Categorias que não representam uma despesa específica
            "Transfer - PIX": "Transferência",
            "Third party transfer - PIX": "Transferência",
            "Transfers": "Transferência",
            "Same person transfer": "Transferência",
            "Fixed income": "Extra",
            # Outros tipos de despesa
            "Bank fees": "Taxas e Impostos",
            "Late payment and overdraft costs": "Taxas e Impostos",
            "Telecommunications": "Taxas e Impostos",
            "Internet": "Taxas e Impostos",
            "Digital services": "Lazer",
        }

        return category_map.get(pluggy_category, "Extra")

    def sync_transaction(self, tx_data, internal_account_id, user_id):
        """Cria ou atualiza o lançamento externo com valor absoluto e tipo normalizado."""
        account = db.session.get(Account, internal_account_id)
        if not account or account.user_id != user_id:
            raise NotFoundError("Conta não encontrada.")
        if tx_data.get("accountId") not in (None, internal_account_id):
            raise ValidationError("A transação não pertence à conta sincronizada.")
        pluggy_tx_id = tx_data.get("id")

        if not pluggy_tx_id:
            return None

        # Inclui identificadores de lançamentos removidos em associações anteriores.
        if self.repository.is_sync_protected(user_id, pluggy_tx_id):
            return None

        # O identificador externo permite atualizar lançamentos já sincronizados.
        existing_tx = Transaction.query.filter_by(external_id=pluggy_tx_id).first()
        if existing_tx and (
            existing_tx.user_id != user_id or existing_tx.account_id != internal_account_id
        ):
            return None

        # Datas ausentes ou inválidas mantêm a data UTC utilizada como fallback.
        raw_date = tx_data.get("date")
        parsed_date = datetime.utcnow()
        if raw_date:
            try:
                parsed_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except Exception:
                pass

        # A classificação depende do tipo de conta.
        is_credit_card = account and account.type and account.type.upper() == "CREDIT"

        pluggy_type = tx_data.get("type", "DEBIT").upper()
        amount_raw = float(tx_data.get("amount", 0.0))

        description_lower = (tx_data.get("description", "") or "").lower()
        merchant_field = tx_data.get("merchant")
        merchant_name = ""
        if merchant_field and isinstance(merchant_field, dict):
            merchant_name = (merchant_field.get("name", "") or "").lower()
        full_text = f"{description_lower} {merchant_name}"

        # Termos que indicam entrada/reembolso mesmo em cartão de crédito
        is_payment_or_refund = any(
            term in full_text
            for term in [
                "pagamento",
                "fatura",
                "estorno",
                "cashback",
                "pix recebido",
                "transferência recebida",
            ]
        )

        # Aplica as regras de receita e despesa para cada tipo de conta.
        if is_credit_card:
            # Em cartão de crédito, o normal é ser despesa, a menos que seja pagamento de fatura ou estorno
            if is_payment_or_refund:
                app_type = "income"
            else:
                app_type = "expense"
        else:
            # Conta corrente / poupança tradicional
            if pluggy_type == "CREDIT" or amount_raw > 0:
                app_type = "income"
            else:
                app_type = "expense"

        # O valor absoluto é armazenado; income/expense representa a direção.
        amount = abs(amount_raw)

        merchant = merchant_field if isinstance(merchant_field, dict) else {}
        name = (
            tx_data.get("description")
            or tx_data.get("name")
            or merchant.get("name")
            or "Transação Pluggy"
        )
        pluggy_category = tx_data.get("category")
        category = (
            "Investimentos"
            if _contains_reserve_reference(tx_data)
            else self.map_category(pluggy_category, app_type)
        )
        description = tx_data.get("observation", "")

        if existing_tx:
            existing_tx.value = amount
            existing_tx.date = parsed_date
            existing_tx.name = name
            existing_tx.category = category
            existing_tx.subcategory = None
            existing_tx.description = description
            existing_tx.type = app_type
            db.session.commit()
            return existing_tx

        # Cria nova transação
        new_tx = Transaction(
            external_id=pluggy_tx_id,
            account_id=internal_account_id,
            user_id=user_id,
            value=amount,
            date=parsed_date,
            name=name,
            category=category,
            description=description,
            type=app_type,
        )

        db.session.add(new_tx)
        db.session.commit()
        return new_tx
