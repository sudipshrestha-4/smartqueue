from datetime import datetime
from app.extensions import db


class Feedback(db.Model):
    __tablename__ = 'feedbacks'

    id = db.Column(db.Integer, primary_key=True)
    queue_entry_id = db.Column(db.Integer, db.ForeignKey('queue_entries.id'), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    queue_entry = db.relationship('QueueEntry', backref=db.backref('feedback', uselist=False))
    customer = db.relationship('User', backref='feedbacks')

    def __repr__(self):
        return f'<Feedback entry={self.queue_entry_id} rating={self.rating}>'
