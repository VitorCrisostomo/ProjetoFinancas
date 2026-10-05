"""Categorias e subcategorias personalizadas de cada usuário."""

from config import db


class Category(db.Model):
    __tablename__ = "categories"
    __table_args__ = (db.UniqueConstraint("user_id", "normalized_name"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    normalized_name = db.Column(db.String(100), nullable=False)
    subcategories = db.relationship("Subcategory", lazy="selectin", order_by="Subcategory.name")

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "subcategories": [{"id": sub.id, "name": sub.name} for sub in self.subcategories],
        }


class Subcategory(db.Model):
    __tablename__ = "subcategories"
    __table_args__ = (db.UniqueConstraint("category_id", "normalized_name"),)

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    normalized_name = db.Column(db.String(100), nullable=False)
