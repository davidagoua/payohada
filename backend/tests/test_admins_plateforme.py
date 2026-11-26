"""Administrateurs de la plateforme : un admin crée d'autres admins de même rôle."""
import unittest
from unittest import mock

from tests.base import API, DEFAULT_PASSWORD, SessionLocal, auth_headers, client, make_tenant, make_user, reset_database
from app.config import settings
from app.models import models as M

URL = f"{API}/platform/administrateurs"
DOMAINE = "payohada.cloud"


class AdminsPlateformeTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.admin = make_user(self.db, "plateforme@payohada.ci", is_admin=True)
        self.tenant = make_tenant(self.db, "cabinet-admins")
        self.db.commit()
        self.entetes = auth_headers(self.admin)

    def tearDown(self):
        self.db.close()

    def _creer(self, **valeurs):
        donnees = {"prenom": "Awa", "nom": "Koné", "email": "Second.Admin@payohada.ci"}
        donnees.update(valeurs)
        with mock.patch("app.routers.platform.send_email", return_value=(True, "")) as envoi:
            return client.post(URL, headers=self.entetes, json=donnees), envoi

    def test_creation_meme_role(self):
        r, envoi = self._creer()
        self.assertEqual(r.status_code, 201, r.text[:300])
        corps = r.json()
        self.assertTrue(corps["mot_de_passe_initial"])
        self.assertTrue(corps["must_change_password"])
        compte = self.db.query(M.Utilisateur).filter_by(email="second.admin@payohada.ci").one()
        self.assertTrue(compte.is_admin)
        self.assertEqual(compte.role, self.admin.role)
        self.assertIsNone(compte.cabinet_owner_id)
        self.assertIsNone(compte.sous_domaine)
        envoi.assert_called_once()
        # Le nouvel admin a les mêmes droits : il peut à son tour créer un admin.
        entetes = auth_headers(compte)
        self.assertEqual(client.get(f"{API}/platform/cabinets", headers=entetes).status_code, 200)
        with mock.patch("app.routers.platform.send_email", return_value=(True, "")):
            r = client.post(URL, headers=entetes, json={"prenom": "A", "nom": "B", "email": "troisieme@payohada.ci"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(client.get(URL, headers=entetes).json()), 3)

    def test_mot_de_passe_choisi(self):
        r, _ = self._creer(password="MotDePasse!2026")
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(r.json()["mot_de_passe_initial"])
        self.assertFalse(r.json()["must_change_password"])
        self.assertEqual(self._creer(email="faible@payohada.ci", password="abc")[0].status_code, 400)

    def test_email_deja_pris(self):
        r, _ = self._creer(email=self.tenant["user"].email.upper())
        self.assertEqual(r.status_code, 400)

    def test_reserve_aux_admins(self):
        entetes = auth_headers(self.tenant["user"])
        self.assertEqual(client.get(URL, headers=entetes).status_code, 403)
        r = client.post(URL, headers=entetes, json={"prenom": "A", "nom": "B", "email": "pirate@exemple.ci"})
        self.assertEqual(r.status_code, 403)

    def test_liste_n_inclut_pas_les_cabinets(self):
        corps = client.get(URL, headers=self.entetes).json()
        self.assertEqual([a["email"] for a in corps], [self.admin.email])
        self.assertTrue(corps[0]["est_moi"])

    def test_desactivation(self):
        autre = self._creer()[0].json()
        statut = f"{URL}/{autre['id']}/statut"
        self.assertEqual(client.put(f"{URL}/{self.admin.id}/statut", headers=self.entetes, json={"actif": False}).status_code, 400)
        r = client.put(statut, headers=self.entetes, json={"actif": False})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["is_active"])
        self.assertEqual(client.post(f"{API}/auth/login", json={"email": autre["email"], "password": autre["mot_de_passe_initial"]}).status_code, 403)
        self.assertEqual(client.put(statut, headers=self.entetes, json={"actif": True}).json()["is_active"], True)
        # Un compte de cabinet n'est pas un administrateur plateforme.
        url_cabinet = f"{URL}/{self.tenant['user'].id}/statut"
        self.assertEqual(client.put(url_cabinet, headers=self.entetes, json={"actif": False}).status_code, 404)

    def test_connexion_sur_l_adresse_principale(self):
        autre = self._creer(password=DEFAULT_PASSWORD)[0].json()
        with mock.patch.object(settings, "DOMAINES_PLATEFORME", DOMAINE):
            principale = client.post(f"{API}/auth/login", headers={"Host": f"app.{DOMAINE}"}, json={"email": autre["email"], "password": DEFAULT_PASSWORD})
            cabinet = client.post(f"{API}/auth/login", headers={"Host": f"cabinet-x.{DOMAINE}"}, json={"email": autre["email"], "password": DEFAULT_PASSWORD})
        self.assertEqual(principale.status_code, 200, principale.text[:300])
        self.assertEqual(cabinet.status_code, 401)


if __name__ == "__main__":
    unittest.main()
