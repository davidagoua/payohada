"""Simulation de départ de la boîte à outils : sans contrat ni enregistrement."""
import unittest

from tests.base import API, SessionLocal, auth_headers, client, make_tenant, reset_database
from app.models import models as M


class SimulationDepartTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.entetes = auth_headers(make_tenant(self.db, "cabinet-simulation")["user"])

    def tearDown(self):
        self.db.close()

    def _simuler(self, **valeurs):
        donnees = {
            "motif": "licenciement", "date_entree": "2018-01-01", "date_sortie": "2026-01-01",
            "salaire_mensuel_moyen": 300000,
        }
        donnees.update(valeurs)
        return client.post(f"{API}/simulations/depart", headers=self.entetes, json=donnees)

    def test_licenciement_huit_ans(self):
        r = self._simuler()
        self.assertEqual(r.status_code, 200, r.text[:300])
        corps = r.json()
        self.assertEqual(corps["anciennete_mois"], 96)
        # 5 ans à 30 % + 3 ans à 35 % de 300 000 = 450 000 + 315 000
        self.assertEqual(corps["rupture"]["montant"], 765000)
        self.assertIsNone(corps["deces"])
        self.assertGreater(corps["total"], corps["rupture"]["montant"])

    def test_faute_lourde_sans_indemnite(self):
        corps = self._simuler(faute_lourde=True).json()
        self.assertEqual(corps["rupture"]["montant"], 0)
        self.assertFalse(corps["rupture"]["eligible"])

    def test_deces_avec_frais_funeraires(self):
        corps = self._simuler(motif="deces", smhc_mensuel=75000).json()
        # Plus de 5 ans et jusqu'à 10 ans : 4 × SMHC
        self.assertEqual(corps["deces"]["frais_funeraires"], 300000)

    def test_fin_de_cdd(self):
        corps = self._simuler(
            motif="fin_cdd", date_entree="2025-01-01", date_sortie="2025-12-31",
            total_brut_cdd=3600000, gratification_active=False, conges_mois_service=0,
        ).json()
        self.assertEqual(corps["fin_cdd"]["indemnite_due"], 108000)
        self.assertEqual(corps["total"], 108000)

    def test_alertes_sans_salaire_minimum(self):
        corps = self._simuler(motif="demission").json()
        self.assertIsNone(corps["gratification"])
        self.assertTrue(any("Gratification" in a for a in corps["alertes"]))

    def test_dates_incoherentes_refusees(self):
        self.assertEqual(self._simuler(date_sortie="2017-01-01").status_code, 400)

    def test_motif_inconnu_refuse(self):
        self.assertEqual(self._simuler(motif="mutation").status_code, 422)

    def test_rien_n_est_enregistre(self):
        self._simuler()
        self.assertEqual(self.db.query(M.DepartSalarie).count(), 0)
        self.assertEqual(self.db.query(M.SoldeToutCompte).count(), 0)

    def test_connexion_requise(self):
        r = client.post(f"{API}/simulations/depart", json={})
        self.assertIn(r.status_code, (401, 403))


if __name__ == "__main__":
    unittest.main()


class SmhcReferenceTests(unittest.TestCase):
    """La liste des contrats donne le salaire minimum retenu, pour pré-remplir."""

    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-smhc")

    def tearDown(self):
        self.db.close()

    def test_smhc_du_contrat_puis_de_la_grille(self):
        contrat = self.t["contrat"]
        url = f"{API}/dossiers/{self.t['dossier'].id}/contrats"
        entetes = auth_headers(self.t["user"])
        self.assertIsNone(client.get(url, headers=entetes).json()[0]["smhc_reference"])

        secteur = M.Secteur(nom="SECTEUR TEST SMHC")
        self.db.add(secteur)
        self.db.commit()
        poste = M.PosteSalaire(secteur_id=secteur.id, categorie_professionnelle="EMPLOYES",
                               echelon_categorie="1", salaire_mensuel_fcfa=80000)
        self.db.add(poste)
        self.db.commit()
        contrat.poste_salaire_id = poste.id
        self.db.commit()
        self.assertEqual(client.get(url, headers=entetes).json()[0]["smhc_reference"], 80000)

        contrat.smhc_mensuel = 95000
        self.db.commit()
        self.assertEqual(client.get(url, headers=entetes).json()[0]["smhc_reference"], 95000)
