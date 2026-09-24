import csv
import io


from datetime import datetime
from models.transaction import Transaction
from exceptions.api_errors import NotFoundError, ValidationError
from repositories.transaction_repository import TransactionRepository
from datetime import datetime

class TransactionService:

    def __init__(self):
        self.repository = TransactionRepository()

    def get_all_transactions(self):
        return self.repository.get_all()

    def get_transactions_by_user_id(self, user_id):
        return self.repository.get_by_user_id(user_id)

    def create_transaction(self, data):
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
            type=type_trans
        )

        return self.repository.create(transaction)
    
    def update_transaction(self, transaction_id, data):
        value = data.get("value")
        date_str = data.get("date") # 1. Pega a data como string
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

        transaction = self.repository.get_by_id(transaction_id)

        if not transaction:
            raise NotFoundError("Transaction not found")

        transaction.value = value
        transaction.date = date_obj
        transaction.name = name
        transaction.category = category
        transaction.description = description
        transaction.user_id = user_id
        transaction.type = type_trans 

        return self.repository.update(transaction)

    def import_csv(self, file, user_id):
        if file.filename == '':
            raise ValidationError("O arquivo recebido não possui nome.")

        if not file.filename.endswith('.csv'):
            raise ValidationError("O arquivo deve ser no formato .csv.")

        try:
            raw_data = file.stream.read()
            try:
                decoded_content = raw_data.decode("utf-8-sig") 
            except UnicodeDecodeError:
                decoded_content = raw_data.decode("latin-1")

            stream = io.StringIO(decoded_content, newline=None)
            
            primeira_linha = stream.readline()
            delimitador = ';' if ';' in primeira_linha else ','
            stream.seek(0)
            
            csv_reader = csv.DictReader(stream, delimiter=delimitador) 
            
            imported_count = 0

            for row_number, row in enumerate(csv_reader, start=2): 
                
                # 1. Limpa as chaves (cabeçalho)
                clean_row = {}
                for key, value in row.items():
                    if key is not None:
                        clean_key = key.replace('\ufeff', '').strip()
                        clean_row[clean_key] = value

                nome_lancamento = clean_row.get("Lançamento", "").strip()
                raw_date = clean_row.get("Data", "").strip()

                # 2. Ignora linhas de fechamento do Banco do Brasil
                if (not nome_lancamento or 
                    nome_lancamento in ["Saldo Anterior", "Saldo do dia", "Saldo Atual"] or 
                    raw_date == "00/00/0000"):
                    continue

                if not raw_date:
                    raise ValidationError(f"A coluna 'Data' não foi encontrada ou está vazia na linha {row_number}.")

                # 3. Converte a Data (AQUI ESTAVA FALTANDO!)
                try:
                    parsed_date = datetime.strptime(raw_date, "%d/%m/%Y").strftime("%Y-%m-%d")
                except ValueError:
                    raise ValidationError(f"Erro na linha {row_number}: A data '{raw_date}' não está no formato esperado (DD/MM/YYYY).")

                # 4. Formata o Valor
                raw_value = clean_row.get("Valor", "0")
                clean_value = raw_value.replace(".", "").replace(",", ".")
                try:
                    float_value = abs(float(clean_value))
                except ValueError:
                    float_value = 0.0

                # 5. Descobre se é Entrada ou Saída
                tipo_lancamento = clean_row.get("Tipo Lançamento", "").strip().lower()
                if "entrada" in tipo_lancamento:
                    transaction_type = "income"
                else:
                    transaction_type = "expense"

                # 6. Prepara a descrição
                descricao = clean_row.get("Detalhes", "").strip()
                doc = clean_row.get("N° documento", "").strip()
                if doc:
                    descricao = f"{descricao} (Doc: {doc})".strip()

                # 7. Monta o pacote final e cria a transação
                data = {
                    "user_id": user_id,
                    "date": parsed_date,
                    "name": nome_lancamento,
                    "category": "Importado",
                    "type": transaction_type,
                    "value": float_value,
                    "description": descricao
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

        self.repository.delete(transaction)
    