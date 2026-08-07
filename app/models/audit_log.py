from datetime import datetime
from app.extensions import db


class TokenResetLog(db.Model):
    __tablename__ = 'token_reset_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    admin_name = db.Column(db.String(100), nullable=False)
    reset_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    counters_reset = db.Column(db.Integer, nullable=False, default=0)

    admin = db.relationship('User', foreign_keys=[admin_id])

    def __repr__(self):
        return f'<TokenResetLog {self.admin_name} - {self.counters_reset} counters @ {self.reset_at}>'
