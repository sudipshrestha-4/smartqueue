from datetime import date
from app.extensions import db


class AnalyticsLog(db.Model):
    __tablename__ = 'analytics_logs'

    id = db.Column(db.Integer, primary_key=True)
    log_date = db.Column(db.Date, default=date.today, index=True)

    total_customers = db.Column(db.Integer, default=0)
    total_completed = db.Column(db.Integer, default=0)
    total_no_shows = db.Column(db.Integer, default=0)

    avg_actual_wait_time = db.Column(db.Float, nullable=True)
    avg_predicted_wait_time = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<AnalyticsLog {self.log_date}>'