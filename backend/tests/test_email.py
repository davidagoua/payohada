"""Tests du service d'envoi d'emails (app/services/email.py).

Aucun envoi réel : `smtplib` est simulé. On vérifie le contrat de retour
`(succès, message)`, la transmission du timeout et le mapping des erreurs.
"""
import smtplib
import unittest
from unittest import mock

from tests import base  # noqa: F401  (configure l'environnement avant les imports app)

from app.config import settings
from app.services.email import send_email


class ServiceEmailTests(unittest.TestCase):
    def setUp(self):
        self._host = settings.SMTP_HOST
        self._port = settings.SMTP_PORT
        self._secure = settings.SMTP_SECURE
        self._user = settings.SMTP_USER
        self._password = settings.SMTP_PASSWORD
        self._from = settings.EMAIL_FROM
        settings.SMTP_HOST = "smtp.exemple.ci"
        settings.SMTP_PORT = 465
        settings.SMTP_SECURE = True
        settings.SMTP_USER = "support@exemple.ci"
        settings.SMTP_PASSWORD = "secret-de-test"
        settings.EMAIL_FROM = "support@exemple.ci"

    def tearDown(self):
        settings.SMTP_HOST = self._host
        settings.SMTP_PORT = self._port
        settings.SMTP_SECURE = self._secure
        settings.SMTP_USER = self._user
        settings.SMTP_PASSWORD = self._password
        settings.EMAIL_FROM = self._from

    def test_envoi_reussi_retourne_true_et_message(self):
        with mock.patch("app.services.email.smtplib.SMTP_SSL") as smtp:
            ok, message = send_email("dest@exemple.ci", "Sujet", "<p>Bonjour</p>")

        self.assertTrue(ok)
        self.assertIn("dest@exemple.ci", message)
        smtp.return_value.login.assert_called_once_with("support@exemple.ci", "secret-de-test")
        # L'expéditeur et le destinataire sont bien positionnés
        args = smtp.return_value.sendmail.call_args[0]
        self.assertEqual(args[0], "support@exemple.ci")
        self.assertEqual(args[1], ["dest@exemple.ci"])
        smtp.return_value.quit.assert_called_once()

    def test_timeout_transmis_a_la_connexion(self):
        """Sans timeout, un serveur SMTP muet bloquerait un worker FastAPI."""
        settings.SMTP_TIMEOUT = 7
        with mock.patch("app.services.email.smtplib.SMTP_SSL") as smtp:
            send_email("dest@exemple.ci", "Sujet", "<p>x</p>")

        self.assertEqual(smtp.call_args.kwargs.get("timeout"), 7)
        self.assertEqual(smtp.call_args.args[0], "smtp.exemple.ci")
        self.assertEqual(smtp.call_args.args[1], 465)

    def test_authentification_refusee(self):
        with mock.patch("app.services.email.smtplib.SMTP_SSL") as smtp:
            smtp.return_value.login.side_effect = smtplib.SMTPAuthenticationError(535, b"nope")
            ok, message = send_email("dest@exemple.ci", "Sujet", "<p>x</p>")

        self.assertFalse(ok)
        self.assertIn("Authentification SMTP refusée", message)
        # Le mot de passe ne doit jamais apparaître dans le message retourné
        self.assertNotIn("secret-de-test", message)
        smtp.return_value.quit.assert_called_once()

    def test_serveur_injoignable(self):
        with mock.patch("app.services.email.smtplib.SMTP_SSL") as smtp:
            smtp.side_effect = OSError("Connection refused")
            ok, message = send_email("dest@exemple.ci", "Sujet", "<p>x</p>")

        self.assertFalse(ok)
        self.assertIn("Échec de la communication", message)

    def test_destinataire_refuse(self):
        with mock.patch("app.services.email.smtplib.SMTP_SSL") as smtp:
            smtp.return_value.sendmail.side_effect = smtplib.SMTPRecipientsRefused(
                {"dest@exemple.ci": (550, b"User unknown")}
            )
            ok, message = send_email("dest@exemple.ci", "Sujet", "<p>x</p>")

        self.assertFalse(ok)
        self.assertIn("refusé", message)

    def test_smtp_non_configure(self):
        settings.SMTP_HOST = ""
        ok, message = send_email("dest@exemple.ci", "Sujet", "<p>x</p>")
        self.assertFalse(ok)
        self.assertIn("pas configuré", message)

    def test_mode_non_securise_utilise_starttls(self):
        settings.SMTP_SECURE = False
        settings.SMTP_PORT = 587
        with mock.patch("app.services.email.smtplib.SMTP") as smtp:
            ok, _ = send_email("dest@exemple.ci", "Sujet", "<p>x</p>")

        self.assertTrue(ok)
        smtp.return_value.starttls.assert_called_once()
        smtp.return_value.login.assert_called_once()


if __name__ == "__main__":
    unittest.main()
