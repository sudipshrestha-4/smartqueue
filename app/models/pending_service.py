from datetime import datetime
from app.extensions import db


class PendingService(db.Model):
    __tablename__ = 'pending_services'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    priority_type = db.Column(db.String(20), default='normal')
    sequence_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    service = db.relationship('Service')
    customer = db.relationship('User', backref='pending_services')

    def __repr__(self):
        return f'<PendingService customer={self.customer_id} service={self.service_id}>'
