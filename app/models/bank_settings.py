from datetime import time

from app.extensions import db


class BankSettings(db.Model):
    """Single-row configuration for bank operating hours and manual open/close."""

    __tablename__ = 'bank_settings'

    id = db.Column(db.Integer, primary_key=True)
    open_time = db.Column(db.Time, nullable=False, default=lambda: time(9, 0))
    close_time = db.Column(db.Time, nullable=False, default=lambda: time(17, 0))
    # None = follow schedule, 'open' = force open, 'closed' = force closed
    manual_override = db.Column(db.String(10), nullable=True)

    def __repr__(self):
        return f'<BankSettings {self.open_time}-{self.close_time} override={self.manual_override}>'
