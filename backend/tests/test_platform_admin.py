"""Administration plateforme : cabinets, administrateurs et suspension."""
import unittest

from datetime import date

from tests.base import (
    API, SessionLocal, auth_headers, client, make_salarie, make_tenant, make_user,
    reset_database,
)
from app.services.payroll import calculate_payslip

from app.models import models as M

MDP = "MotDePasse!2026"


class PlateformeCabinetsTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.admin = make_user(
            self.db, "plateforme@payohada.ci", role="cabinet", is_admin=True,
        )
        self.entetes = auth_headers(self.admin)

    def tearDown(self):
        self.db.close()

    def _creer(self, email="direction@cabinet-test.ci", password=MDP, nom="Cabinet Test"):
        return client.post(
            f"{API}/platform/cabinets",
            headers=self.entetes,
            json={
                "cabinet_nom": nom,
                "cabinet_telephone": "+225 07 00 00 00 00",
                "cabinet_ville": "Abidjan",
                "administrateur": {
                    "prenom": "Awa", "nom": "Kouassi",
                    "email": email, "password": password,
                },
            },
        )

    def _proprietaire(self, email="direction@cabinet-test.ci"):
        return (
            self.db.query(M.Utilisateur)
            .filter(M.Utilisateur.email == email)
            .first()
        )

    def _connexion(self, email, password=MDP):
        return client.post(
            f"{API}/auth/login",
            json={"email": email, "password": password},
        )

    def test_l_administrateur_plateforme_cree_un_cabinet(self):
        r = self._creer()
        self.assertEqual(r.status_code, 201, r.text[:500])
        corps = r.json()
        self.assertEqual(corps["cabinet_nom"], "Cabinet Test")
        self.assertEqual(corps["email"], "direction@cabinet-test.ci")
        self.assertFalse(corps["suspendu"])
        self.assertEqual(corps["administrateurs"][0]["est_proprietaire"], True)

        proprietaire = self._proprietaire()
        self.assertIsNotNone(proprietaire)
        self.assertEqual(proprietaire.role, "cabinet")
        self.assertFalse(proprietaire.is_admin)
        self.assertIsNone(proprietaire.cabinet_owner_id)
        self.assertEqual(self._connexion(proprietaire.email).status_code, 200)

    def test_un_email_deja_utilise_est_refuse(self):
        self.assertEqual(self._creer().status_code, 201)
        r = self._creer(email="direction@cabinet-test.ci")
        self.assertEqual(r.status_code, 400, r.text[:300])

    def test_un_cabinet_ne_peut_pas_administrer_la_plateforme(self):
        self._creer()
        proprietaire = self._proprietaire()
        r = client.get(f"{API}/platform/cabinets", headers=auth_headers(proprietaire))
        self.assertEqual(r.status_code, 403, r.text[:300])

    def test_liste_des_cabinets(self):
        self._creer()
        r = client.get(f"{API}/platform/cabinets", headers=self.entetes)
        self.assertEqual(r.status_code, 200, r.text[:300])
        cabinets = r.json()
        self.assertEqual(len(cabinets), 1)
        self.assertEqual(cabinets[0]["membres"], 1)
        self.assertEqual(cabinets[0]["administrateurs"][0]["email"], "direction@cabinet-test.ci")

    def test_suspension_bloque_la_connexion_et_l_api(self):
        self._creer()
        proprietaire = self._proprietaire()
        entetes_owner = auth_headers(proprietaire)

        r = client.put(
            f"{API}/platform/cabinets/{proprietaire.id}/statut",
            headers=self.entetes, json={"suspendu": True},
        )
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertTrue(r.json()["suspendu"])

        self.assertEqual(self._connexion(proprietaire.email).status_code, 403)
        self.assertEqual(
            client.get(f"{API}/dossiers", headers=entetes_owner).status_code,
            403,
        )

        r = client.put(
            f"{API}/platform/cabinets/{proprietaire.id}/statut",
            headers=self.entetes, json={"suspendu": False},
        )
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(self._connexion(proprietaire.email).status_code, 200)
        self.assertEqual(
            client.get(f"{API}/dossiers", headers=entetes_owner).status_code,
            200,
        )

    def test_ajout_d_un_administrateur_au_cabinet(self):
        self._creer()
        proprietaire = self._proprietaire()
        r = client.post(
            f"{API}/platform/cabinets/{proprietaire.id}/administrateurs",
            headers=self.entetes,
            json={"prenom": "Serge", "nom": "Adou", "email": "associe@cabinet-test.ci"},
        )
        self.assertEqual(r.status_code, 201, r.text[:500])
        corps = r.json()
        self.assertTrue(corps["mot_de_passe_initial"])
        self.assertFalse(corps["email_envoye"])

        associe = (
            self.db.query(M.Utilisateur)
            .filter(M.Utilisateur.email == "associe@cabinet-test.ci")
            .first()
        )
        self.assertIsNotNone(associe)
        self.assertEqual(associe.role, "cabinet")
        self.assertEqual(associe.cabinet_owner_id, proprietaire.id)
        self.assertEqual(
            self._connexion(associe.email, corps["mot_de_passe_initial"]).status_code,
            200,
        )

        # La suspension du propriétaire bloque aussi le co-administrateur.
        client.put(
            f"{API}/platform/cabinets/{proprietaire.id}/statut",
            headers=self.entetes, json={"suspendu": True},
        )
        self.assertEqual(
            self._connexion(associe.email, corps["mot_de_passe_initial"]).status_code,
            403,
        )

    def test_mot_de_passe_genere_pour_l_administrateur(self):
        r = client.post(
            f"{API}/platform/cabinets",
            headers=self.entetes,
            json={
                "cabinet_nom": "Cabinet Sans Mot De Passe",
                "administrateur": {
                    "prenom": "Awa", "nom": "Kouassi",
                    "email": "genere@cabinet-test.ci",
                },
            },
        )
        self.assertEqual(r.status_code, 201, r.text[:500])
        corps = r.json()
        self.assertTrue(corps["mot_de_passe_initial"])
        self.assertEqual(
            self._connexion("genere@cabinet-test.ci", corps["mot_de_passe_initial"]).status_code,
            200,
        )



class PlateformeSaasTests(unittest.TestCase):
    """L'administrateur pilote le SaaS sans accéder à la paie des cabinets."""

    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.admin = make_user(
            self.db, "plateforme@payohada.ci", role="cabinet", is_admin=True,
        )
        self.entetes = auth_headers(self.admin)
        self.t = make_tenant(self.db, "cabinet-saas")
        self.t["user"].cabinet_nom = "Cabinet SaaS"
        make_salarie(self.db, self.t["etablissement"], matricule="M2")
        self.db.commit()
        aujourd_hui = date.today()
        self.bulletin = calculate_payslip(
            self.db, self.t["contrat"].id, aujourd_hui.month, aujourd_hui.year
        )

    def tearDown(self):
        self.db.close()

    def test_tableau_de_bord_agrege_l_usage_par_cabinet(self):
        r = client.get(f"{API}/platform/tableau-de-bord", headers=self.entetes)
        self.assertEqual(r.status_code, 200, r.text[:500])
        corps = r.json()
        self.assertEqual(corps["cabinets"]["total"], 1)
        self.assertEqual(corps["cabinets"]["actifs"], 1)
        self.assertEqual(corps["cabinets"]["nouveaux_30_jours"], 1)
        self.assertEqual(corps["societes"], 1)
        self.assertEqual(corps["salaries_actifs"], 2)
        self.assertEqual(corps["bulletins_mois_courant"], 1)
        self.assertEqual(len(corps["activite"]), 6)
        self.assertEqual(corps["activite"][-1]["bulletins"], 1)
        self.assertNotIn("plateforme@payohada.ci", str(corps))

        usage = corps["usage_cabinets"][0]
        self.assertEqual(usage["cabinet_nom"], "Cabinet SaaS")
        self.assertEqual(usage["societes"], 1)
        self.assertEqual(usage["salaries_actifs"], 2)
        self.assertEqual(usage["bulletins_mois_courant"], 1)

    def test_tableau_de_bord_reserve_a_la_plateforme(self):
        r = client.get(
            f"{API}/platform/tableau-de-bord", headers=auth_headers(self.t["user"])
        )
        self.assertEqual(r.status_code, 403)

    def test_l_admin_ne_voit_pas_les_dossiers_des_cabinets(self):
        dossier = self.t["dossier"]
        self.assertEqual(client.get(f"{API}/dossiers", headers=self.entetes).json(), [])
        for chemin in (
            f"/dossiers/{dossier.id}",
            f"/dossiers/{dossier.id}/bulletins",
            f"/etablissements/{self.t['etablissement'].id}",
            f"/salaries/{self.t['salarie'].id}",
            f"/contrats/{self.t['contrat'].id}",
            f"/bulletins/{self.bulletin.id}",
        ):
            r = client.get(f"{API}{chemin}", headers=self.entetes)
            self.assertIn(r.status_code, (403, 404), f"{chemin} : {r.status_code}")

    def test_l_admin_ne_peut_ni_creer_ni_calculer_de_paie(self):
        r = client.post(
            f"{API}/dossiers", headers=self.entetes,
            json={"code": "ADM01", "nom_dossier": "Dossier admin"},
        )
        self.assertEqual(r.status_code, 403, r.text[:200])
        aujourd_hui = date.today()
        r = client.post(
            f"{API}/bulletins/calculer", headers=self.entetes,
            json={"contrat_id": self.t["contrat"].id, "mois": aujourd_hui.month,
                  "annee": aujourd_hui.year},
        )
        self.assertEqual(r.status_code, 403, r.text[:200])

    def test_l_admin_ne_voit_pas_les_reclamations(self):
        r = client.get(f"{API}/reclamations", headers=self.entetes)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])


if __name__ == "__main__":
    unittest.main()
