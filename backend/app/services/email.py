"""Envoi des emails transactionnels (bulletins de paie, notifications)."""
import logging
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional, Sequence, Tuple

from app.config import settings

logger = logging.getLogger(__name__)

#: Pièce jointe : (nom du fichier, contenu binaire, type MIME).
PieceJointe = Tuple[str, bytes, str]

MIME_PAR_DEFAUT = "application/octet-stream"


def _construire_message(
    to_email: str,
    subject: str,
    html_content: str,
    pieces_jointes: Sequence[PieceJointe],
) -> MIMEMultipart:
    """Assemble le message MIME.

    Sans pièce jointe, la structure reste `multipart/alternative` (HTML seul).
    Avec pièces jointes, on encapsule cette partie dans un `multipart/mixed` :
    les clients affichent alors le HTML **et** proposent les fichiers, au lieu de
    remplacer le corps du message par la première pièce jointe.
    """
    if not pieces_jointes:
        message = MIMEMultipart("alternative")
        corps = MIMEText(html_content, "html", "utf-8")
    else:
        message = MIMEMultipart("mixed")
        alternative = MIMEMultipart("alternative")
        alternative.attach(MIMEText(html_content, "html", "utf-8"))
        message.attach(alternative)
        corps = None

    message["Subject"] = subject
    # formataddr protège l'affichage des caractères non ASCII du nom d'expéditeur.
    message["From"] = formataddr((settings.EMAIL_FROM_NAME, settings.EMAIL_FROM))
    message["To"] = to_email

    if corps is not None:
        message.attach(corps)
    else:
        for nom, contenu, type_mime in pieces_jointes:
            # Le nom de fichier peut contenir des accents (nom du salarié) : on
            # laisse l'encodage RFC 2231 le prendre en charge.
            partie = MIMEApplication(contenu, _subtype=type_mime.split("/")[-1])
            partie.add_header(
                "Content-Disposition", "attachment", filename=("utf-8", "", nom)
            )
            message.attach(partie)

    return message


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    pieces_jointes: Optional[Sequence[PieceJointe]] = None,
) -> Tuple[bool, str]:
    """Envoie un e-mail HTML, avec pièces jointes éventuelles.

    Retourne `(succès, message)`. Le message d'erreur est destiné à l'exploitant
    (journaux, réponse HTTP) : il ne contient jamais le mot de passe SMTP.

    Un `timeout` est appliqué à toutes les opérations réseau : sans lui, une
    connexion SMTP qui ne répond pas immobiliserait un worker FastAPI
    indéfiniment, l'envoi étant effectué dans le fil de la requête.
    """
    if not settings.SMTP_HOST:
        logger.warning("SMTP_HOST non configuré : email non envoyé à %s", to_email)
        return False, "L'envoi d'emails n'est pas configuré sur ce serveur (SMTP_HOST absent)."

    message = _construire_message(
        to_email, subject, html_content, pieces_jointes or ()
    )
    if pieces_jointes:
        logger.info(
            "Envoi de %d pièce(s) jointe(s) à %s : %s",
            len(pieces_jointes), to_email,
            ", ".join(nom for nom, _, _ in pieces_jointes),
        )

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
