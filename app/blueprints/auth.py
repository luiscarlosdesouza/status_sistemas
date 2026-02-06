from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db, login_manager, oauth
from ..models import User

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.users_list') if current_user.role == 'admin' else url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            if user.is_default_password:
                flash('Por favor, redefina sua senha.', 'warning')
                return redirect(url_for('auth.profile'))
            return redirect(url_for('main.index'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    # Logout Flask-Login
    logout_user()
    
    # Clear Flask session (IMPORTANT for Authlib to clear oauth tokens)
    # This prevents token reuse if stored in session
    from flask import session
    session.clear()
    
    return redirect(url_for('main.index'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
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
                return redirect(url_for('auth.profile'))
            
            current_user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
            current_user.is_default_password = False
            flash('Senha alterada com sucesso!', 'success')
        
        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('main.index'))
        
    return render_template('profile.html', user=current_user)

# --- Google OAuth ---
@auth_bp.route('/login/google')
def google_login():
    # We need to ensure 'google' is registered on oauth in extensions or factory.
    # It will be accessible via oauth.google
    redirect_uri = url_for('auth.google_authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/login/google/callback')
def google_authorize():
    try:
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.userinfo()
        email = user_info['email']
        name = user_info.get('name', email.split('@')[0])
        
        # Check if user exists by email
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash(f'Acesso negado. O e-mail {email} não está cadastrado no sistema.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Log in the user
        login_user(user)
        flash(f'Bem-vindo, {user.name or name}!', 'success')
        
        return redirect(url_for('main.index'))
        return redirect(url_for('main.index'))
    except Exception as e:
        flash(f'Erro no login com Google: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))

# --- USP Senha Unica OAuth 1.0a ---
@auth_bp.route('/login/usp')
def usp_login():
    redirect_uri = url_for('auth.usp_callback', _external=True)
    callback_id = current_app.config.get('USP_CALLBACK_ID')
    return oauth.usp.authorize_redirect(redirect_uri, callback_id=callback_id)

@auth_bp.route('/login/usp/callback')
def usp_callback():
    try:
        token = oauth.usp.authorize_access_token()
        resp = oauth.usp.post('usuariousp', token=token)
        user_data = resp.json()
        
        # DEBUG LOGGING (Temporary)
        print(f"DEBUG: USP Callback Token: {token}", flush=True)
        print(f"DEBUG: USP RAW User Data: {user_data}", flush=True)
        
        # Validar campos retornados (loginUsuario, nomeUsuario, emailPrincipalUsuario)
        username = user_data.get('loginUsuario')
        name = user_data.get('nomeUsuario')
        email = user_data.get('emailPrincipalUsuario')
        
        # FIX: 'codpes' might be missing. Use 'loginUsuario' as fallback for NUSP or handle None safely.
        # Do NOT convert None to "None" string blindly.
        raw_nusp = user_data.get('codpes')
        if raw_nusp:
            nusp = str(raw_nusp)
        else:
            # Fallback: In USP Digital, loginUsuario is often the NUSP
            nusp = str(username) if username else None
        
        print(f"DEBUG: Extracted -> Username: {username}, NUSP: {nusp}, Email: {email}", flush=True)

        if not username:
             raise Exception("Dados de usuário inválidos retornados pela USP.")

        # Check if user exists by nusp or username
        user = User.query.filter((User.nusp == nusp) | (User.username == username)).first()
        
        if user:
             print(f"DEBUG: Found existing user: ID={user.id}, Username={user.username}, NUSP={user.nusp}", flush=True)
        else:
             print("DEBUG: User not found in DB. Proceeding to registration logic.", flush=True)
        
        if not user:
            # Auto-register new USP user
            import secrets
            
            # Check if username (loginUsuario) is already taken by a non-USP user
            existing_username = User.query.filter_by(username=username).first()
            if existing_username:
                if email and existing_username.email == email:
                    user = existing_username
                    # Update NUSP to link account
                    user.nusp = nusp
                    print(f"DEBUG: Linked to existing user by Email: {user.username}", flush=True)
                else:
                    if email:
                        user_by_email = User.query.filter_by(email=email).first()
                        if user_by_email:
                            user = user_by_email
                            user.nusp = nusp
                            print(f"DEBUG: Linked to existing user by Alternate Email Lookup: {user.username}", flush=True)
            
            if not user:
                # Create NEW User
                temp_pass = secrets.token_urlsafe(16)
                hashed = generate_password_hash(temp_pass, method='pbkdf2:sha256')
                
                # Ensure username is unique if we didn't match above
                final_username = username
                if User.query.filter_by(username=final_username).first():
                    final_username = f"{username}_{nusp}"

                user = User(
                    username=final_username,
                    password_hash=hashed,
                    name=name,
                    email=email,
                    nusp=nusp,
                    role='user', # Default limited role
                    is_default_password=False, # OAuth users don't use password
                    receive_notifications=False
                )
                db.session.add(user)
                print(f"DEBUG: Creating NEW user: {final_username}", flush=True)
                flash(f'Conta criada com sucesso! Seu acesso é limitado até aprovação.', 'info')
        
        # Ensure NUSP is set if it was missing (for existing users linking)
        if hasattr(user, 'nusp') and not user.nusp and nusp:
            user.nusp = nusp
            
        db.session.commit()
        
        login_user(user)
        print(f"DEBUG: Logged in user: {user.username}", flush=True)
        flash(f'Bem-vindo, {user.name}!', 'success')
        return redirect(url_for('main.index'))
        
    except Exception as e:
        print(f"DEBUG: Error in USP callback: {str(e)}", flush=True)
        flash(f'Erro no login USP: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))
