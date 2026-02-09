import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

# Load credentials we just updated (or from .env)
# For this test we will use the values provided directly to force a check
# independent of the .env loading which might be cached.

SMTP_SERVER = "smtp.ime.usp.br"
SMTP_PORT = 587
EMAIL_USER = "apoio@ime.usp.br" # Testing if full email works for login
EMAIL_PASS = "Leirohk7boaliGh2mah6veiZuiw3jok9"
EMAIL_FROM = "apoio@ime.usp.br" # Usually 'From' needs domain
EMAIL_TO = "luiscarlosdesouza@ime.usp.br" # Send to developer/user to verify

print(f"Testing connection to {SMTP_SERVER}:{SMTP_PORT}...")

try:
    msg = EmailMessage()
    msg['Subject'] = "Teste de Envio SMTP - Monitora Sites"
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg.set_content("Se você recebeu este e-mail, a configuração SMTP do IME-USP está funcionando corretamente via TLS.")

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.set_debuglevel(1) # Show conversation
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        print("Login...")
        smtp.login(EMAIL_USER, EMAIL_PASS)
        print("Sending...")
        smtp.send_message(msg)
        print("✅ Email sent successfully!")
        
except Exception as e:
    print(f"❌ Failed to send email: {e}")
