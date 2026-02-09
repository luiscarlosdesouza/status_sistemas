import smtplib
from email.message import EmailMessage
from datetime import datetime
from ..models import User

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
        msg = EmailMessage()
        msg['Subject'] = f"ALERTA: {site.name} está OFFLINE"
        
        sender = settings.email_user
        if sender and '@' not in sender:
             if 'ime.usp.br' in settings.smtp_server:
                 sender = f"{sender}@ime.usp.br"
        
        msg['From'] = f"Monitor de Sites <{sender}>"
        msg['To'] = recipient
        msg.set_content(f"O site {site.name} ({site.url}) está inacessível há mais de {settings.alert_threshold} minutos.\n\nHorário: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\nErro: {site.error_message}")

        try:
            _send_email(msg, settings, smtp_port)
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
        msg = EmailMessage()
        msg['Subject'] = f"RECUPERAÇÃO: {site.name} está ONLINE novamente"
        
        sender = settings.email_user
        if sender and '@' not in sender:
             if settings.smtp_server and 'ime.usp.br' in settings.smtp_server:
                 sender = f"{sender}@ime.usp.br"
        
        msg['From'] = f"Monitor de Sites <{sender}>"
        msg['To'] = recipient
        msg.set_content(f"O site {site.name} ({site.url}) voltou a responder.\n\nHorário: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        try:
            _send_email(msg, settings, smtp_port)
            print(f"Sent recovery email for {site.name} to {recipient}")
        except Exception as e:
            print(f"Failed to send recovery email to {recipient}: {e}")

def send_new_user_admin_notification(new_user, admins, settings):
    """
    Notifies ALL admins that a new user has registered.
    """
    if not (settings.email_user and settings.email_password):
        return

    recipients = [u.email for u in admins if u.email]
    if not recipients:
        return

    try:
        smtp_port = int(settings.smtp_port) if settings.smtp_port else 465
    except ValueError:
        smtp_port = 465

    for recipient in recipients:
        msg = EmailMessage()
        msg['Subject'] = f"Novo Usuário Cadastrado: {new_user.name}"
        
        # Ensure 'From' has domain if user just put username (e.g. 'apoio')
        if sender and '@' not in sender:
             # Try to guess domain from SMTP server or hardcode based on user request
             if settings.smtp_server and 'ime.usp.br' in settings.smtp_server:
                 sender = f"{sender}@ime.usp.br"
        
        msg['From'] = f"Monitor de Sites <{sender}>"
        msg['To'] = recipient
        
        body = (
            f"Um novo usuário acabou de se cadastrar no Monitor de Sites.\n\n"
            f"Nome: {new_user.name}\n"
            f"Usuario (Login): {new_user.username}\n"
            f"Email: {new_user.email}\n"
            f"Número USP: {new_user.nusp}\n\n"
            f"Por favor, acesse o painel administrativo para definir a função/permissões deste usuário.\n"
        )
        msg.set_content(body)

        try:
            _send_email(msg, settings, smtp_port)
            print(f"Sent new user admin notification to {recipient}")
        except Exception as e:
            print(f"Failed to send admin notification to {recipient}: {e}")

def send_welcome_email(new_user, settings):
    """
    Sends a welcome email to the new user.
    """
    if not (settings.email_user and settings.email_password) or not new_user.email:
        return

    try:
        smtp_port = int(settings.smtp_port) if settings.smtp_port else 465
    except ValueError:
        smtp_port = 465

    msg = EmailMessage()
    msg['Subject'] = "Bem-vindo ao Monitor de Sites - Aguardando Aprovação"
    
    sender = settings.email_user
    if sender and '@' not in sender:
         if 'ime.usp.br' in settings.smtp_server:
             sender = f"{sender}@ime.usp.br"
    msg['From'] = f"Monitor de Sites <{sender}>"
    
    msg['To'] = new_user.email
    
    body = (
        f"Olá, {new_user.name}!\n\n"
        f"Seu cadastro no Monitor de Sites foi recebido com sucesso.\n\n"
        f"Seu acesso está atualmente limitado. Um administrador analisará sua solicitação "
        f"e liberará as permissões adequadas em até 48 horas.\n\n"
        f"Você receberá um novo e-mail assim que seu nível de acesso for atualizado.\n"
    )
    msg.set_content(body)

    try:
        _send_email(msg, settings, smtp_port)
        print(f"Sent welcome email to {new_user.email}")
    except Exception as e:
        print(f"Failed to send welcome email to {new_user.email}: {e}")

def send_role_update_email(user, new_role, settings):
    """
    Notifies the user that their role has been updated.
    """
    if not (settings.email_user and settings.email_password) or not user.email:
        return

    try:
        smtp_port = int(settings.smtp_port) if settings.smtp_port else 465
    except ValueError:
        smtp_port = 465

    msg = EmailMessage()
    msg['Subject'] = "Seu nível de acesso foi atualizado"
    
    sender = settings.email_user
    if sender and '@' not in sender:
         if settings.smtp_server and 'ime.usp.br' in settings.smtp_server:
             sender = f"{sender}@ime.usp.br"
    msg['From'] = f"Monitor de Sites <{sender}>"
    
    msg['To'] = user.email
    
    role_name = "Operador" if new_role == 'operator' else "Administrador" if new_role == 'admin' else "Usuário (Limitado)"
    
    body = (
        f"Olá, {user.name}!\n\n"
        f"Informamos que seu nível de acesso no Monitor de Sites foi atualizado para: {role_name}.\n\n"
        f"Você já pode acessar as funcionalidades correspondentes ao seu novo perfil.\n"
    )
    msg.set_content(body)

    try:
        _send_email(msg, settings, smtp_port)
        print(f"Sent role update email to {user.email}")
    except Exception as e:
        print(f"Failed to send role update email to {user.email}: {e}")

def _send_email(msg, settings, port):
    if port == 465:
        with smtplib.SMTP_SSL(settings.smtp_server, port) as smtp:
            smtp.login(settings.email_user, settings.email_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(settings.smtp_server, port) as smtp:
            smtp.starttls()
            smtp.login(settings.email_user, settings.email_password)
            smtp.send_message(msg)
