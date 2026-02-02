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
    status = db.Column(db.String(20), default='online')
    first_failure_time = db.Column(db.DateTime, nullable=True)
    last_checked = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.String(500), nullable=True)

# --- Monitoring ---
def check_sites():
    print("Checking sites...")
    with app.app_context():
        sites = Site.query.all()
        for site in sites:
            try:
                response = requests.get(site.url, timeout=10)
                is_success = False
                
                if response.status_code == 200:
                    if site.expected_text:
                        if site.expected_text in response.text:
                            is_success = True
                        else:
                            is_success = False
                            error_msg = f"Texto esperado '{site.expected_text}' não encontrado."
                    else:
                        is_success = True
                else:
                    is_success = False
                    error_msg = f"Status Code: {response.status_code}"

                if is_success:
                    # Success State
                    site.status = 'online'
                    site.first_failure_time = None
                    site.error_message = None
                else:
                    # Failure State
                    site.error_message = error_msg
                    
                    if site.first_failure_time is None:
                        # First failure detected
                        site.first_failure_time = datetime.now()
                        site.status = 'warning' # Orange
                    else:
                        # Successive failure
                        time_diff = datetime.now() - site.first_failure_time
                        if time_diff.total_seconds() >= 300: # 5 minutes
                            # Failure persisted for > 5 mins
                            previous_status = site.status
                            site.status = 'offline' # Red
                            
                            # Send Alert only if transitioning to offline for the first time
                            if previous_status != 'offline':
                                send_alert_email(site)
                        else:
                            # Still in warning period
                            site.status = 'warning'

            except Exception as e:
                # Exception Handling
                site.error_message = str(e)
                if site.first_failure_time is None:
                    site.first_failure_time = datetime.now()
                    site.status = 'warning'
                else:
                    time_diff = datetime.now() - site.first_failure_time
                    if time_diff.total_seconds() >= 300:
                        previous_status = site.status
                        site.status = 'offline'
                        if previous_status != 'offline':
                            send_alert_email(site)
                    else:
                        site.status = 'warning'
            
            site.last_checked = datetime.now()
            
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
        msg['Subject'] = f"ALERT: {site.name} is OFFLINE"
        msg['From'] = email_user
        msg['To'] = recipient
        msg.set_content(f"The site {site.name} ({site.url}) has been down for more than 5 minutes.\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nError: {site.error_message}")

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

@app.route('/site/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_site(id):
    site = Site.query.get(id)
    if request.method == 'POST':
        site.name = request.form.get('name')
        site.url = request.form.get('url')
        if not site.url.startswith(('http://', 'https://')):
            site.url = 'https://' + site.url
        site.expected_text = request.form.get('expected_text')
        db.session.commit()
        # Re-check immediately
        check_sites()
        return redirect(url_for('admin'))
    return render_template('edit_site.html', site=site)

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
