"""Envoi des emails transactionnels (bulletins de paie, notifications)."""
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Tuple

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, html_content: str) -> Tuple[bool, str]:
    """Envoie un e-mail HTML avec les paramètres SMTP configurés.

    Retourne `(succès, message)`. Le message d'erreur est destiné à l'exploitant
    (journaux, réponse HTTP) : il ne contient jamais le mot de passe SMTP.

    Un `timeout` est appliqué à toutes les opérations réseau : sans lui, une
    connexion SMTP qui ne répond pas immobiliserait un worker FastAPI
    indéfiniment, l'envoi étant effectué dans le fil de la requête.
    """
    if not settings.SMTP_HOST:
        logger.warning("SMTP_HOST non configuré : email non envoyé à %s", to_email)
        return False, "L'envoi d'emails n'est pas configuré sur ce serveur (SMTP_HOST absent)."

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    # formataddr protège l'affichage des caractères non ASCII du nom d'expéditeur.
    message["From"] = formataddr((settings.EMAIL_FROM_NAME, settings.EMAIL_FROM))
    message["To"] = to_email
    message.attach(MIMEText(html_content, "html", "utf-8"))

    server = None
    try:
        if settings.SMTP_SECURE:
            server = smtplib.SMTP_SSL(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT,
                context=ssl.create_default_context(),
            )
        else:
            server = smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT,
            )

        server.ehlo()
        if not settings.SMTP_SECURE:
            try:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            except smtplib.SMTPException as e:
                # Serveur local sans TLS (MailHog, Mailpit…) : on poursuit.
                logger.info("STARTTLS indisponible (%s) : envoi sans chiffrement.", e)

        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

        server.sendmail(settings.EMAIL_FROM, [to_email], message.as_string())
        logger.info("Email envoyé à %s (sujet : %s)", to_email, subject)
        return True, f"Email envoyé à {to_email}."

    except smtplib.SMTPAuthenticationError as e:
        logger.error("Authentification SMTP refusée pour %s : %s", settings.SMTP_USER, e)
        return False, "Authentification SMTP refusée : vérifiez SMTP_USER et SMTP_PASSWORD."
    except smtplib.SMTPRecipientsRefused as e:
        logger.error("Destinataire refusé %s : %s", to_email, e)
        return False, f"Le destinataire {to_email} a été refusé par le serveur SMTP."
    except (smtplib.SMTPException, OSError, ssl.SSLError) as e:
        logger.exception("Échec de l'envoi de l'email à %s", to_email)
        return False, f"Échec de la communication avec le serveur SMTP : {type(e).__name__}."
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:  # pragma: no cover - fermeture best effort
                pass
