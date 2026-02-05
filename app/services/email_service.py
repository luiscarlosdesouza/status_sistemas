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
        msg['From'] = settings.email_user
        msg['To'] = recipient
        msg.set_content(f"The site {site.name} ({site.url}) has been down for more than {settings.alert_threshold} minutes.\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nError: {site.error_message}")

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
        msg['From'] = settings.email_user
        msg['To'] = recipient
        msg.set_content(f"The site {site.name} ({site.url}) is responding again.\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            _send_email(msg, settings, smtp_port)
            print(f"Sent recovery email for {site.name} to {recipient}")
        except Exception as e:
            print(f"Failed to send recovery email to {recipient}: {e}")

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
