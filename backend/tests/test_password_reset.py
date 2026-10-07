"""Tests de la réinitialisation de mot de passe.

Couvre la sécurité (énumération, usage unique, expiration, hachage), le parcours
nominal et les cas d'erreur.
"""
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from tests import base
from tests.base import (
    API,
    DEFAULT_PASSWORD,
    SessionLocal,
    auth_headers,
    client,
    make_user,
    reset_database,
)

from app.config import settings
from app.models import models as M
from app.services import password_reset as pr
from app.services.rate_limit import (
    reinitialisation_compte_limiter,
    reinitialisation_ip_limiter,
    reset_token_limiter,
)


class MotDePasseOublieTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.user = make_user(self.db, "oubli@exemple.ci", role="cabinet")

    def tearDown(self):
        self.db.close()

    def _demander(self, email="oubli@exemple.ci"):
        with mock.patch("app.routers.auth.send_email", return_value=(True, "ok")) as envoi:
            reponse = client.post(f"{API}/auth/forgot-password", json={"email": email})
        return reponse, envoi

    # ── Parcours nominal ────────────────────────────────────────────────

    def test_demande_envoie_un_email_avec_le_lien(self):
        reponse, envoi = self._demander()

        self.assertEqual(reponse.status_code, 200, reponse.text)
        self.assertIn("Si un compte est associé", reponse.json()["message"])

        envoi.assert_called_once()
        destinataire, sujet, contenu = envoi.call_args.args
        self.assertEqual(destinataire, "oubli@exemple.ci")
        self.assertIn("Réinitialisation", sujet)
        self.assertIn("/reset-password?token=", contenu)

        self.assertEqual(
            self.db.query(M.PasswordResetToken).filter(
                M.PasswordResetToken.utilisateur_id == self.user.id
            ).count(),
            1,
        )

    def test_jeton_stocke_hache_jamais_en_clair(self):
        """Une fuite de la base ne doit pas permettre de réinitialiser un compte."""
        _, envoi = self._demander()
        contenu = envoi.call_args.args[2]

        jeton_clair = contenu.split("token=")[1].split('"')[0].split("<")[0].strip()
        self.assertTrue(jeton_clair)

        enregistre = self.db.query(M.PasswordResetToken).first()
        self.assertNotEqual(enregistre.token_hash, jeton_clair)
        self.assertEqual(enregistre.token_hash, pr.hacher_jeton(jeton_clair))
        self.assertEqual(len(enregistre.token_hash), 64)

    def test_reponse_identique_pour_une_adresse_inconnue(self):
        """Aucune énumération : même statut et même message."""
        connu, _ = self._demander("oubli@exemple.ci")
        inconnu, envoi = self._demander("personne@nulle-part.ci")

        self.assertEqual(inconnu.status_code, connu.status_code)
        self.assertEqual(inconnu.json(), connu.json())
        self.assertFalse(envoi.called, "aucun email ne doit partir pour une adresse inconnue")

    def test_adresse_inconnue_ne_cree_aucun_jeton(self):
        self._demander("personne@nulle-part.ci")
        self.assertEqual(self.db.query(M.PasswordResetToken).count(), 0)

    def test_compte_desactive_ne_recoit_pas_d_email(self):
        self.user.is_active = False
        self.db.commit()

        reponse, envoi = self._demander()

        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(envoi.called)

    def test_nouveau_jeton_invalide_le_precedent(self):
        """Un seul lien actif à la fois."""
        _, premier = self._demander()
        jeton1 = premier.call_args.args[2].split("token=")[1].split('"')[0].split("<")[0].strip()

        _, second = self._demander()
        jeton2 = second.call_args.args[2].split("token=")[1].split('"')[0].split("<")[0].strip()

        self.assertIsNone(pr.obtenir_jeton_valide(self.db, jeton1))
        self.assertIsNotNone(pr.obtenir_jeton_valide(self.db, jeton2))

    def test_limite_de_demandes_par_compte(self):
        ancien = reinitialisation_compte_limiter.max_attempts
        reinitialisation_compte_limiter.max_attempts = 2
        try:
            self._demander()
            self._demander()
            with mock.patch("app.routers.auth.send_email", return_value=(True, "ok")):
                reponse = client.post(
                    f"{API}/auth/forgot-password", json={"email": "oubli@exemple.ci"}
                )
            self.assertEqual(reponse.status_code, 429)
        finally:
            reinitialisation_compte_limiter.max_attempts = ancien

    def test_echec_d_envoi_non_revele_au_client(self):
        """Un échec SMTP ne doit pas trahir l'existence du compte."""
        with mock.patch("app.routers.auth.send_email", return_value=(False, "SMTP HS")):
            reponse = client.post(
                f"{API}/auth/forgot-password", json={"email": "oubli@exemple.ci"}
            )
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Si un compte est associé", reponse.json()["message"])


class ReinitialisationTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.user = make_user(self.db, "reset@exemple.ci", role="client")

    def tearDown(self):
        self.db.close()

    def _obtenir_jeton(self) -> str:
        with mock.patch("app.routers.auth.send_email", return_value=(True, "ok")) as envoi:
            client.post(f"{API}/auth/forgot-password", json={"email": "reset@exemple.ci"})
        contenu = envoi.call_args.args[2]
        return contenu.split("token=")[1].split('"')[0].split("<")[0].strip()

    def _reinitialiser(self, jeton, mot_de_passe="NouveauSecret!2026"):
        return client.post(f"{API}/auth/reset-password", json={
            "token": jeton, "new_password": mot_de_passe,
        })

    # ── Parcours nominal ────────────────────────────────────────────────

    def test_reinitialisation_puis_connexion(self):
        jeton = self._obtenir_jeton()

        reponse = self._reinitialiser(jeton)
        self.assertEqual(reponse.status_code, 200, reponse.text)

        # Le nouveau mot de passe fonctionne
        connexion = client.post(f"{API}/auth/login", json={
            "email": "reset@exemple.ci", "password": "NouveauSecret!2026",
        })
        self.assertEqual(connexion.status_code, 200, connexion.text)

        # L'ancien ne fonctionne plus
        ancienne = client.post(f"{API}/auth/login", json={
            "email": "reset@exemple.ci", "password": DEFAULT_PASSWORD,
        })
        self.assertEqual(ancienne.status_code, 401)

    def test_reinitialisation_leve_lobligation_de_changer_le_mot_de_passe(self):
        self.user.must_change_password = True
        self.db.commit()

        self._reinitialiser(self._obtenir_jeton())

        self.db.refresh(self.user)
        self.assertFalse(self.user.must_change_password)

    def test_validation_du_jeton_renvoie_un_email_masque(self):
        jeton = self._obtenir_jeton()

        reponse = client.get(f"{API}/auth/reset-password/valider", params={"token": jeton})

        self.assertEqual(reponse.status_code, 200)
        corps = reponse.json()
        self.assertTrue(corps["valide"])
        self.assertNotIn("reset@exemple.ci", corps["email_masque"])
        self.assertIn("*", corps["email_masque"])
        self.assertTrue(corps["email_masque"].endswith(".ci"))

    # ── Usage unique et expiration ──────────────────────────────────────

    def test_jeton_a_usage_unique(self):
        jeton = self._obtenir_jeton()
        self.assertEqual(self._reinitialiser(jeton).status_code, 200)

        seconde = self._reinitialiser(jeton, "AutreSecret!2026")
        self.assertEqual(seconde.status_code, 400)
        self.assertIn("invalide", seconde.json()["detail"])

    def test_jeton_expire_refuse(self):
        jeton = self._obtenir_jeton()
        enregistre = self.db.query(M.PasswordResetToken).first()
        enregistre.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.db.commit()

        reponse = self._reinitialiser(jeton)
        self.assertEqual(reponse.status_code, 400)

        validation = client.get(f"{API}/auth/reset-password/valider", params={"token": jeton})
        self.assertFalse(validation.json()["valide"])

    def test_jeton_inexistant_refuse(self):
        self.assertEqual(
            self._reinitialiser("jeton-completement-invente-1234567890").status_code, 400
        )

    def test_jeton_tronque_refuse(self):
        jeton = self._obtenir_jeton()
        self.assertEqual(self._reinitialiser(jeton[:-2]).status_code, 400)

    # ── Validation du nouveau mot de passe ─────────────────────────────

    def test_mot_de_passe_trop_court_refuse(self):
        jeton = self._obtenir_jeton()
        reponse = client.post(f"{API}/auth/reset-password", json={
            "token": jeton, "new_password": "court",
        })
        self.assertEqual(reponse.status_code, 422)

    def test_mot_de_passe_sans_chiffre_refuse(self):
        jeton = self._obtenir_jeton()
        reponse = self._reinitialiser(jeton, "MotDePasseSansChiffre")
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("lettres et chiffres", reponse.json()["detail"])

    def test_mot_de_passe_identique_a_l_ancien_refuse(self):
        jeton = self._obtenir_jeton()
        reponse = self._reinitialiser(jeton, DEFAULT_PASSWORD)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("différent de l'ancien", reponse.json()["detail"])

    def test_mot_de_passe_refuse_laisse_le_jeton_utilisable(self):
        """L'utilisateur doit pouvoir corriger sa saisie sans redemander un lien."""
        jeton = self._obtenir_jeton()
        self.assertEqual(self._reinitialiser(jeton, "sanschiffre").status_code, 400)

        reponse = self._reinitialiser(jeton, "ValideCetteFois!2026")
        self.assertEqual(reponse.status_code, 200, reponse.text)

    def test_compte_desactive_refuse(self):
        jeton = self._obtenir_jeton()
        self.user.is_active = False
        self.db.commit()

        reponse = self._reinitialiser(jeton)
        self.assertEqual(reponse.status_code, 403)

    # ── Interactions avec le changement de mot de passe ────────────────

    def test_changement_de_mot_de_passe_invalide_les_jetons_en_attente(self):
        jeton = self._obtenir_jeton()

        client.post(f"{API}/auth/change-password", headers=auth_headers(self.user), json={
            "old_password": DEFAULT_PASSWORD, "new_password": "ChangeDepuisProfil!9",
        })

        self.assertIsNone(pr.obtenir_jeton_valide(self.db, jeton))
        self.assertEqual(self._reinitialiser(jeton, "TentativeApresChangement!1").status_code, 400)

    def test_limite_sur_la_consommation_du_jeton(self):
        ancien = reset_token_limiter.max_attempts
        reset_token_limiter.max_attempts = 2
        try:
            for _ in range(2):
                self._reinitialiser("mauvais-jeton-0123456789")
            reponse = self._reinitialiser("mauvais-jeton-0123456789")
            self.assertEqual(reponse.status_code, 429)
        finally:
            reset_token_limiter.max_attempts = ancien

    # ── Ménage ─────────────────────────────────────────────────────────

    def test_purge_des_jetons_obsoletes(self):
        jeton = self._obtenir_jeton()
        enregistre = self.db.query(M.PasswordResetToken).first()
        enregistre.expires_at = datetime.now(timezone.utc) - timedelta(days=30)
        self.db.commit()

        supprimes = pr.purger_jetons_obsoletes(self.db, jours=7)
        self.db.commit()

        self.assertEqual(supprimes, 1)
        self.assertIsNone(pr.obtenir_jeton_valide(self.db, jeton))


class GabaritEmailTests(unittest.TestCase):
    def test_donnees_utilisateur_echappees(self):
        """Les données d'état civil viennent de la base : elles doivent être échappées."""
        from app.services.email_templates import email_reinitialisation_mot_de_passe

        sujet, html = email_reinitialisation_mot_de_passe(
            "<script>alert(1)</script>", "Nom & Fils", "https://x.ci/r?token=abc", 30
        )

        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&amp;", html)
        self.assertIn("Réinitialisation", sujet)

    def test_lien_present_et_echappe(self):
        from app.services.email_templates import email_reinitialisation_mot_de_passe

        _, html = email_reinitialisation_mot_de_passe("A", "B", 'https://x.ci/r?token=a"b', 30)

        self.assertIn("https://x.ci/r?token=a&quot;b", html)
        self.assertIn("30 minutes", html)
        self.assertIn("une seule utilisation", html)


class ConfigurationReinitialisationTests(unittest.TestCase):
    def test_lien_pointe_vers_le_frontend(self):
        ancien = settings.FRONTEND_BASE_URL
        try:
            settings.FRONTEND_BASE_URL = "https://app.payohada.ci/"
            lien = pr.construire_lien_reinitialisation("ABC123")
            self.assertEqual(lien, "https://app.payohada.ci/reset-password?token=ABC123")
        finally:
            settings.FRONTEND_BASE_URL = ancien

    def test_normalisation_des_dates_naives_et_conscientes(self):
        """SQLite renvoie des dates naïves, PostgreSQL des dates avec fuseau."""
        naive = datetime(2030, 1, 1, 12, 0, 0)
        consciente = datetime(2030, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(pr._normaliser(naive), consciente)
        self.assertEqual(pr._normaliser(consciente), consciente)
        self.assertIsNone(pr._normaliser(None))


if __name__ == "__main__":
    unittest.main()
