from config import db


class Transaction(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(10), nullable=False)
    description = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"),nullable=False)

    def to_json(self):
        return {
            "id": self.id,
            "value": self.value,
            "date": self.date,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "user_id": self.user_id
        }