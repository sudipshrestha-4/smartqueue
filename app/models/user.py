from datetime import datetime
from flask_login import UserMixin
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # 'customer' | 'staff' | 'admin'
    role = db.Column(db.String(20), nullable=False, default='customer')

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # If role == 'staff', which counter they're assigned to (nullable otherwise)
    assigned_counter_id = db.Column(db.Integer, db.ForeignKey('counters.id'), nullable=True)

    # Relationships
    queue_entries = db.relationship('QueueEntry', backref='customer', lazy='dynamic',
                                     foreign_keys='QueueEntry.customer_id')

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'