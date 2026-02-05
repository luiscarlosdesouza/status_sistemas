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
from sqlalchemy import text
from authlib.integrations.flask_client import OAuth

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-dev-key-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sites.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# OAuth Config
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    # New V1.1 Fields
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

# --- Monitoring ---
def check_sites():
    # print("Tick...") 
    with app.app_context():
        settings = GlobalSettings.query.first()
        if not settings:
            return

        # Determine current interval (Weekday vs Weekend)
        # Weekday: 0-4 (Mon-Fri), Weekend: 5-6 (Sat-Sun)
        is_weekend = datetime.now().weekday() >= 5
        current_interval_minutes = settings.interval_weekend if is_weekend else settings.interval_weekday
        threshold_seconds = settings.alert_threshold * 60

        sites = Site.query.all()
        for site in sites:
            # Check if it is time to check this site
            if site.last_checked:
                time_since_check = datetime.now() - site.last_checked
                if time_since_check.total_seconds() < (current_interval_minutes * 60):
                    continue # Skip, not time yet

            # --- Perform Check ---
            print(f"Checking {site.name}...")
            previous_status = site.status
            try:
                response = requests.get(site.url, timeout=30)
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
                    if site.status == 'offline':
                        send_recovery_email(site, settings)
                        
                        # Close History
                        history_entry = SiteHistory.query.filter_by(site_id=site.id, end_time=None).first()
                        if history_entry:
                            history_entry.end_time = datetime.now()
                    
                    site.status = 'online'
                    site.first_failure_time = None
                    site.error_message = None
                else:
                    # Failure State
                    site.error_message = error_msg
                    
                    if site.first_failure_time is None:
                        # First failure detected
                        site.first_failure_time = datetime.now()
                        site.status = 'warning'
                    else:
                        # Successive failure
                        time_diff = datetime.now() - site.first_failure_time
                        if time_diff.total_seconds() >= threshold_seconds:
                            site.status = 'offline'
                            
                            # Send Alert only if transitioning to offline for the first time
                            if previous_status != 'offline':
                                send_alert_email(site, settings)
                                
                                # Open History
                                new_history = SiteHistory(site_id=site.id, status='offline', start_time=datetime.now(), error_message=site.error_message)
                                db.session.add(new_history)
                        else:
                            site.status = 'warning'

            except Exception as e:
                # Exception Handling
                site.error_message = f"Connection Error: {str(e)}"
                if site.first_failure_time is None:
                    site.first_failure_time = datetime.now()
                    site.status = 'warning'
                else:
                    time_diff = datetime.now() - site.first_failure_time
                    if time_diff.total_seconds() >= threshold_seconds:
                        previous_status = site.status
                        site.status = 'offline'
                        if previous_status != 'offline':
                            send_alert_email(site, settings)
                            new_history = SiteHistory(site_id=site.id, status='offline', start_time=datetime.now(), error_message=site.error_message)
                            db.session.add(new_history)
                    else:
                        site.status = 'warning'
            
            site.last_checked = datetime.now()
            
        db.session.commit()

def send_alert_email(site, settings):
    if not (settings.email_user and settings.email_password):
        print("Email configuration (User/Pass) missing in Settings. Notification skipped.")
        return

    # Fetch users who want notifications
    users_to_notify = User.query.filter_by(receive_notifications=True).all()
    recipients = [u.email for u in users_to_notify if u.email]
    
    if not recipients:
        print("No users configured to receive notifications.")
        return

    try:
        smtp_port = int(settings.smtp_port) if settings.smtp_port else 465
    except ValueError:
        smtp_port = 465

    for recipient in recipients:
        msg = EmailMessage()
        msg['Subject'] = f"ALERT: {site.name} is OFFLINE"
        msg['From'] = settings.email_user
        msg['To'] = recipient
        msg.set_content(f"The site {site.name} ({site.url}) has been down for more than {settings.alert_threshold} minutes.\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nError: {site.error_message}")

        try:
            if smtp_port == 465:
                with smtplib.SMTP_SSL(settings.smtp_server, smtp_port) as smtp:
                    smtp.login(settings.email_user, settings.email_password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(settings.smtp_server, smtp_port) as smtp:
                    smtp.starttls()
                    smtp.login(settings.email_user, settings.email_password)
                    smtp.send_message(msg)
            print(f"Sent alert email for {site.name} to {recipient}")
        except Exception as e:
            print(f"Failed to send email to {recipient}: {e}")

def send_recovery_email(site, settings):
    if not (settings.email_user and settings.email_password):
        return

    # Fetch users who want notifications
    users_to_notify = User.query.filter_by(receive_notifications=True).all()
    recipients = [u.email for u in users_to_notify if u.email]

    if not recipients:
        return

    try:
        smtp_port = int(settings.smtp_port) if settings.smtp_port else 465
    except ValueError:
        smtp_port = 465

    for recipient in recipients:
        msg = EmailMessage()
        msg['Subject'] = f"RECOVERY: {site.name} is BACK ONLINE"
        msg['From'] = settings.email_user
        msg['To'] = recipient
        msg.set_content(f"The site {site.name} ({site.url}) is responding again.\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            if smtp_port == 465:
                with smtplib.SMTP_SSL(settings.smtp_server, smtp_port) as smtp:
                    smtp.login(settings.email_user, settings.email_password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(settings.smtp_server, smtp_port) as smtp:
                    smtp.starttls()
                    smtp.login(settings.email_user, settings.email_password)
                    smtp.send_message(msg)
            print(f"Sent recovery email for {site.name} to {recipient}")
        except Exception as e:
            print(f"Failed to send recovery email to {recipient}: {e}")

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
    if current_user.is_authenticated:
        return redirect(url_for('users')) # Redirect to users or index
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            if user.is_default_password:
                flash('Por favor, redefina sua senha.', 'warning')
                return redirect(url_for('profile'))
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
            
    return render_template('login.html')

@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
def google_authorize():
    try:
        token = google.authorize_access_token()
        resp = google.get('userinfo')
        user_info = resp.json()
        email = user_info['email']
        name = user_info.get('name', email.split('@')[0])
        
        # Check if user exists by email
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Check if admin authorized this domain/email (Security Check can be added here)
            # For now, we only allow if the Admin pre-registered the email OR we auto-create if configured.
            flash(f'Acesso negado. O e-mail {email} não está cadastrado no sistema.', 'danger')
            return redirect(url_for('login'))
        
        # Log in the user
        login_user(user)
        flash(f'Bem-vindo, {user.name or name}!', 'success')
        
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Erro no login com Google: {str(e)}', 'danger')
        return redirect(url_for('login'))

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

@app.route('/reports')
@login_required
def reports():
    # Fetch offline events sorted by start_time desc
    history = SiteHistory.query.order_by(SiteHistory.start_time.desc()).all()
    # Calculate duration for display
    enriched_history = []
    for h in history:
        duration = "Em andamento"
        if h.end_time:
            delta = h.end_time - h.start_time
            # Format duration nicely
            minutes, seconds = divmod(delta.total_seconds(), 60)
            hours, minutes = divmod(minutes, 60)
            duration = f"{int(hours)}h {int(minutes)}m"
        enriched_history.append({
            'site_name': h.site.name,
            'url': h.site.url,
            'status': h.status,
            'start_time': h.start_time,
            'end_time': h.end_time,
            'duration': duration,
            'error': h.error_message
        })
            
    return render_template('reports.html', history=enriched_history)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role != 'admin':
        flash('Acesso negado. Apenas administradores podem acessar configurações globais.', 'danger')
        return redirect(url_for('index'))
    settings = GlobalSettings.query.first()
    if request.method == 'POST':
        settings.email_user = request.form.get('email_user')
        if request.form.get('email_password'): # Only update if provided
            settings.email_password = request.form.get('email_password')
        settings.email_to = request.form.get('email_to')
        settings.smtp_server = request.form.get('smtp_server')
        settings.smtp_port = int(request.form.get('smtp_port'))
        settings.interval_weekday = int(request.form.get('interval_weekday'))
        settings.alert_threshold = int(request.form.get('alert_threshold'))
        db.session.commit()
        flash('Configurações atualizadas com sucesso!')
        return redirect(url_for('settings'))
        
    return render_template('settings.html', settings=settings)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Update Name/Email
        current_user.name = request.form.get('name')
        current_user.email = request.form.get('email')
        
        # Password Change
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password:
            if new_password != confirm_password:
                flash('Novas senhas não conferem.', 'danger')
                return redirect(url_for('profile'))
            
            current_user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
            current_user.is_default_password = False
            flash('Senha alterada com sucesso!', 'success')
        
        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('index'))
        
    return render_template('profile.html', user=current_user)

# --- User Management Routes ---

@app.route('/users')
@login_required
def users():
    # Only Admin can access
    if current_user.role != 'admin':
        flash('Acesso negado. Apenas administradores podem gerenciar usuários.', 'danger')
        return redirect(url_for('index'))
    
    all_users = User.query.all()
    return render_template('users.html', users=all_users)

@app.route('/users/add', methods=['GET', 'POST'])
@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id=None):
    if current_user.role != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('index'))
        
    user = User.query.get(user_id) if user_id else None
    
    if request.method == 'POST':
        # Password Reset Logic
        if request.form.get('reset_password'):
            import secrets
            temp_pass = secrets.token_urlsafe(8)
            user.password_hash = generate_password_hash(temp_pass, method='pbkdf2:sha256')
            user.is_default_password = True
            db.session.commit()
            flash(f'Senha redefinida! Nova senha temporária: {temp_pass}', 'warning')
            return redirect(url_for('edit_user', user_id=user.id))

        name = request.form.get('name')
        email = request.form.get('email')
        role = request.form.get('role')
        receive_notifications = 'receive_notifications' in request.form
        
        if user:
            # Update
            user.name = name
            user.email = email
            user.role = role
            user.receive_notifications = receive_notifications
            db.session.commit()
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('users'))
        else:
            # Create
            username = request.form.get('username')
            if User.query.filter_by(username=username).first():
                flash('Nome de usuário já existe.', 'danger')
                return render_template('edit_user.html', user=None)
            
            import secrets
            temp_pass = secrets.token_urlsafe(8)
            hashed = generate_password_hash(temp_pass, method='pbkdf2:sha256')
            
            new_user = User(
                username=username,
                password_hash=hashed,
                name=name,
                email=email,
                role=role,
                is_default_password=True,
                receive_notifications=receive_notifications
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f'Usuário criado! Senha temporária: {temp_pass}', 'success')
            return redirect(url_for('users'))

    return render_template('edit_user.html', user=user)

@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('users'))
        
    user = User.query.get(user_id)
    if user:
        if user.username == 'admin':
            flash('Não é possível excluir o administrador principal.', 'danger')
        elif user.id == current_user.id:
            flash('Você não pode excluir a si mesmo.', 'danger')
        else:
            db.session.delete(user)
            db.session.commit()
            flash('Usuário excluído.', 'success')
    return redirect(url_for('users'))

def check_and_add_column(table_name, column_name, column_type, default_value=None):
    with db.engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in result.fetchall()]
        
        if column_name not in columns:
            print(f"Migrating: Adding {column_name} to {table_name}")
            try:
                # Add column
                alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                conn.execute(text(alter_query))
                
                # Update default values if provided
                if default_value is not None:
                    if isinstance(default_value, str):
                        update_query = f"UPDATE {table_name} SET {column_name} = '{default_value}'"
                    else:
                        update_query = f"UPDATE {table_name} SET {column_name} = {default_value}"
                    conn.execute(text(update_query))
                
                conn.commit()
            except Exception as e:
                print(f"Migration error: {e}")

# --- Init DB ---
def init_db():
    with app.app_context():
        # Ensure tables exist
        db.create_all()
        
        # --- Migrations for V1.1 ---
        # Add new columns to User table if they don't exist
        from sqlalchemy import text
        check_and_add_column('user', 'name', 'VARCHAR(100)', 'Administrador')
        check_and_add_column('user', 'email', 'VARCHAR(100)')
        check_and_add_column('user', 'role', 'VARCHAR(20)', 'admin')
        check_and_add_column('user', 'is_default_password', 'BOOLEAN', 0) # Default to 0 (False) for existing users to avoid forced change
        check_and_add_column('user', 'receive_notifications', 'BOOLEAN', 1) # Default Admin receives notifications

        # Create or update default admin
        admin_pass = os.getenv('ADMIN_PASSWORD', 'admin')
        hashed_pw = generate_password_hash(admin_pass, method='pbkdf2:sha256')
        
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            # Update existing admin to ensure it has the correct role
            if not admin_user.role:
                admin_user.role = 'admin'
                admin_user.name = 'Administrador'
                admin_user.receive_notifications = True
            
            # Update email if not set, trying to grab from Settings or Env
            if not admin_user.email:
                 # Try env first
                 env_email_to = os.getenv('EMAIL_TO')
                 if env_email_to:
                     admin_user.email = env_email_to.split(',')[0].strip()
            
            # Only reset password if it matches the default 'admin' hash (optional, but good for safety)
            # admin_user.password_hash = hashed_pw 
        else:
            # Create new admin
            env_email_to = os.getenv('EMAIL_TO')
            first_email = env_email_to.split(',')[0].strip() if env_email_to else 'admin@localhost'
            
            new_admin = User(
                username='admin', 
                password_hash=hashed_pw,
                name='Administrador',
                role='admin',
                email=first_email,
                is_default_password=True,
                receive_notifications=True
            )
            db.session.add(new_admin)
            print("Created default Admin user.")

        # Init Settings
        settings = GlobalSettings.query.first()
        if not settings:
            settings = GlobalSettings(
                email_user=os.getenv('EMAIL_USER'),
                email_password=os.getenv('EMAIL_PASSWORD'),
                email_to=os.getenv('EMAIL_TO'),
                smtp_server=os.getenv('EMAIL_SMTP_SERVER') or 'smtp.gmail.com',
                smtp_port=int(os.getenv('EMAIL_SMTP_PORT') or 465),
                interval_weekday=60,
                interval_weekend=120,
                alert_threshold=15
            )
            db.session.add(settings)
            print("Created default Global Settings.")
        
        db.session.commit()

if __name__ == '__main__':
    # Always run init_db to ensure tables/migrations exist
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
