from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from ..extensions import db
from ..models import Site, User, GlobalSettings

from ..services.monitor_service import check_sites
from ..services.email_service import send_role_update_email

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
def dashboard():
    if current_user.role not in ['admin', 'operator']:
        flash('Acesso negado. Funcionalidade apenas para administradores ou operadores.', 'danger')
        return redirect(url_for('main.index'))
    
    sites = Site.query.all()
    sites = Site.query.all()
    return render_template('admin.html', sites=sites)

@admin_bp.route('/force_update')
@login_required
def force_update():
    if current_user.role not in ['admin', 'operator']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.index'))
        
    check_sites(current_app._get_current_object(), force=True)
    flash('Verificação de sites realizada com sucesso!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/site/add', methods=['POST'])
@login_required
def add_site():
    if current_user.role not in ['admin', 'operator']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.index'))

    name = request.form.get('name')
    url = request.form.get('url')
    expected_text = request.form.get('expected_text')
    
    if name and url:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        new_site = Site(name=name, url=url, expected_text=expected_text)
        db.session.add(new_site)
        db.session.commit()
        # Check immediately. Need to pass app from current_app._get_current_object() or similar?
        # check_sites() expects 'app' to create context.
        # But inside a route we Are in context.
        # Let's Modify check_sites to handle being called within context or accept app.
        # Re-using the service directly.
        
        # NOTE: logic in service uses "with app.app_context()".
        # We can pass current_app._get_current_object()
        check_sites(current_app._get_current_object())
        
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/site/delete/<int:id>', methods=['POST'])
@login_required
def delete_site(id):
    if current_user.role not in ['admin', 'operator']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.index'))

    site = Site.query.get(id)
    if site:
        db.session.delete(site)
        db.session.commit()
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/site/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_site(id):
    if current_user.role not in ['admin', 'operator']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.index'))

    site = Site.query.get(id)
    if request.method == 'POST':
        site.name = request.form.get('name')
        site.url = request.form.get('url')
        if not site.url.startswith(('http://', 'https://')):
            site.url = 'https://' + site.url
        site.expected_text = request.form.get('expected_text')
        db.session.commit()
        
        check_sites(current_app._get_current_object())
        return redirect(url_for('admin.dashboard'))
    return render_template('edit_site.html', site=site)

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role != 'admin':
        flash('Acesso negado. Apenas administradores podem acessar configurações globais.', 'danger')
        return redirect(url_for('main.index'))
    
    settings = GlobalSettings.query.first()
    if request.method == 'POST':
        settings.email_user = request.form.get('email_user')
        if request.form.get('email_password'):
            settings.email_password = request.form.get('email_password')
        settings.email_to = request.form.get('email_to')
        settings.smtp_server = request.form.get('smtp_server')
        settings.smtp_port = int(request.form.get('smtp_port'))
        settings.interval_weekday = int(request.form.get('interval_weekday'))
        settings.alert_threshold = int(request.form.get('alert_threshold'))
        db.session.commit()
        flash('Configurações atualizadas com sucesso!')
        return redirect(url_for('admin.settings'))
        
    return render_template('settings.html', settings=settings)

# --- User Management ---

@admin_bp.route('/users')
@login_required
def users_list():
    if current_user.role != 'admin':
        flash('Acesso negado. Apenas administradores podem gerenciar usuários.', 'danger')
        return redirect(url_for('main.index'))
    
    all_users = User.query.all()
    return render_template('users.html', users=all_users)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id=None):
    if current_user.role != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.index'))
        
    user = User.query.get(user_id) if user_id else None
    
    if request.method == 'POST':
        # Password Reset
        if request.form.get('reset_password'):
            import secrets
            temp_pass = secrets.token_urlsafe(8)
            user.password_hash = generate_password_hash(temp_pass, method='pbkdf2:sha256')
            user.is_default_password = True
            db.session.commit()
            flash(f'Senha redefinida! Nova senha temporária: {temp_pass}', 'warning')
            return redirect(url_for('admin.edit_user', user_id=user.id))

        name = request.form.get('name')
        email = request.form.get('email')
        role = request.form.get('role')
        receive_notifications = 'receive_notifications' in request.form
        
        if user:
            new_role = request.form.get('role')
            old_role = user.role
            
            user.name = name
            user.email = email
            user.role = new_role
            user.receive_notifications = receive_notifications
            db.session.commit()
            
            # Send Notification if Role Changed
            if old_role != new_role:
                settings = GlobalSettings.query.first()
                if settings:
                    send_role_update_email(user, new_role, settings)
            
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('admin.users_list'))
        else:
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
            return redirect(url_for('admin.users_list'))

    return render_template('edit_user.html', user=user)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('admin.users_list'))
        
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
    return redirect(url_for('admin.users_list'))
