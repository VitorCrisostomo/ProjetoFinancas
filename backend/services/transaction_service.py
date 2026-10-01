"""Valida transações, importa CSV e adapta dados da Pluggy."""

import csv
import io
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from config import db
from exceptions.api_errors import NotFoundError, ValidationError
from models.account import Account
from models.transaction import Transaction
from repositories.transaction_repository import TransactionRepository


class TransactionService:
    """Regras de lançamentos manuais, importação e sincronização."""

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

    def create_transaction(self, data):
        """Valida os campos e cria um lançamento com data YYYY-MM-DD."""
        value = data.get("value")
        date_str = data.get("date")
        name = data.get("name")
        category = data.get("category")
        description = data.get("description")
        user_id = data.get("user_id")

        type_trans = data.get("type")

        if not value:
            raise ValidationError("Value is required")
        if not date_str:
            raise ValidationError("Date is required")

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Formato de data inválido. Use YYYY-MM-DD")

        if not name:
            raise ValidationError("Name is required")
        if not user_id:
            raise ValidationError("UserId is required")
        if not category:
            raise ValidationError("Category is required")

        if not type_trans:
            type_trans = "expense"

        if not description:
            description = ""

        transaction = Transaction(
            user_id=user_id,
            value=value,
            date=date_obj,
            name=name,
            category=category,
            description=description,
            type=type_trans,
        )

        return self.repository.create(transaction)

    def update_transaction(self, transaction_id, data, commit=True):
        """Atualiza os campos fornecidos de uma transação existente."""
        transaction = self.repository.get_by_id(transaction_id)

        if not transaction:
            raise NotFoundError("Transaction not found")

        if transaction.is_opening_balance:
            raise ValidationError("O saldo anterior automático é recalculado pela aplicação.")

        if "value" in data:
            if not data["value"]:
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

        if "category" in data:
            if not data["category"]:
                raise ValidationError("Category is required")
            transaction.category = data["category"]

        if "description" in data:
            transaction.description = data["description"]

        if "type" in data:
            if not data["type"]:
                transaction.type = "expense"
            else:
                transaction.type = data["type"]

        if any(key in data for key in ("value", "date", "name", "category", "description", "type")):
            self.repository.protect_from_sync(transaction)
        return self.repository.update(transaction, commit=commit)

    def associate_transaction(self, user_id, keep_id, remove_id, updated_data):
        """Associa atomicamente e protege os dois identificadores externos."""
        if keep_id == remove_id:
            raise ValidationError("Selecione duas transações diferentes para associar.")
        t1 = self.repository.get_by_id(keep_id)
        t2 = self.repository.get_by_id(remove_id)

        if not t1 or t1.user_id != user_id or not t2 or t2.user_id != user_id:
            raise NotFoundError("Transações não encontradas ou não pertencem ao usuário")

        if t1.is_opening_balance or t2.is_opening_balance:
            raise ValidationError("O saldo anterior automático não pode ser associado.")

        try:
            updated_transaction = self.update_transaction(keep_id, updated_data, commit=False)
            self.repository.protect_from_sync(t1)
            self.repository.protect_from_sync(t2)
            db.session.delete(t2)
            db.session.commit()
            return updated_transaction
        except Exception:
            db.session.rollback()
            raise

    def import_csv(self, file, user_id):
        """Importa o extrato CSV; cada linha válida é persistida individualmente."""
        if file.filename == "":
            raise ValidationError("O arquivo recebido não possui nome.")

        if not file.filename.endswith(".csv"):
            raise ValidationError("O arquivo deve ser no formato .csv.")

        try:
            raw_data = file.stream.read()
            # Tenta decodificar como UTF-8 primeiro, se der erro tenta Latin-1 (padrão Windows)
            try:
                decoded_content = raw_data.decode("utf-8-sig")
            except UnicodeDecodeError:
                decoded_content = raw_data.decode("latin-1")

            stream = io.StringIO(decoded_content, newline=None)

            # Descobre se o banco usou vírgula ou ponto-e-vírgula para separar as colunas
            primeira_linha = stream.readline()
            delimitador = ";" if ";" in primeira_linha else ","
            stream.seek(0)

            csv_reader = csv.DictReader(stream, delimiter=delimitador)

            imported_count = 0

            for row_number, row in enumerate(csv_reader, start=2):
                clean_row = {}
                for key, value in row.items():
                    if key is not None:
                        clean_key = key.replace("\ufeff", "").strip()
                        clean_row[clean_key] = value

                nome_lancamento = clean_row.get("Lançamento", "").strip()
                raw_date = clean_row.get("Data", "").strip()

                nome_limpo_para_teste = nome_lancamento.upper().replace(" ", "")

                if (
                    not nome_lancamento
                    or nome_limpo_para_teste
                    in ["SALDODODIA", "SALDOATUAL", "SALDO", "SALDOANTERIOR"]
                    or raw_date == "00/00/0000"
                ):
                    continue

                if not raw_date:
                    raise ValidationError(
                        f"A coluna 'Data' não foi encontrada ou está vazia na linha {row_number}."
                    )

                try:
                    parsed_date = datetime.strptime(raw_date, "%d/%m/%Y").strftime("%Y-%m-%d")
                except ValueError:
                    raise ValidationError(
                        f"Erro na linha {row_number}: A data '{raw_date}' não está no formato esperado (DD/MM/YYYY)."
                    )

                raw_value = clean_row.get("Valor", "0")
                clean_value = raw_value.replace(".", "").replace(",", ".")

                try:
                    parsed_float = float(clean_value)
                    float_value = abs(parsed_float)
                except ValueError:
                    parsed_float = 0.0
                    float_value = 0.0

                # Usa o tipo explícito do extrato; na ausência, usa o sinal do valor.
                tipo_lancamento = clean_row.get("Tipo Lançamento", "").strip().lower()

                if tipo_lancamento:
                    if "entrada" in tipo_lancamento:
                        transaction_type = "income"
                    else:
                        transaction_type = "expense"
                else:
                    if parsed_float >= 0:
                        transaction_type = "income"
                    else:
                        transaction_type = "expense"

                descricao = clean_row.get("Detalhes", "").strip()
                doc = clean_row.get("N° documento", "").strip()
                if doc:
                    descricao = f"{descricao} (Doc: {doc})".strip()

                data = {
                    "user_id": user_id,
                    "date": parsed_date,
                    "name": nome_lancamento,
                    "category": "Importado",
                    "type": transaction_type,
                    "value": float_value,
                    "description": descricao,
                }

                self.create_transaction(data)
                imported_count += 1

            return imported_count

        except ValidationError as ve:
            raise ve
        except Exception as e:
            raise ValidationError(f"Erro inesperado ao processar arquivo: {str(e)}")

    def delete_transaction(self, transaction_id):
        transaction = self.repository.get_by_id(transaction_id)

        if not transaction:
            raise NotFoundError("Transaction not found")

        if transaction.is_opening_balance:
            raise ValidationError("O saldo anterior automático não pode ser excluído.")

        self.repository.delete(transaction)

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
            # Entretenimento
            "Shopping": "Compras",
            "Clothing": "Compras",
            "Tickets": "Entretenimento",
            "Leisure": "Entretenimento",
            "Cinema, theater and concerts": "Entretenimento",
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
            "Digital services": "Entretenimento",
        }

        return category_map.get(pluggy_category, "Extra")

    def sync_transaction(self, tx_data, internal_account_id, user_id):
        """Cria ou atualiza o lançamento externo com valor absoluto e tipo normalizado."""
        pluggy_tx_id = tx_data.get("id")

        if not pluggy_tx_id:
            return None

        # Inclui identificadores de lançamentos removidos em associações anteriores.
        if self.repository.is_sync_protected(user_id, pluggy_tx_id):
            return None

        # O identificador externo permite atualizar lançamentos já sincronizados.
        existing_tx = Transaction.query.filter_by(external_id=pluggy_tx_id).first()
        if existing_tx and existing_tx.user_id != user_id:
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
        account = Account.query.get(internal_account_id)
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

        name = tx_data.get("description") or tx_data.get("merchant", {}).get(
            "name", "Transação Pluggy"
        )
        pluggy_category = tx_data.get("category")
        category = self.map_category(pluggy_category, app_type)
        description = tx_data.get("observation", "")

        if existing_tx:
            existing_tx.value = amount
            existing_tx.date = parsed_date
            existing_tx.name = name
            existing_tx.category = category
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
