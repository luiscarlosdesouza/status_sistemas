import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import atexit
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-dev-key-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sites.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    expected_text = db.Column(db.String(200), nullable=True)
    is_online = db.Column(db.Boolean, default=False)
    last_checked = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.String(500), nullable=True)

# --- Monitoring ---
def check_sites():
    print("Checking sites...")
    with app.app_context():
        sites = Site.query.all()
        for site in sites:
            previous_status = site.is_online
            try:
                response = requests.get(site.url, timeout=10)
                if response.status_code == 200:
                    # Content Verification
                    if site.expected_text:
                        if site.expected_text in response.text:
                            site.is_online = True
                            site.error_message = None
                        else:
                            site.is_online = False
                            site.error_message = f"Texto esperado '{site.expected_text}' não encontrado."
                    else:
                        site.is_online = True
                        site.error_message = None
                else:
                    site.is_online = False
                    site.error_message = f"Status Code: {response.status_code}"
            except Exception as e:
                site.is_online = False
                site.error_message = str(e)
            
            site.last_checked = datetime.now()
            
            # Email Notification Logic
            if previous_status and not site.is_online:
                send_alert_email(site)
            
        db.session.commit()

def send_alert_email(site):
    email_user = os.getenv('EMAIL_USER')
    email_pass = os.getenv('EMAIL_PASSWORD')
    email_to = os.getenv('EMAIL_TO') # Who receives the alert

    if not (email_user and email_pass and email_to):
        print("Email configuration missing. Notification skipped.")
        return

    recipients = [e.strip() for e in email_to.split(',')]

    for recipient in recipients:
        msg = EmailMessage()
        msg['Subject'] = f"ALERT: {site.name} is DOWN"
        msg['From'] = email_user
        msg['To'] = recipient
        msg.set_content(f"The site {site.name} ({site.url}) appears to be down.\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nError: {site.error_message}")

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(email_user, email_pass)
                smtp.send_message(msg)
            print(f"Sent alert email for {site.name} to {recipient}")
        except Exception as e:
            print(f"Failed to send email to {recipient}: {e}")

# Start Scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_sites, trigger="interval", minutes=1)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())


# --- Routes ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    sites = Site.query.all()
    return render_template('index.html', sites=sites)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('admin'))
        else:
            flash('Login failed. Check username and password.')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    sites = Site.query.all()
    return render_template('admin.html', sites=sites)

@app.route('/site/add', methods=['POST'])
@login_required
def add_site():
    name = request.form.get('name')
    url = request.form.get('url')
    expected_text = request.form.get('expected_text')
    
    if name and url:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        new_site = Site(name=name, url=url, expected_text=expected_text)
        db.session.add(new_site)
        db.session.commit()
        # Check immediately
        check_sites() 
    return redirect(url_for('admin'))

@app.route('/site/delete/<int:id>', methods=['POST'])
@login_required
def delete_site(id):
    site = Site.query.get(id)
    if site:
        db.session.delete(site)
        db.session.commit()
    return redirect(url_for('admin'))

# --- Init DB ---
def init_db():
    with app.app_context():
        db.create_all()
        # Create or update default admin
        admin_pass = os.getenv('ADMIN_PASSWORD', 'admin')
        hashed_pw = generate_password_hash(admin_pass, method='pbkdf2:sha256')
        
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            admin_user.password_hash = hashed_pw
            print(f"Updated admin user password.")
        else:
            admin_user = User(username='admin', password_hash=hashed_pw)
            db.session.add(admin_user)
            print(f"Created default admin user.")
        
        db.session.commit()

if __name__ == '__main__':
    if not os.path.exists('sites.db'):
        init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
