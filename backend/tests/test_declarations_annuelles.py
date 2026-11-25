"""DISA et DASC de l'exercice, construites depuis les déclarations mensuelles."""
import unittest
from io import BytesIO

from tests.base import API, SessionLocal, auth_headers, client, make_tenant, make_user, reset_database
from app.services.payroll import calculate_payslip


class DeclarationsAnnuellesTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-disa")
        self.entetes = auth_headers(self.t["user"])
        self.etab = self.t["etablissement"]
        self.etab.cnps_matricule = "468453"
        self.t["salarie"].numero_securite_sociale = "202100108350"
        self.db.commit()
        self.decl = f"{API}/etablissements/{self.etab.id}/declarations-cnps"
        self.annuel = f"{API}/etablissements/{self.etab.id}/declarations-annuelles/2025"
        self.mensuelles = {}
        for mois in (1, 2):
            bulletin = calculate_payslip(self.db, self.t["contrat"].id, mois, 2025)
            bulletin.statut = "valide"
            self.db.commit()
            self.mensuelles[mois] = client.post(f"{self.decl}/2025/{mois}", headers=self.entetes).json()
        # Janvier payé, février seulement déposé
        client.post(f"{API}/declarations-cnps/{self.mensuelles[1]['id']}/paiements", headers=self.entetes,
                    json={"date_paiement": "2025-02-15", "montant": self.mensuelles[1]["total_cotisations"]})
        client.put(f"{API}/declarations-cnps/{self.mensuelles[1]['id']}/depot", headers=self.entetes,
                   json={"date_depot": "2025-02-10"})

    def tearDown(self):
        self.db.close()

    def _annuel(self):
        r = client.get(self.annuel, headers=self.entetes)
        self.assertEqual(r.status_code, 200, r.text[:400])
        return r.json()

    def test_disa_une_ligne_par_salarie(self):
        corps = self._annuel()
        self.assertEqual(len(corps["lignes"]), 1)
        ligne = corps["lignes"][0]
        self.assertEqual(ligne["duree_activite"], 2)
        self.assertEqual(ligne["salaire_brut"], 600000)
        self.assertEqual(ligne["montant_pf_at"], 150000)
        self.assertEqual(ligne["montant_retraite"], 600000)
        self.assertEqual(ligne["regime"], "123")
        self.assertEqual(ligne["numero_cnps"], "202100108350")

    def test_dasc_totaux(self):
        t = self._annuel()["totaux"]
        declare = self.mensuelles[1]["total_cotisations"] + self.mensuelles[2]["total_cotisations"]
        # Totaux en francs entiers : au plus un demi-franc d'écart par mois.
        self.assertTrue(all(isinstance(t[c], int) for c in ("total_i", "total_ii", "total_iii", "solde")))
        self.assertLessEqual(abs(t["total_i"] - declare), 1)
        self.assertEqual(t["total_iv"], t["total_iii"] - t["total_i"])
        self.assertEqual(t["total_v"], t["total_i"] - t["total_ii"])
        self.assertEqual(t["solde"], t["total_iv"] + t["total_v"])
        # Les cotisations annuelles recalculées retrouvent les déclarations mensuelles.
        self.assertLessEqual(abs(t["total_iii"] - t["total_i"]), 2)

    def test_paiement_arrondi_au_franc_solde_nul(self):
        """Un paiement arrondi au franc (x,5 → x+1) ne laisse pas de solde de −1."""
        t = self._annuel()["totaux"]
        mois_payes = [m for m in self._annuel()["mois"] if m["paiements_effectues"]]
        for m in mois_payes:
            self.assertGreaterEqual(m["paiements_effectues"], m["cotisations_declarees"] - 1)
        self.assertEqual(t["total_v"], t["total_i"] - t["total_ii"])

    def test_regimes_et_montants_e_cnps(self):
        corps = self._annuel()
        regimes = {r["code"]: r for r in corps["regimes"]}
        self.assertEqual(regimes["prestations_familiales"]["taux"], 5.0)
        self.assertEqual(regimes["prestations_familiales"]["base_annuelle"], 150000)
        self.assertEqual(regimes["prestations_familiales"]["cotisation"], 7500)
        self.assertEqual(regimes["retraite"]["taux"], 14.0)
        self.assertEqual(regimes["retraite"]["cotisation"], 84000)
        e_cnps = corps["totaux"]["e_cnps"]
        self.assertEqual(e_cnps["effectif_disa"], 1)
        self.assertEqual(e_cnps["salaire_brut_non_plafonne"], 600000)
        self.assertEqual(e_cnps["salaire_pf"], 150000)
        self.assertEqual(e_cnps["salaire_retraite"], 600000)

    def test_anomalies(self):
        bulletin = calculate_payslip(self.db, self.t["contrat"].id, 3, 2025)
        self.db.commit()
        messages = [a["message"] for a in self._annuel()["anomalies"]]
        self.assertTrue(any("Mars" in m and "aucune déclaration" in m for m in messages))
        self.assertTrue(any("Février" in m and "non déposée" in m for m in messages))

    def test_exercice_sans_declaration(self):
        r = client.get(f"{API}/etablissements/{self.etab.id}/declarations-annuelles/2024", headers=self.entetes)
        self.assertTrue(any(a["niveau"] == "bloquant" for a in r.json()["anomalies"]))

    def test_fichier_disa(self):
        from openpyxl import load_workbook
        r = client.get(f"{self.annuel}/disa", headers=self.entetes)
        self.assertEqual(r.status_code, 200)
        self.assertIn("DISA_2025.xlsx", r.headers["content-disposition"])
        feuille = load_workbook(BytesIO(r.content))["DISA"]
        self.assertEqual([feuille["A1"].value, feuille["B1"].value], ["EXERCICE", 2025])
        self.assertEqual(feuille["B2"].value, 468453)
        self.assertEqual(feuille["D4"].value, 202100108350)
        self.assertEqual(feuille["I4"].value, 600000)
        self.assertEqual(feuille["A5"].value, "TOTAL")
        self.assertEqual(feuille["K5"].value, 150000)

    def test_pdf_dasc(self):
        r = client.get(f"{self.annuel}/dasc", headers=self.entetes)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF-"))
        try:
            from pypdf import PdfReader
        except ImportError:  # pragma: no cover
            self.skipTest("pypdf indisponible")
        texte = "".join(p.extract_text() for p in PdfReader(BytesIO(r.content)).pages)
        self.assertIn("TOTAL III", texte)
        self.assertIn("468453", texte)

    def test_droits(self):
        autre = auth_headers(make_tenant(self.db, "autre-cabinet-disa")["user"])
        self.assertIn(client.get(self.annuel, headers=autre).status_code, (403, 404))
        compte = make_user(self.db, "client-disa@exemple.ci", role="client", dossier_id=self.t["dossier"].id)
        self.assertEqual(client.get(self.annuel, headers=auth_headers(compte)).status_code, 403)


if __name__ == "__main__":
    unittest.main()
