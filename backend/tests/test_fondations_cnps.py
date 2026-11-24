"""Fondations des déclarations CNPS : plafonds, type de salarié, N° CNPS."""
import unittest

from tests.base import API, SessionLocal, auth_headers, client, make_tenant, reset_database
from app.models import models as M
from app.services.payroll import calculate_payslip


class PlafondsCnpsTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-plafonds")

    def tearDown(self):
        self.db.close()

    def test_plafond_pf_at_maternite_a_75000(self):
        for code in ("CNPS_PF_PLAFOND", "CNPS_AT_PLAFOND", "CNPS_MATERNITE_PLAFOND"):
            constante = self.db.query(M.Constante).filter_by(code=code, pays="CI").one()
            self.assertEqual(constante.montant, 75000.0, code)

    def test_bulletin_cotise_sur_75000(self):
        bulletin = calculate_payslip(self.db, self.t["contrat"].id, 6, 2025)
        lignes = {l.code: l for l in bulletin.lignes}
        for code in ("CNPS_PF", "CNPS_AT", "CNPS_MATERNITE"):
            self.assertEqual(lignes[code].base_p, 75000, code)


class ContratCnpsTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-type-cnps")
        self.entetes = auth_headers(self.t["user"])
        self.url = f"{API}/contrats/{self.t['contrat'].id}"

    def tearDown(self):
        self.db.close()

    def test_type_deduit_puis_choisi(self):
        corps = client.get(self.url, headers=self.entetes).json()
        self.assertEqual(corps["type_salarie_cnps"], "M")
        self.assertEqual(corps["cnps_branches"], "123")

        r = client.put(self.url, headers=self.entetes, json={"cnps_type_salarie": "j", "cnps_branches": "32"})
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(r.json()["type_salarie_cnps"], "J")
        self.assertEqual(r.json()["cnps_branches"], "23")

    def test_contrat_horaire_deduit_h(self):
        self.t["contrat"].type_salaire = "Horaire"
        self.db.commit()
        self.assertEqual(client.get(self.url, headers=self.entetes).json()["type_salarie_cnps"], "H")

    def test_valeurs_refusees(self):
        self.assertEqual(client.put(self.url, headers=self.entetes, json={"cnps_type_salarie": "X"}).status_code, 422)
        self.assertEqual(client.put(self.url, headers=self.entetes, json={"cnps_branches": "14"}).status_code, 422)

    def test_branches_videes_reviennent_a_123(self):
        client.put(self.url, headers=self.entetes, json={"cnps_branches": "23"})
        r = client.put(self.url, headers=self.entetes, json={"cnps_branches": ""})
        self.assertEqual(r.json()["cnps_branches"], "123")


class NumeroCnpsTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-numero-cnps")
        self.entetes = auth_headers(self.t["user"])
        self.url = f"{API}/salaries/{self.t['salarie'].id}"

    def tearDown(self):
        self.db.close()

    def test_numero_normalise(self):
        r = client.put(self.url, headers=self.entetes, json={"numero_securite_sociale": "2021 0010-8350"})
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(r.json()["numero_securite_sociale"], "202100108350")

    def test_numero_non_numerique_refuse(self):
        r = client.put(self.url, headers=self.entetes, json={"numero_securite_sociale": "1 85 05 2A"})
        self.assertEqual(r.status_code, 422)

    def test_creation_avec_numero(self):
        r = client.post(f"{API}/etablissements/{self.t['etablissement'].id}/salaries", headers=self.entetes,
                        json={"nom": "Koné", "prenom": "Ali", "numero_securite_sociale": "184 011 462 472"})
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(r.json()["numero_securite_sociale"], "184011462472")

    def test_fiche_existante_mal_formee_reste_lisible(self):
        self.t["salarie"].numero_securite_sociale = "1 85 05 2A"
        self.db.commit()
        self.assertEqual(client.get(self.url, headers=self.entetes).status_code, 200)


if __name__ == "__main__":
    unittest.main()
