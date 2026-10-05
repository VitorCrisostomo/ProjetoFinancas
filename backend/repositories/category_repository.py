"""Persistência do catálogo de categorias, sempre restrito ao usuário."""

from config import db
from models.category import Category


class CategoryRepository:
    def get_by_user_id(self, user_id):
        return Category.query.filter_by(user_id=user_id).order_by(Category.name).all()

    def get_by_id(self, category_id, user_id):
        return Category.query.filter_by(id=category_id, user_id=user_id).first()

    def get_by_name(self, normalized_name, user_id):
        return Category.query.filter_by(normalized_name=normalized_name, user_id=user_id).first()

    def save(self, record):
        db.session.add(record)
        db.session.commit()
        return record
