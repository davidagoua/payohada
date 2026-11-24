"""Déclaration CNPS mensuelle : aperçu, génération figée, fichier e-CNPS, dépôt."""
import unittest
from datetime import date, datetime
from io import BytesIO

from tests.base import (
    API, SessionLocal, auth_headers, client, make_contrat, make_salarie, make_tenant, make_user,
    reset_database,
)
from app.models import models as M
from app.services.payroll import calculate_payslip


class DeclarationsCnpsTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-declaration")
        self.entetes = auth_headers(self.t["user"])
        self.etab = self.t["etablissement"]
        salarie = self.t["salarie"]
        salarie.numero_securite_sociale = "202100108350"
        salarie.date_naissance = datetime(1994, 6, 17)
        self.t["contrat"].date_debut_contrat = "2025-05-13"
        self.db.commit()
        self.bulletin = calculate_payslip(self.db, self.t["contrat"].id, 10, 2026)
        self.base = f"{API}/etablissements/{self.etab.id}/declarations-cnps"

    def tearDown(self):
        self.db.close()

    def _valider(self):
        self.bulletin.statut = "valide"
        self.db.commit()

    def _generer(self):
        return client.post(f"{self.base}/2026/10", headers=self.entetes)

    # ─── Aperçu et anomalies ───────────────────────────────

    def test_apercu_bloque_tant_que_le_bulletin_n_est_pas_valide(self):
        apercu = client.get(f"{self.base}/2026/10/apercu", headers=self.entetes).json()
        self.assertTrue(apercu["bloquee"])
        self.assertTrue(any("non validé" in a["message"] for a in apercu["anomalies"]))
        r = self._generer()
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.db.query(M.DSN).count(), 0)

    def test_numero_cnps_manquant_bloque(self):
        self._valider()
        self.t["salarie"].numero_securite_sociale = None
        self.db.commit()
        apercu = client.get(f"{self.base}/2026/10/apercu", headers=self.entetes).json()
        self.assertTrue(any("N° CNPS manquant" in a["message"] and a["niveau"] == "bloquant" for a in apercu["anomalies"]))

    def test_mois_sans_bulletin_bloque(self):
        apercu = client.get(f"{self.base}/2026/11/apercu", headers=self.entetes).json()
        self.assertTrue(apercu["bloquee"])

    def test_contrat_sans_bulletin_signale(self):
        self._valider()
        autre = make_salarie(self.db, self.etab, matricule="M999")
        make_contrat(self.db, self.t["dossier"], self.etab, autre, numero="C999", date_debut_contrat="2026-01-01")
        apercu = client.get(f"{self.base}/2026/10/apercu", headers=self.entetes).json()
        self.assertFalse(apercu["bloquee"])
        self.assertTrue(any("sans bulletin" in a["message"] for a in apercu["anomalies"]))

    # ─── Génération ────────────────────────────────────────

    def test_generation_fige_les_lignes(self):
        self._valider()
        r = self._generer()
        self.assertEqual(r.status_code, 200, r.text[:400])
        corps = r.json()
        self.assertEqual(corps["statut"], "generee")
        self.assertEqual(corps["effectif"], 1)
        self.assertEqual(corps["masse_salariale"], 300000)
        ligne = corps["lignes"][0]
        self.assertEqual(ligne["numero_cnps"], "202100108350")
        self.assertEqual(ligne["type_salarie"], "M")
        self.assertEqual(ligne["duree_travaillee"], 1)
        self.assertEqual(ligne["branches"], "123")
        self.assertEqual(ligne["base_pf_at_am"], 75000)
        self.assertEqual(ligne["date_embauche"], "2025-05-13")
        self.assertGreater(ligne["cotisation_retraite"], 0)
        totaux = corps["totaux"]
        self.assertAlmostEqual(totaux["total_cotisations"], sum(totaux["cotisations"].values()), places=2)

    def test_branche_retraite_exclue(self):
        self._valider()
        self.t["contrat"].cnps_branches = "23"
        self.db.commit()
        ligne = self._generer().json()["lignes"][0]
        self.assertEqual(ligne["cotisation_retraite"], 0)
        self.assertEqual(ligne["base_retraite"], 0)
        self.assertGreater(ligne["cotisation_pf"], 0)

    def test_depart_dans_le_mois(self):
        self._valider()
        self.db.add(M.DepartSalarie(contrat_id=self.t["contrat"].id, date_sortie="2026-10-31", motif_sortie=59))
        self.db.commit()
        self.assertEqual(self._generer().json()["lignes"][0]["date_depart"], "2026-10-31")

    def test_liste_des_douze_mois(self):
        self._valider()
        self._generer()
        mois = client.get(f"{self.base}?annee=2026", headers=self.entetes).json()
        self.assertEqual(len(mois), 12)
        octobre = mois[9]
        self.assertEqual(octobre["bulletins"], 1)
        self.assertEqual(octobre["bulletins_valides"], 1)
        self.assertEqual(octobre["declaration"]["statut"], "generee")
        self.assertIsNone(mois[0]["declaration"])

    def test_ecart_si_le_bulletin_change_apres_generation(self):
        self._valider()
        declaration_id = self._generer().json()["id"]
        self.bulletin.salaire_brut = 350000
        self.db.commit()
        lu = client.get(f"{API}/declarations-cnps/{declaration_id}", headers=self.entetes).json()
        self.assertTrue(lu["ecart_bulletins"])
        self.assertEqual(lu["masse_salariale"], 300000)

    # ─── Fichier e-CNPS ────────────────────────────────────

    def test_fichier_au_format_du_modele(self):
        from openpyxl import load_workbook
        self._valider()
        declaration_id = self._generer().json()["id"]
        r = client.get(f"{API}/declarations-cnps/{declaration_id}/fichier", headers=self.entetes)
        self.assertEqual(r.status_code, 200)
        self.assertIn("cotisation_nominative_CNPS_10-2026.xlsx", r.headers["content-disposition"])
        feuille = load_workbook(BytesIO(r.content)).active
        entetes = [c.value for c in feuille[1]]
        self.assertEqual(entetes[0], "NUMERO CNPS")
        self.assertTrue(entetes[6].startswith("TYPE SALARIE"))
        self.assertTrue(entetes[9].startswith("BRANCHE COTISEE"))
        ligne = [c.value for c in feuille[2]]
        self.assertEqual(ligne[0], 202100108350)
        self.assertEqual(ligne[3].date(), date(1994, 6, 17))
        self.assertEqual(ligne[6:10], ["M", 1, 300000, 123])

    # ─── Dépôt et verrouillage ─────────────────────────────

    def test_depot_verrouille_puis_annulation(self):
        self._valider()
        declaration_id = self._generer().json()["id"]
        url = f"{API}/declarations-cnps/{declaration_id}"
        r = client.put(f"{url}/depot", headers=self.entetes,
                       json={"date_depot": "2026-11-10", "reference_depot": "6025432"})
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(r.json()["statut"], "deposee")
        self.assertEqual(r.json()["reference_depot"], "6025432")

        self.assertEqual(self._generer().status_code, 409)
        self.assertEqual(client.delete(url, headers=self.entetes).status_code, 409)

        r = client.delete(f"{url}/depot", headers=self.entetes)
        self.assertEqual(r.json()["statut"], "generee")
        self.assertEqual(self._generer().status_code, 200)
        self.assertEqual(client.delete(url, headers=self.entetes).status_code, 204)

    # ─── Droits ────────────────────────────────────────────

    def test_un_autre_cabinet_n_y_accede_pas(self):
        self._valider()
        declaration_id = self._generer().json()["id"]
        autre = auth_headers(make_tenant(self.db, "autre-cabinet")["user"])
        self.assertIn(client.get(f"{self.base}?annee=2026", headers=autre).status_code, (403, 404))
        self.assertIn(client.get(f"{API}/declarations-cnps/{declaration_id}", headers=autre).status_code, (403, 404))

    def test_le_client_n_y_accede_pas(self):
        compte = make_user(self.db, "client-decl@exemple.ci", role="client", dossier_id=self.t["dossier"].id)
        self.assertEqual(client.get(f"{self.base}?annee=2026", headers=auth_headers(compte)).status_code, 403)


if __name__ == "__main__":
    unittest.main()
