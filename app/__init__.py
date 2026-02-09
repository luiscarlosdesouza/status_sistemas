from flask import Flask
from .extensions import db, login_manager, migrate, oauth, scheduler
from .models import User, GlobalSettings, Site, SiteHistory
from .services.monitor_service import check_sites
from config import Config
import atexit
import os
from werkzeug.security import generate_password_hash

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Init Extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    migrate.init_app(app, db)
    oauth.init_app(app)
    
    # Register Blueprints
    from .blueprints.auth import auth_bp
    from .blueprints.admin import admin_bp
    from .blueprints.main import main_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)

    # Scheduler
    if not scheduler.running:
        scheduler.add_job(func=check_sites, args=[app], trigger="interval", minutes=1)
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())

    # OAuth Registry (Moved from global to here or extensions? Extensions has object, registry needs app context or init)
    # Actually oauth.register can be called anywhere on the oauth object.
    # But usually done at module level.
    # In app.py it was: oauth.register(...)
    # Let's do it in extensions.py or here.
    # Doing it here ensures it picks up config.
    
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )

    oauth.register(
        name='usp',
        client_id=app.config['USP_CLIENT_KEY'],
        client_secret=app.config['USP_CLIENT_SECRET'],
        request_token_url='https://uspdigital.usp.br/wsusuario/oauth/request_token',
        request_token_params=None,
        access_token_url='https://uspdigital.usp.br/wsusuario/oauth/access_token',
        access_token_params=None,
        authorize_url='https://uspdigital.usp.br/wsusuario/oauth/authorize',
        authorize_params=None,
        api_base_url='https://uspdigital.usp.br/wsusuario/oauth/',
        client_kwargs=None
    )
    
    # Init DB (One-time check logic)
    # We can use @app.before_first_request (deprecated in Flask 2.3+) or just run it.
    # Or exposing a command.
    # For now, let's keep the automatic check inside create_app but guarded.
    # BETTER: Use a CLI command `flask init-db`.
    # But to keep strictly compatible with previous "just run" behavior:
    with app.app_context():
        # Check if DB exists or create
        # db.create_all() # handled by migrate usually, but we want ensure basic structure
        # Let's avoid running this on every reload if possible, but for SQLite it's fast.
        pass

    return app

def init_db(app):
    with app.app_context():
        db.create_all()
        # ... (logic to create default admin/settings) ...
        # Copying logic from app.py
        
        # Migrations/Columns check logic (Simplified, assuming Migrate handles schema now?)
        # Since we have Flask-Migrate, we should rely on it for structural changes.
        # But we still need to seed data (Admin, Settings).
        
        from sqlalchemy import text
        # ... (check_and_add_column logic is less needed with Migrate, but if user didn't run upgrade...)
        # Let's stick to Seeding.
        
        # Create/Update Admin
        admin_pass = os.getenv('ADMIN_PASSWORD', 'admin')
        hashed_pw = generate_password_hash(admin_pass, method='pbkdf2:sha256')
        
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            env_email = os.getenv('EMAIL_TO', 'admin@localhost').split(',')[0].strip()
            new_admin = User(
                username='admin', 
                password_hash=hashed_pw,
                name='Administrador',
                role='admin',
                email=env_email,
                is_default_password=True,
                receive_notifications=True
            )
            db.session.add(new_admin)
            print("Created default Admin user.")
            
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
