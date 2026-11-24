"""Formulaire de départ : motif codifié, préavis, modification."""
import unittest

from tests.base import API, SessionLocal, auth_headers, client, make_tenant, make_user, reset_database
from app.models import models as M


class DepartFormulaireTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-depart")
        self.entetes = auth_headers(self.t["user"])
        self.url = f"{API}/contrats/{self.t['contrat'].id}/depart"

    def tearDown(self):
        self.db.close()

    def _declarer(self, **valeurs):
        donnees = {"date_sortie": "2026-10-31", "motif_sortie": 31, "dernier_jour_travaille": "2026-10-31"}
        donnees.update(valeurs)
        return client.post(self.url, headers=self.entetes, json=donnees)

    def test_le_motif_de_sortie_fixe_le_motif_de_calcul(self):
        r = self._declarer()
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(r.json()["motif_fin_contrat"], "fin_cdd")
        self.db.expire_all()
        contrat = self.db.get(M.Contrat, self.t["contrat"].id)
        self.assertEqual(contrat.statut, "termine")

    def test_trois_preavis_et_dates_enregistres(self):
        r = self._declarer(
            motif_sortie=26, date_engagement_procedure="2026-09-15",
            date_notification_rupture="2026-09-30", transaction_en_cours=True,
            type_paiement_preavis01=10, preavis_de01="2026-10-01", preavis_au01="2026-10-15",
            type_paiement_preavis02=1, preavis_de02="2026-10-16", preavis_au02="2026-10-31",
            type_paiement_preavis03=90,
        )
        self.assertEqual(r.status_code, 200, r.text[:300])
        lu = client.get(self.url, headers=self.entetes).json()
        self.assertEqual(lu["motif_fin_contrat"], "licenciement")
        self.assertEqual(lu["preavis_au02"], "2026-10-31")
        self.assertEqual(lu["type_paiement_preavis03"], 90)
        self.assertTrue(lu["transaction_en_cours"])

    def test_motif_ou_preavis_inconnu_refuse(self):
        self.assertEqual(self._declarer(motif_sortie=777).status_code, 422)
        self.assertEqual(self._declarer(type_paiement_preavis01=5).status_code, 422)

    def test_modification_du_depart(self):
        self._declarer()
        r = client.put(self.url, headers=self.entetes,
                       json={"motif_sortie": 59, "date_sortie": "2026-11-15", "maintien_affiliation": True})
        self.assertEqual(r.status_code, 200, r.text[:300])
        corps = r.json()
        self.assertEqual(corps["motif_fin_contrat"], "demission")
        self.assertEqual(corps["date_sortie"], "2026-11-15")
        self.assertTrue(corps["maintien_affiliation"])
        self.db.expire_all()
        self.assertEqual(self.db.get(M.Contrat, self.t["contrat"].id).date_fin_previsionnelle_contrat[:10], "2026-11-15")

    def test_motif_a_preciser_garde_le_motif_de_calcul(self):
        self._declarer(motif_sortie=59)
        r = client.put(self.url, headers=self.entetes, json={"motif_sortie": 34})
        self.assertEqual(r.json()["motif_fin_contrat"], "demission")

    def test_modifier_sans_depart_404(self):
        r = client.put(self.url, headers=self.entetes, json={"motif_sortie": 59})
        self.assertEqual(r.status_code, 404)

    def test_client_ne_modifie_pas_le_depart(self):
        self._declarer()
        compte = make_user(self.db, "client-depart@exemple.ci", role="client", dossier_id=self.t["dossier"].id)
        r = client.put(self.url, headers=auth_headers(compte), json={"motif_sortie": 59})
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
