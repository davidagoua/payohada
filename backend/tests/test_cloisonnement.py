"""Cloisonnement par cabinet : un sous-domaine par cabinet, même base de données."""
import unittest
from unittest import mock

from tests.base import (
    API, DEFAULT_PASSWORD, SessionLocal, auth_headers, client, make_tenant, make_user, reset_database,
)
from app.config import settings
from app.models import models as M
from app.services.espaces import (
    attribuer_sous_domaines_manquants, espace_depuis_hote, generer_sous_domaine, normaliser_sous_domaine,
)
from app.services.security import create_access_token

DOMAINE = "payohada.cloud"
HOTE_X = {"Host": f"cabinet-x.{DOMAINE}"}
HOTE_Y = {"Host": f"cabinet-y.{DOMAINE}"}
HOTE_PLATEFORME = {"Host": f"app.{DOMAINE}"}


class EspaceDepuisHoteTests(unittest.TestCase):
    def test_inactif_sans_domaine_configure(self):
        with mock.patch.object(settings, "DOMAINES_PLATEFORME", ""):
            self.assertEqual(espace_depuis_hote("cabinet-x.payohada.cloud").type, "local")

    def test_resolution(self):
        with mock.patch.object(settings, "DOMAINES_PLATEFORME", "payohada.cloud, payohada.com"):
            self.assertEqual(espace_depuis_hote("payohada.cloud").type, "plateforme")
            self.assertEqual(espace_depuis_hote("app.payohada.cloud:443").type, "plateforme")
            self.assertEqual(espace_depuis_hote("www.payohada.com").type, "plateforme")
            espace = espace_depuis_hote("Cabinet-X.payohada.com")
            self.assertEqual((espace.type, espace.sous_domaine), ("cabinet", "cabinet-x"))
            self.assertEqual(espace_depuis_hote("a.b.payohada.cloud").type, "inconnu")
            self.assertEqual(espace_depuis_hote("autre-site.com").type, "inconnu")
            self.assertEqual(espace_depuis_hote("localhost:3000").type, "local")
            self.assertEqual(espace_depuis_hote("10.0.0.4:8000").type, "local")


class SousDomainesTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_normalisation(self):
        self.assertEqual(normaliser_sous_domaine("Cabinet Kouassi & Fils"), "cabinet-kouassi-fils")
        self.assertEqual(normaliser_sous_domaine("  Société Générale d'Études  "), "societe-generale-d-etudes")

    def test_generation_unique_et_mots_reserves(self):
        premier = make_user(self.db, "a@exemple.ci")
        premier.sous_domaine = "audit-paie"
        self.db.commit()
        self.assertEqual(generer_sous_domaine(self.db, "Audit Paie"), "audit-paie-2")
        self.assertEqual(generer_sous_domaine(self.db, "API"), "cabinet-api")
        self.assertEqual(generer_sous_domaine(self.db, "AB"), "cabinet-ab")

    def test_attribution_au_demarrage(self):
        for indice in range(2):
            compte = make_user(self.db, f"proprio{indice}@exemple.ci")
            compte.cabinet_nom = "Cabinet Alpha"
        admin = make_user(self.db, "admin@exemple.ci", is_admin=True)
        self.db.commit()
        self.assertEqual(attribuer_sous_domaines_manquants(self.db), 2)
        self.db.commit()
        domaines = sorted(u.sous_domaine for u in self.db.query(M.Utilisateur).filter(M.Utilisateur.role == "cabinet", M.Utilisateur.is_admin.is_(False)))
        self.assertEqual(domaines, ["cabinet-alpha", "cabinet-alpha-2"])
        self.assertIsNone(admin.sous_domaine)


class CloisonnementTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.x = make_tenant(self.db, "cabinet-x")
        self.y = make_tenant(self.db, "cabinet-y")
        self.x["user"].sous_domaine = "cabinet-x"
        self.y["user"].sous_domaine = "cabinet-y"
        self.admin = make_user(self.db, "plateforme@payohada.ci", is_admin=True)
        self.client_x = make_user(self.db, "client-x@exemple.ci", role="client", dossier_id=self.x["dossier"].id)
        self.membre_x = make_user(self.db, "gestion-x@exemple.ci", role="gestionnaire_paie")
        self.membre_x.cabinet_owner_id = self.x["user"].id
        self.db.commit()
        # Configuration de production : domaine de base et adresse principale en https.
        self.patchs = [
            mock.patch.object(settings, "DOMAINES_PLATEFORME", DOMAINE),
            mock.patch.object(settings, "FRONTEND_BASE_URL", f"https://app.{DOMAINE}"),
        ]
        for patch in self.patchs:
            patch.start()

    def tearDown(self):
        for patch in self.patchs:
            patch.stop()
        self.db.close()

    def _connexion(self, email, hote):
        return client.post(f"{API}/auth/login", headers=hote, json={"email": email, "password": DEFAULT_PASSWORD})

    # ─── Connexion ─────────────────────────────────────────

    def test_connexion_sur_son_cabinet_seulement(self):
        self.assertEqual(self._connexion(self.x["user"].email, HOTE_X).status_code, 200)
        refus = self._connexion(self.x["user"].email, HOTE_Y)
        self.assertEqual(refus.status_code, 401)
        # Même message qu'un mot de passe faux : rien ne trahit le compte.
        mauvais = client.post(f"{API}/auth/login", headers=HOTE_Y, json={"email": self.x["user"].email, "password": "faux-mdp"})
        self.assertEqual(refus.json()["detail"], mauvais.json()["detail"])

    def test_comptes_rattaches_au_cabinet(self):
        for email in ("client-x@exemple.ci", "gestion-x@exemple.ci"):
            with self.subTest(email=email):
                self.assertEqual(self._connexion(email, HOTE_X).status_code, 200)
                self.assertEqual(self._connexion(email, HOTE_Y).status_code, 401)

    def test_plateforme_reservee_a_l_admin(self):
        self.assertEqual(self._connexion(self.admin.email, HOTE_PLATEFORME).status_code, 200)
        self.assertEqual(self._connexion(self.admin.email, HOTE_X).status_code, 401)
        self.assertEqual(self._connexion(self.x["user"].email, HOTE_PLATEFORME).status_code, 401)

    def test_adresse_inconnue_refusee(self):
        r = self._connexion(self.x["user"].email, {"Host": "autre-site.com"})
        self.assertEqual(r.status_code, 401)

    # ─── Jeton ─────────────────────────────────────────────

    def test_jeton_lie_au_sous_domaine(self):
        jeton = self._connexion(self.x["user"].email, HOTE_X).json()["access_token"]
        entetes = {"Authorization": f"Bearer {jeton}"}
        self.assertEqual(client.get(f"{API}/auth/me", headers={**entetes, **HOTE_X}).status_code, 200)
        self.assertEqual(client.get(f"{API}/auth/me", headers={**entetes, **HOTE_Y}).status_code, 401)
        self.assertEqual(client.get(f"{API}/dossiers", headers={**entetes, **HOTE_Y}).status_code, 401)

    def test_jeton_sans_espace_verifie_l_appartenance(self):
        entetes = auth_headers(self.x["user"])  # jeton sans « dom »
        self.assertEqual(client.get(f"{API}/auth/me", headers={**entetes, **HOTE_X}).status_code, 200)
        self.assertEqual(client.get(f"{API}/auth/me", headers={**entetes, **HOTE_Y}).status_code, 401)

    def test_jeton_forge_pour_un_autre_espace_refuse(self):
        jeton = create_access_token({"sub": self.x["user"].supabase_uid, "email": self.x["user"].email, "dom": "cabinet-y"})
        entetes = {"Authorization": f"Bearer {jeton}", **HOTE_X}
        self.assertEqual(client.get(f"{API}/auth/me", headers=entetes).status_code, 401)

    # ─── Mot de passe oublié ───────────────────────────────

    def test_mot_de_passe_oublie_cloisonne(self):
        with mock.patch("app.routers.auth.send_email", return_value=(True, "")) as envoi:
            r = client.post(f"{API}/auth/forgot-password", headers=HOTE_Y, json={"email": self.x["user"].email})
            self.assertEqual(r.status_code, 200)
            envoi.assert_not_called()
            self.assertEqual(self.db.query(M.PasswordResetToken).count(), 0)

            client.post(f"{API}/auth/forgot-password", headers=HOTE_X, json={"email": self.x["user"].email})
            envoi.assert_called_once()
            self.assertIn(f"https://cabinet-x.{DOMAINE}/reset-password?token=", envoi.call_args[0][2])

    # ─── Espace courant ────────────────────────────────────

    def test_espace_courant(self):
        self.x["user"].cabinet_nom = "Cabinet X Conseil"
        self.db.commit()
        corps = client.get(f"{API}/auth/espace", headers=HOTE_X).json()
        self.assertEqual((corps["type"], corps["cabinet_nom"]), ("cabinet", "Cabinet X Conseil"))
        self.assertEqual(client.get(f"{API}/auth/espace", headers=HOTE_PLATEFORME).json()["type"], "plateforme")
        self.assertEqual(client.get(f"{API}/auth/espace", headers={"Host": f"inexistant.{DOMAINE}"}).status_code, 404)

    # ─── Administration des cabinets ───────────────────────

    def _creer_cabinet(self, **valeurs):
        donnees = {
            "cabinet_nom": "Audit & Paie Côte d'Ivoire",
            "administrateur": {"prenom": "Awa", "nom": "Koné", "email": "direction@audit-paie.ci", "password": "MotDePasse!2026"},
        }
        donnees.update(valeurs)
        entetes = {**auth_headers(self.admin), **HOTE_PLATEFORME}
        with mock.patch("app.routers.platform.send_email", return_value=(True, "")) as envoi:
            reponse = client.post(f"{API}/platform/cabinets", headers=entetes, json=donnees)
        return reponse, envoi

    def test_creation_avec_sous_domaine_deduit_et_lien_d_acces(self):
        r, envoi = self._creer_cabinet()
        self.assertEqual(r.status_code, 201, r.text[:300])
        self.assertEqual(r.json()["sous_domaine"], "audit-paie-cote-d-ivoire")
        self.assertEqual(r.json()["url_espace"], f"https://audit-paie-cote-d-ivoire.{DOMAINE}")
        self.assertIn(f"https://audit-paie-cote-d-ivoire.{DOMAINE}/login", envoi.call_args[0][2])

    def test_sous_domaine_choisi_controle(self):
        self.assertEqual(self._creer_cabinet(sous_domaine="Mon Cabinet")[0].json()["sous_domaine"], "mon-cabinet")
        r, _ = self._creer_cabinet(sous_domaine="cabinet-x", administrateur={"prenom": "A", "nom": "B", "email": "b@b.ci", "password": "MotDePasse!2026"})
        self.assertEqual(r.status_code, 400)
        r, _ = self._creer_cabinet(sous_domaine="api", administrateur={"prenom": "A", "nom": "B", "email": "c@c.ci", "password": "MotDePasse!2026"})
        self.assertEqual(r.status_code, 400)

    def test_changement_de_sous_domaine(self):
        entetes = {**auth_headers(self.admin), **HOTE_PLATEFORME}
        url = f"{API}/platform/cabinets/{self.x['user'].id}/sous-domaine"
        r = client.put(url, headers=entetes, json={"sous_domaine": "nouveau-x"})
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(r.json()["sous_domaine"], "nouveau-x")
        self.assertEqual(self._connexion(self.x["user"].email, {"Host": f"nouveau-x.{DOMAINE}"}).status_code, 200)
        self.assertEqual(self._connexion(self.x["user"].email, HOTE_X).status_code, 401)
        self.assertEqual(client.put(url, headers=entetes, json={"sous_domaine": "cabinet-y"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
