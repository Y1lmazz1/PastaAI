from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), default='customer')  # 'admin' veya 'customer'

    def __repr__(self):
        return f'<User {self.username}>'


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_source = db.Column(db.Text, nullable=False)
    is_ai = db.Column(db.Boolean, default=False)
    tier_count = db.Column(db.Integer, nullable=False)
    prompt = db.Column(db.Text)
    status = db.Column(db.String(20), default='Bekliyor')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship('User', backref=db.backref('orders', lazy=True))

    def __repr__(self):
        return f'<Order {self.id} - {self.tier_count} kat - {self.status}>'