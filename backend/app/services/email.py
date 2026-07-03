import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config import settings

def send_email(to_email: str, subject: str, html_content: str):
    """Envoie un e-mail HTML en utilisant les paramètres SMTP configurés."""
    if not settings.SMTP_HOST:
        print("SMTP WARNING: SMTP_HOST non configuré, mail non envoyé.")
        return False
        
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
        msg["To"] = to_email
        
        part_html = MIMEText(html_content, "html", "utf-8")
        msg.attach(part_html)
        
        # Connect to SMTP server
        if settings.SMTP_SECURE:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            
        server.ehlo()
        if not settings.SMTP_SECURE:
            try:
                server.starttls()
                server.ehlo()
            except Exception:
                # TLS non supporté par le serveur local, poursuite sans TLS
                pass
                
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
        server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())
        server.quit()
        print(f"SMTP SUCCESS: Mail envoyé avec succès à {to_email}")
        return True
    except Exception as e:
        print(f"SMTP ERROR: Impossible d'envoyer le mail à {to_email}. Erreur: {e}")
        return False
