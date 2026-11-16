"""« Payé le » du bulletin : jour de virement du dossier, au mois du bulletin."""
import unittest
from datetime import date

from tests.base import API, SessionLocal, auth_headers, client, make_tenant, reset_database
from app.services.bulletin_saari import construire_html_saari
from app.services.payroll import calculate_payslip


class DateVersementTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-versement")
        self.dossier = self.t["dossier"]

    def tearDown(self):
        self.db.close()

    def _bulletin(self, jour, mois=11, annee=2026):
        self.dossier.jour_virement = jour
        self.db.commit()
        bulletin = calculate_payslip(self.db, self.t["contrat"].id, mois, annee)
        self.db.refresh(bulletin)
        return bulletin

    def test_jour_de_virement_applique_au_mois_du_bulletin(self):
        self.assertEqual(self._bulletin(5).date_versement, date(2026, 11, 5))

    def test_jour_ramene_au_dernier_jour_du_mois(self):
        self.assertEqual(self._bulletin(31).date_versement, date(2026, 11, 30))
        self.assertEqual(self._bulletin(31, mois=2, annee=2028).date_versement, date(2028, 2, 29))

    def test_sans_jour_de_virement_pas_de_date(self):
        self.assertIsNone(self._bulletin(None).date_versement)

    def test_api_et_pdf_affichent_la_date_du_dossier(self):
        bulletin = self._bulletin(25)
        r = client.get(f"{API}/bulletins/{bulletin.id}", headers=auth_headers(self.t["user"]))
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(r.json()["date_versement"], "2026-11-25")

        contrat = self.t["contrat"]
        html = construire_html_saari(
            bulletin, contrat=contrat, salarie=contrat.salarie,
            etablissement=contrat.etablissement, dossier=self.dossier,
        )
        self.assertIn("25/11/2026", html)


if __name__ == "__main__":
    unittest.main()


class DateVersementParLeFormulaireTests(unittest.TestCase):
    """Chaîne complète : formulaire du dossier → bulletin déjà calculé."""

    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-formulaire")
        self.entetes = auth_headers(self.t["user"])

    def tearDown(self):
        self.db.close()

    def test_modifier_le_jour_de_virement_met_a_jour_un_bulletin_existant(self):
        bulletin = calculate_payslip(self.db, self.t["contrat"].id, 11, 2026)
        lu = client.get(f"{API}/bulletins/{bulletin.id}", headers=self.entetes).json()
        self.assertIsNone(lu["date_versement"])

        r = client.put(f"{API}/dossiers/{self.t['dossier'].id}", headers=self.entetes,
                       json={"jour_virement": 12})
        self.assertEqual(r.status_code, 200, r.text[:300])

        lu = client.get(f"{API}/bulletins/{bulletin.id}", headers=self.entetes).json()
        self.assertEqual(lu["date_versement"], "2026-11-12")
