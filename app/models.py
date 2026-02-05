from .extensions import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=True)
    role = db.Column(db.String(20), default='operator') # 'admin' or 'operator'
    is_default_password = db.Column(db.Boolean, default=True)
    receive_notifications = db.Column(db.Boolean, default=False)

class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    expected_text = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='online')
    first_failure_time = db.Column(db.DateTime, nullable=True)
    last_checked = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.String(500), nullable=True)

class SiteHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    site = db.relationship('Site', backref=db.backref('history', lazy=True))
    status = db.Column(db.String(20), nullable=False) # 'offline' (confirmed failure)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.now)
    end_time = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.String(500), nullable=True)

class GlobalSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Email Config
    email_user = db.Column(db.String(100), nullable=True)
    email_password = db.Column(db.String(100), nullable=True)
    email_to = db.Column(db.String(500), nullable=True)
    smtp_server = db.Column(db.String(100), default='smtp.gmail.com')
    smtp_port = db.Column(db.Integer, default=465)
    
    # Intervals (in minutes)
    interval_weekday = db.Column(db.Integer, default=60)
    interval_weekend = db.Column(db.Integer, default=120)
    alert_threshold = db.Column(db.Integer, default=15)
