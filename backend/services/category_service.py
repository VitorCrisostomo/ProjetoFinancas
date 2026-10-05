"""Criação, validação e compatibilidade das classificações financeiras."""

import unicodedata

from sqlalchemy.exc import IntegrityError

from config import db
from exceptions.api_errors import NotFoundError, ValidationError
from models.category import Category, Subcategory
from models.transaction import Transaction
from repositories.category_repository import CategoryRepository

DEFAULT_CATEGORIES = (
    "Salário",
    "Extra",
    "Transferência",
    "Alimentação",
    "Moradia",
    "Transporte",
    "Compras",
    "Lazer",
    "Saúde",
    "Educação",
    "Taxas e Impostos",
    "Esportes",
    "Investimentos",
)

# Lista fornecida pelo usuário a partir do BB; os nomes dos pais seguem o catálogo existente.
# Faturas não é criada. Despesas Pessoais / Vestuário corresponde a Compras.
DEFAULT_SUBCATEGORIES = {
    "Moradia": (
        "Aluguel / Prestação imobiliária",
        "Condomínio",
        "Água, Luz e Gás",
        "Internet / TV a Cabo",
        "Manutenção e Reformas",
    ),
    "Alimentação": (
        "Supermercado e Feira",
        "Restaurantes",
        "Delivery / Lanches",
        "Padaria e Cafés",
    ),
    "Transporte": (
        "Combustível",
        "Aplicativos de Transporte (Uber, 99)",
        "Transporte Público / Metrô",
        "Manutenção do Veículo / Seguro",
        "Estacionamento e Pedágio",
    ),
    "Saúde": (
        "Plano de Saúde",
        "Farmácia e Medicamentos",
        "Consultas e Exames",
        "Dentista",
    ),
    "Educação": (
        "Mensalidade Escolar / Faculdade",
        "Cursos e Certificações",
        "Livros e Material Didático",
    ),
    "Lazer": (
        "Cinema, Shows e Teatro",
        "Viagens e Hospedagem",
        "Bares e Festas",
        "Streaming e Assinaturas (Netflix, Spotify)",
    ),
    "Compras": (
        "Roupas e Calçados",
        "Salão de Beleza / Barbearia",
        "Cuidados Pessoais / Cosméticos",
        "Presentes",
    ),
    "Investimentos": ("Aplicações financeiras (Poupança, CDB, Fundos)",),
    "Taxas e Impostos": (
        "Tarifas Bancárias / Anuidade de Cartão",
        "Impostos (IPTU, IPVA, IR)",
        "Juros e IOF",
    ),
}


def category_name(value):
    """Normaliza o nome apresentado, mantendo os acentos e limitando seu tamanho."""
    if not isinstance(value, str):
        raise ValidationError("Informe um nome válido de até 50 caracteres.")
    name = " ".join(unicodedata.normalize("NFKC", value).split())
    if not name or len(name) > 50:
        raise ValidationError("Informe um nome válido de até 50 caracteres.")
    return name


class CategoryService:
    def __init__(self):
        self.repository = CategoryRepository()

    def migrate_leisure_category(self, user_id=None):
        """Renomeia o padrão antigo, preservando filhos e proteções de sincronização."""
        legacy = Category.query.filter_by(normalized_name="entretenimento")
        transactions = Transaction.query
        if user_id is not None:
            legacy = legacy.filter_by(user_id=user_id)
            transactions = transactions.filter_by(user_id=user_id)
        transactions = [
            transaction
            for transaction in transactions.all()
            if (transaction.category or "").casefold() == "entretenimento"
        ]
        for category in legacy.all():
            target = self.repository.get_by_name("lazer", category.user_id)
            if target is None:
                category.name = "Lazer"
                category.normalized_name = "lazer"
                continue
            children = {sub.normalized_name: sub for sub in target.subcategories}
            for sub in list(category.subcategories):
                duplicate = children.get(sub.normalized_name)
                if duplicate:
                    for transaction in transactions:
                        if (
                            transaction.user_id == category.user_id
                            and transaction.subcategory == sub.name
                        ):
                            transaction.subcategory = duplicate.name
                    db.session.delete(sub)
                else:
                    sub.category_id = target.id
            db.session.flush()
            db.session.expire(category, ["subcategories"])
            db.session.delete(category)
        for transaction in transactions:
            transaction.category = "Lazer"
        db.session.commit()

    def list_categories(self, user_id):
        """Acrescenta padrões e nomes históricos sem reclassificar transações."""
        self.migrate_leisure_category(user_id)
        existing = {
            category.normalized_name for category in self.repository.get_by_user_id(user_id)
        }
        historical = {
            transaction.category
            for transaction in Transaction.query.filter_by(user_id=user_id).all()
        }
        for name in (*DEFAULT_CATEGORIES, *historical):
            if not name or name == "Saldo anterior":
                continue
            normalized = name.casefold()
            if normalized not in existing:
                db.session.add(Category(user_id=user_id, name=name, normalized_name=normalized))
                existing.add(normalized)
        try:
            db.session.flush()
            defaults_by_name = {
                name.casefold(): children for name, children in DEFAULT_SUBCATEGORIES.items()
            }
            for category in self.repository.get_by_user_id(user_id):
                defaults = defaults_by_name.get(category.normalized_name, ())
                children = {sub.normalized_name for sub in category.subcategories}
                for name in defaults:
                    name = category_name(name)
                    if name.casefold() not in children:
                        db.session.add(
                            Subcategory(
                                category_id=category.id, name=name, normalized_name=name.casefold()
                            )
                        )
            db.session.commit()
        except IntegrityError:
            # Duas primeiras consultas simultâneas podem tentar cadastrar os mesmos padrões.
            db.session.rollback()
        return self.repository.get_by_user_id(user_id)

    def create_category(self, user_id, data):
        if not isinstance(data, dict):
            raise ValidationError("Informe o nome da categoria.")
        name = category_name(data.get("name"))
        if name.casefold() == "saldo anterior":
            raise ValidationError(
                "Saldo anterior é uma categoria reservada aos ajustes automáticos."
            )
        self.list_categories(user_id)
        if self.repository.get_by_name(name.casefold(), user_id):
            raise ValidationError("Já existe uma categoria com esse nome.")
        return self._save(Category(user_id=user_id, name=name, normalized_name=name.casefold()))

    def create_subcategory(self, user_id, category_id, data):
        category = self.repository.get_by_id(category_id, user_id)
        if category is None:
            raise NotFoundError("Categoria não encontrada.")
        if not isinstance(data, dict):
            raise ValidationError("Informe o nome da subcategoria.")
        name = category_name(data.get("name"))
        if any(sub.normalized_name == name.casefold() for sub in category.subcategories):
            raise ValidationError("Já existe uma subcategoria com esse nome nesta categoria.")
        self._save(Subcategory(category_id=category.id, name=name, normalized_name=name.casefold()))
        db.session.expire(category, ["subcategories"])
        return category

    def _save(self, record):
        try:
            return self.repository.save(record)
        except IntegrityError as error:
            db.session.rollback()
            raise ValidationError("Esse nome já está cadastrado.") from error

    def validate_classification(self, user_id, category, subcategory):
        """Uma subcategoria só pode pertencer à categoria do próprio usuário."""
        name = category_name(category)
        parent = self.repository.get_by_name(name.casefold(), user_id)
        if subcategory is None or subcategory == "":
            # Mantém compatibilidade com categorias históricas ainda não listadas no catálogo.
            return parent.name if parent else name, None
        sub_name = category_name(subcategory)
        if parent:
            sub = next(
                (sub for sub in parent.subcategories if sub.normalized_name == sub_name.casefold()),
                None,
            )
            if sub:
                return parent.name, sub.name
        raise ValidationError("A subcategoria não pertence à categoria selecionada.")
