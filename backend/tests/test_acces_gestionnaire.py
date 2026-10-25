"""Rôle « gestionnaire de paie » : un compte plateforme, des sociétés confiées.

L'accès ne vient plus du rôle seul mais de l'affectation (`acces_dossiers`) :
c'est ce que ces tests verrouillent, sur les endpoints les plus sensibles.
"""
import unittest

from tests.base import (
    API, SessionLocal, auth_headers, client, make_dossier, make_etablissement,
    make_tenant, make_user, reset_database,
)

from app.models import models as M


class GestionnairePaieTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-gestionnaires")
        self.entetes_proprietaire = auth_headers(self.t["user"])

        self.second_dossier = make_dossier(
            self.db, self.t["user"], code="DOSS2", nom="Seconde société",
        )
        self.second_etab = make_etablissement(self.db, self.second_dossier, code="ETB2")
        self.db.commit()

    def tearDown(self):
        self.db.close()

    # ── helpers ──────────────────────────────────────────────────────────

    def _creer_gestionnaire(self, dossier_id=None, email="paie@cabinet.ci", **extra):
        return client.post(
            f"{API}/dossiers/{dossier_id or self.t['dossier'].id}/gestionnaires",
            headers=self.entetes_proprietaire,
            json={
                "email": email,
                "nom": "Yao",
                "prenom": "Adjoua",
                **extra,
            },
        )

    def _compte(self, email="paie@cabinet.ci"):
        return (
            self.db.query(M.Utilisateur)
            .filter(M.Utilisateur.email == email)
            .first()
        )

    # ── création et affectation ──────────────────────────────────────────

    def test_le_proprietaire_cree_un_gestionnaire(self):
        r = self._creer_gestionnaire()
        self.assertEqual(r.status_code, 200, r.text[:300])
        corps = r.json()
        self.assertEqual(corps["role"], "gestionnaire_paie")
        self.assertTrue(corps["mot_de_passe_initial"])

        compte = self._compte()
        self.assertIsNotNone(compte)
        self.assertEqual(compte.role, "gestionnaire_paie")
        self.assertTrue(compte.is_active)
        self.assertIsNotNone(
            self.db.query(M.AccesDossier)
            .filter(
                M.AccesDossier.utilisateur_id == compte.id,
                M.AccesDossier.dossier_id == self.t["dossier"].id,
            )
            .first()
        )

    def test_un_compte_existant_est_affecte_a_une_seconde_societe(self):
        """Le même gestionnaire peut tenir plusieurs sociétés, sans nouveau mot de passe."""
        premier = self._creer_gestionnaire().json()
        second = self._creer_gestionnaire(dossier_id=self.second_dossier.id)

        self.assertEqual(second.status_code, 200, second.text[:300])
        corps = second.json()
        self.assertEqual(corps["id"], premier["id"])
        # Un compte qui existe déjà : aucun mot de passe régénéré, aucun email
        self.assertIsNone(corps["mot_de_passe_initial"])
        self.assertIsNone(corps["email_envoye"])

        affectations = (
            self.db.query(M.AccesDossier)
            .filter(M.AccesDossier.utilisateur_id == premier["id"])
            .count()
        )
        self.assertEqual(affectations, 2)

    def test_une_affectation_en_double_est_refusee(self):
        self._creer_gestionnaire()
        r = self._creer_gestionnaire()
        self.assertEqual(r.status_code, 409, r.text[:200])

    def test_un_email_deja_pris_par_un_autre_role_est_refuse(self):
        make_user(self.db, "client@exemple.ci", role="client",
                  dossier_id=self.t["dossier"].id)
        self.db.commit()
        r = self._creer_gestionnaire(email="client@exemple.ci")
        self.assertEqual(r.status_code, 400, r.text[:200])

    def test_les_identifiants_partent_par_email(self):
        import app.routers.dossiers as routeur

        appels = []
        origine = routeur.send_email

        def faux_envoi(to_email, subject, html, pieces_jointes=None):
            appels.append({"to": to_email, "html": html})
            return True, "ok"

        routeur.send_email = faux_envoi
        self.addCleanup(setattr, routeur, "send_email", origine)

        corps = self._creer_gestionnaire().json()
        self.assertTrue(corps["email_envoye"])
        self.assertEqual(appels[0]["to"], "paie@cabinet.ci")
        self.assertIn("Espace Paie", appels[0]["html"])
        self.assertIn(corps["mot_de_passe_initial"], appels[0]["html"])

    # ── portée de l'accès ────────────────────────────────────────────────

    def test_le_gestionnaire_affecte_accede_a_sa_societe(self):
        corps = self._creer_gestionnaire().json()
        entetes = auth_headers(self._compte())

        # Il voit la société dans sa liste, et seulement celle-là
        liste = client.get(f"{API}/dossiers", headers=entetes).json()
        self.assertEqual([d["id"] for d in liste], [self.t["dossier"].id])

        # Il accède au dossier, à ses établissements et à ses salariés
        self.assertEqual(
            client.get(f"{API}/dossiers/{self.t['dossier'].id}", headers=entetes).status_code,
            200,
        )
        salaries = client.get(
            f"{API}/etablissements/{self.t['etablissement'].id}/salaries", headers=entetes
        )
        self.assertEqual(salaries.status_code, 200, salaries.text[:200])

        # Et il peut produire un état de paie
        etat = client.post(
            f"{API}/editions/JOURNAL_PAIE/generer", headers=entetes,
            json={
                "etablissement_id": self.t["etablissement"].id,
                "mois_debut": 6, "annee_debut": 2025,
                "mois_fin": 6, "annee_fin": 2025,
            },
        )
        self.assertEqual(etat.status_code, 200, etat.text[:300])

    def test_un_gestionnaire_non_affecte_est_refuse(self):
        make_user(self.db, "inconnu@cabinet.ci", role="gestionnaire_paie")
        self.db.commit()
        entetes = auth_headers(self._compte("inconnu@cabinet.ci"))

        self.assertEqual(
            client.get(f"{API}/dossiers/{self.t['dossier'].id}", headers=entetes).status_code,
            403,
        )
        self.assertEqual(
            client.get(f"{API}/dossiers", headers=entetes).json(), []
        )
        self.assertEqual(
            client.get(
                f"{API}/etablissements/{self.t['etablissement'].id}/salaries",
                headers=entetes,
            ).status_code,
            403,
        )

    def test_seul_le_proprietaire_distribue_les_acces(self):
        self._creer_gestionnaire()
        entetes_gestionnaire = auth_headers(self._compte())
        url = f"{API}/dossiers/{self.t['dossier'].id}/gestionnaires"

        # Un gestionnaire affecté ne peut pas créer d'autre gestionnaire
        r = client.post(url, headers=entetes_gestionnaire,
                        json={"email": "autre@cabinet.ci", "nom": "X", "prenom": "Y"})
        self.assertEqual(r.status_code, 403)

        # Ni lister les accès
        self.assertEqual(client.get(url, headers=entetes_gestionnaire).status_code, 403)

        # Un client non plus
        compte_client = make_user(
            self.db, "rh-gestionnaires@exemple.ci", role="client",
            dossier_id=self.t["dossier"].id,
        )
        self.db.commit()
        r = client.post(url, headers=auth_headers(compte_client),
                        json={"email": "autre2@cabinet.ci", "nom": "X", "prenom": "Y"})
        self.assertEqual(r.status_code, 403)

    def test_le_retrait_revoque_l_acces(self):
        corps = self._creer_gestionnaire().json()
        compte = self._compte()
        entetes = auth_headers(compte)

        self.assertEqual(
            client.get(f"{API}/dossiers/{self.t['dossier'].id}", headers=entetes).status_code,
            200,
        )

        r = client.delete(
            f"{API}/dossiers/{self.t['dossier'].id}/gestionnaires/{corps['id']}",
            headers=self.entetes_proprietaire,
        )
        self.assertEqual(r.status_code, 204, r.text[:200])

        self.assertEqual(
            client.get(f"{API}/dossiers/{self.t['dossier'].id}", headers=entetes).status_code,
            403,
        )
        # Sans aucun accès restant, le compte est désactivé
        self.db.refresh(compte)
        self.assertFalse(compte.is_active)

    def test_le_retrait_preserve_un_compte_encore_affecte(self):
        corps = self._creer_gestionnaire().json()
        self._creer_gestionnaire(dossier_id=self.second_dossier.id)

        client.delete(
            f"{API}/dossiers/{self.t['dossier'].id}/gestionnaires/{corps['id']}",
            headers=self.entetes_proprietaire,
        )

        compte = self._compte()
        self.db.refresh(compte)
        self.assertTrue(compte.is_active)
        # Il garde l'accès à la seconde société
        self.assertEqual(
            client.get(
                f"{API}/dossiers/{self.second_dossier.id}",
                headers=auth_headers(compte),
            ).status_code,
            200,
        )


if __name__ == "__main__":
    unittest.main()
