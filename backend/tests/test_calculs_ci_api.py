"""Tests d'API des calculateurs réglementaires ivoiriens.

Les montants attendus sont ceux des classeurs fournis.
"""
import unittest

from tests import base
from tests.base import API, SessionLocal, auth_headers, client, make_tenant, reset_database

from app.models import models as M


class CalculateursApiTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-calculs")
        self.contrat = self.t["contrat"]
        self.entetes = auth_headers(self.t["user"])
        # Historique de paie : 12 mois de bulletins
        for mois in range(1, 13):
            self.db.add(M.BulletinPaie(
                contrat_id=self.contrat.id, dossier_id=self.t["dossier"].id,
                mois=mois, annee=2025, statut="calcule", salaire_brut=300_000.0,
            ))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _url(self, suffixe: str) -> str:
        return f"{API}/contrats/{self.contrat.id}{suffixe}"

    # ── Indemnité de licenciement ──────────────────────────────────────

    def test_rupture_avec_salaires_fournis(self):
        r = client.post(self._url("/calculs/rupture"), headers=self.entetes, json={
            "anciennete_mois": 104,
            "salaires_12_mois": [300_000.0] * 12,
        })
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        self.assertTrue(corps["eligible"])
        self.assertAlmostEqual(corps["salaire_global_moyen"], 300_000.0, places=2)
        self.assertAlmostEqual(corps["montant"], 835_000.0, places=2)
        self.assertEqual(len(corps["tranches"]), 3)
        self.assertAlmostEqual(corps["tranches"][1]["montant"], 385_000.0, places=2)

    def test_rupture_utilise_les_bulletins_existants(self):
        """Sans salaires fournis, les 12 derniers bulletins servent de base."""
        r = client.post(self._url("/calculs/rupture"), headers=self.entetes, json={
            "anciennete_mois": 60,
        })
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        self.assertEqual(corps["nombre_salaires_retenus"], 12)
        self.assertAlmostEqual(corps["salaire_global_moyen"], 300_000.0, places=2)
        self.assertAlmostEqual(corps["montant"], 450_000.0, places=2)  # 5 ans × 30 %

    def test_rupture_non_eligible_sous_un_an(self):
        r = client.post(self._url("/calculs/rupture"), headers=self.entetes, json={
            "anciennete_mois": 8,
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["eligible"])
        self.assertEqual(r.json()["montant"], 0.0)

    def test_rupture_faute_lourde(self):
        r = client.post(self._url("/calculs/rupture"), headers=self.entetes, json={
            "anciennete_mois": 104, "faute_lourde": True,
        })
        self.assertFalse(r.json()["eligible"])

    def test_rupture_retraite(self):
        r = client.post(self._url("/calculs/rupture"), headers=self.entetes, json={
            "anciennete_mois": 240, "salaires_12_mois": [300_000.0] * 12,
            "depart_retraite": True,
        })
        self.assertAlmostEqual(r.json()["montant"], 2_175_000.0, places=2)

    # ── Indemnité de décès ────────────────────────────────────────────

    def test_deces_avec_frais_funeraires(self):
        r = client.post(self._url("/calculs/deces"), headers=self.entetes, json={
            "anciennete_mois": 72,
            "salaires_12_mois": [350_000.0] * 12,
            "smhc_mensuel": 125_000.0,
        })
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        self.assertTrue(corps["eligible"])
        self.assertAlmostEqual(corps["indemnite_rupture"], 647_500.0, places=2)
        self.assertEqual(corps["multiplicateur_frais_funeraires"], 4)
        self.assertAlmostEqual(corps["frais_funeraires"], 500_000.0, places=2)
        self.assertAlmostEqual(corps["total"], 1_147_500.0, places=2)

    def test_deces_total_ayants_droit(self):
        r = client.post(self._url("/calculs/deces"), headers=self.entetes, json={
            "anciennete_mois": 72, "salaires_12_mois": [350_000.0] * 12,
            "smhc_mensuel": 125_000.0, "salaire_presence": 200_000.0,
            "conges_acquis": 150_000.0, "autres_droits": 50_000.0,
        })
        self.assertAlmostEqual(r.json()["total_ayants_droit"], 1_547_500.0, places=2)

    def test_deces_sous_un_an_frais_funeraires_seuls(self):
        r = client.post(self._url("/calculs/deces"), headers=self.entetes, json={
            "anciennete_mois": 6, "salaires_12_mois": [350_000.0] * 12,
            "smhc_mensuel": 125_000.0,
        })
        corps = r.json()
        self.assertFalse(corps["eligible"])
        self.assertEqual(corps["indemnite_rupture"], 0.0)
        self.assertAlmostEqual(corps["frais_funeraires"], 375_000.0, places=2)  # 3 ×

    # ── Fin de CDD ────────────────────────────────────────────────────

    def test_fin_cdd_trois_pour_cent(self):
        r = client.post(self._url("/calculs/fin-cdd"), headers=self.entetes, json={
            "total_brut_cdd": 3_750_000.0,
            "sous_motif_fin_cdd": "terme_normal_sans_cdi",
        })
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        self.assertTrue(corps["eligible"])
        self.assertAlmostEqual(corps["indemnite_theorique"], 112_500.0, places=2)
        self.assertAlmostEqual(corps["indemnite_due"], 112_500.0, places=2)

    def test_fin_cdd_exclue_si_cdi_conclu(self):
        r = client.post(self._url("/calculs/fin-cdd"), headers=self.entetes, json={
            "total_brut_cdd": 3_750_000.0, "sous_motif_fin_cdd": "cdi_conclu",
        })
        self.assertFalse(r.json()["eligible"])
        self.assertEqual(r.json()["indemnite_due"], 0.0)

    def test_fin_cdd_utilise_les_bulletins(self):
        r = client.post(self._url("/calculs/fin-cdd"), headers=self.entetes, json={
            "sous_motif_fin_cdd": "terme_normal_sans_cdi",
        })
        # 12 bulletins × 300 000 = 3 600 000 → 3 % = 108 000
        self.assertAlmostEqual(r.json()["total_brut_cdd"], 3_600_000.0, places=2)
        self.assertAlmostEqual(r.json()["indemnite_due"], 108_000.0, places=2)

    # ── Gratification annuelle ────────────────────────────────────────

    def test_gratification_minimum_conventionnel(self):
        r = client.get(self._url("/calculs/gratification"), headers=self.entetes,
                       params={"annee": 2026, "smhc_mensuel": 125_000.0,
                               "jours_service": 270, "taux_entreprise": 0.75})
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        self.assertAlmostEqual(corps["jours_service"], 270.0, places=2)
        self.assertAlmostEqual(corps["prorata"], 0.75, places=6)
        self.assertAlmostEqual(corps["gratification_retenue"], 70_312.5, places=2)

    def test_gratification_alerte_si_smhc_absent(self):
        r = client.get(self._url("/calculs/gratification"), headers=self.entetes,
                       params={"annee": 2026})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["alertes"])

    # ── Congés payés ──────────────────────────────────────────────────

    def test_conges_payes(self):
        r = client.get(self._url("/calculs/conges"), headers=self.entetes,
                       params={"mois_service": 12, "jours_pris": 15,
                               "anciennete_annees": 2})
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        self.assertAlmostEqual(corps["jours_principaux_acquis"], 26.4, places=2)
        self.assertAlmostEqual(corps["solde_jours_ouvrables"], 11.4, places=2)
        self.assertAlmostEqual(corps["solde_jours_calendaires"], 14.25, places=2)
        # Base reprise des bulletins : 12 × 300 000 → journalier 10 000
        self.assertAlmostEqual(corps["salaire_mensuel_moyen"], 300_000.0, places=2)
        self.assertAlmostEqual(corps["montant_conventionnel"], 142_500.0, places=2)
        self.assertIn("conventionnelle supérieure", corps["comparaison"])

    # ── Avantages en nature ───────────────────────────────────────────

    def test_simulation_avantages_nature(self):
        r = client.post(self._url("/calculs/avantages-nature"), headers=self.entetes, json={
            "mois": 6, "annee": "2025",
            "logement_fourni": True, "mobilier_fourni": True,
            "electricite_prise_en_charge": True, "eau_prise_en_charge": True,
            "nombre_pieces": 3, "nombre_climatiseurs": 2,
        })
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        # Le contrat de test a un salaire mensuel de 300 000
        self.assertAlmostEqual(corps["total_avant_participation"], 290_000.0, places=2)
        self.assertAlmostEqual(corps["avantage_imposable"], 290_000.0, places=2)
        self.assertAlmostEqual(corps["salaire_brut_imposable"], 590_000.0, places=2)

    def test_enregistrement_puis_liste_et_suppression(self):
        charge = {
            "mois": 7, "annee": "2025", "logement_fourni": True, "nombre_pieces": 2,
            "vehicule_type": "transport_collectif_forfait",
            "vehicule_forfait_mensuel": 45_000.0,
        }
        r = client.post(self._url("/avantages-nature"), headers=self.entetes, json=charge)
        self.assertEqual(r.status_code, 200, r.text)
        # 80 000 (logement 2 pièces) + (45 000 − 30 000) = 95 000
        self.assertAlmostEqual(r.json()["total_avant_participation"], 95_000.0, places=2)

        r = client.get(self._url("/avantages-nature"), headers=self.entetes,
                       params={"annee": "2025"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 1)
        self.assertEqual(r.json()[0]["nombre_pieces"], 2)

        # Une seconde écriture sur la même période remplace la ligne
        charge["nombre_pieces"] = 4
        client.post(self._url("/avantages-nature"), headers=self.entetes, json=charge)
        r = client.get(self._url("/avantages-nature"), headers=self.entetes,
                       params={"annee": "2025"})
        self.assertEqual(len(r.json()), 1)
        self.assertEqual(r.json()[0]["nombre_pieces"], 4)

        r = client.delete(self._url("/avantages-nature/7/2025"), headers=self.entetes)
        self.assertEqual(r.status_code, 204)
        self.assertEqual(
            self.db.query(M.AvantageEnNature).filter(
                M.AvantageEnNature.contrat_id == self.contrat.id
            ).count(), 0,
        )

    def test_suppression_inexistante(self):
        r = client.delete(self._url("/avantages-nature/3/2025"), headers=self.entetes)
        self.assertEqual(r.status_code, 404)

    # ── Solde de tout compte complet ──────────────────────────────────

    def test_stc_complet_licenciement(self):
        r = client.post(self._url("/solde-tout-compte/complet"), headers=self.entetes, json={
            "motif_fin_contrat": "licenciement",
            "date_sortie": "2025-12-31",
            "salaires_12_mois": [300_000.0] * 12,
            "conges_mois_service": 12,
            "conges_jours_pris": 15,
            "gratification_annee": 2025,
            "gratification_jours_service": 360,
            "indemnite_preavis": 300_000.0,
        })
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        self.assertAlmostEqual(corps["indemnite_licenciement"], 0.0, places=2)
        self.assertAlmostEqual(corps["indemnite_conges_payes"], 142_500.0, places=2)
        self.assertIn("conges", corps["details"])

        stc = self.db.query(M.SoldeToutCompte).filter(
            M.SoldeToutCompte.contrat_id == self.contrat.id
        ).first()
        self.assertIsNotNone(stc)
        self.assertAlmostEqual(stc.indemnite_conges_payes, 142_500.0, places=2)
        self.assertAlmostEqual(stc.indemnite_preavis, 300_000.0, places=2)
        self.assertEqual(stc.statut, "genere")
        self.assertIsNotNone(stc.detail_calcul)

        depart = self.db.query(M.DepartSalarie).filter(
            M.DepartSalarie.contrat_id == self.contrat.id
        ).first()
        self.assertIsNotNone(depart)
        self.assertEqual(depart.motif_fin_contrat, "licenciement")
        self.db.refresh(self.contrat)
        self.assertEqual(self.contrat.statut, "termine")

    def test_stc_complet_deces(self):
        r = client.post(self._url("/solde-tout-compte/complet"), headers=self.entetes, json={
            "motif_fin_contrat": "deces",
            "date_sortie": "2025-12-31",
            "anciennete_mois": 72,
            "salaires_12_mois": [350_000.0] * 12,
            "smhc_mensuel": 125_000.0,
            "gratification_annee": 2025,
            "gratification_jours_service": 360,
        })
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        self.assertAlmostEqual(corps["indemnite_deces"], 647_500.0, places=2)
        # 72 mois > 60 → multiplicateur 4 (et non 3)
        self.assertAlmostEqual(corps["frais_funeraires"], 500_000.0, places=2)

    def test_stc_complet_fin_cdd(self):
        r = client.post(self._url("/solde-tout-compte/complet"), headers=self.entetes, json={
            "motif_fin_contrat": "fin_cdd",
            "sous_motif_fin_cdd": "terme_normal_sans_cdi",
            "date_sortie": "2025-12-31",
        })
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        # 12 × 300 000 = 3 600 000 → 3 % = 108 000
        self.assertAlmostEqual(corps["indemnite_fin_cdd"], 108_000.0, places=2)

    def test_stc_complet_demission_sans_indemnite_de_rupture(self):
        r = client.post(self._url("/solde-tout-compte/complet"), headers=self.entetes, json={
            "motif_fin_contrat": "demission",
            "date_sortie": "2025-12-31",
            "conges_mois_service": 12,
        })
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        self.assertEqual(corps["indemnite_licenciement"], 0.0)
        self.assertEqual(corps["indemnite_fin_cdd"], 0.0)
        self.assertGreater(corps["indemnite_conges_payes"], 0)

    def test_stc_complet_motif_invalide(self):
        r = client.post(self._url("/solde-tout-compte/complet"), headers=self.entetes, json={
            "motif_fin_contrat": "nimporte_quoi",
        })
        self.assertEqual(r.status_code, 422)
        self.assertIn("Motif de fin de contrat invalide", r.json()["detail"])

    def test_get_stc_expose_le_detail_de_calcul(self):
        """La réimpression du bulletin a besoin du détail, désérialisé."""
        client.post(self._url("/solde-tout-compte/complet"), headers=self.entetes, json={
            "motif_fin_contrat": "licenciement",
            "date_sortie": "2025-12-31",
            "anciennete_mois": 104,
            "salaires_12_mois": [300_000.0] * 12,
            "conges_mois_service": 12,
        })
        r = client.get(self._url("/solde-tout-compte"), headers=self.entetes)
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        self.assertIsNotNone(corps["detail_calcul"])
        self.assertIsInstance(corps["details"], dict)
        self.assertEqual(corps["details"]["motif"], "licenciement")
        self.assertEqual(corps["details"]["anciennete_mois"], 104)
        self.assertIn("conges", corps["details"])

    def test_put_stc_conserve_les_nouvelles_composantes_dans_le_total(self):
        """Régression : le recalcul du total ignorait fin de CDD, décès et gratification."""
        client.post(self._url("/solde-tout-compte/complet"), headers=self.entetes, json={
            "motif_fin_contrat": "fin_cdd",
            "sous_motif_fin_cdd": "terme_normal_sans_cdi",
            "date_sortie": "2025-12-31",
        })
        avant = client.get(self._url("/solde-tout-compte"), headers=self.entetes).json()
        self.assertAlmostEqual(avant["indemnite_fin_cdd"], 108_000.0, places=2)

        # Une modification manuelle du préavis ne doit pas effacer les autres
        r = client.put(self._url("/solde-tout-compte"), headers=self.entetes,
                       json={"indemnite_preavis": 50_000.0})
        self.assertEqual(r.status_code, 200, r.text)
        apres = r.json()
        self.assertAlmostEqual(apres["indemnite_preavis"], 50_000.0, places=2)
        self.assertAlmostEqual(apres["indemnite_fin_cdd"], 108_000.0, places=2)
        self.assertAlmostEqual(
            apres["total"],
            (apres["indemnite_fin_cdd"] + apres["indemnite_conges_payes"]
             + apres["indemnite_preavis"] + apres["indemnite_autre"]),
            places=2,
        )

    # ── Contrats d'interface avec les pages Nuxt ──────────────────────
    # Les payloads ci-dessous reproduisent exactement ceux que construisent
    # les écrans (valeurs nulles incluses) : ils garantissent que le frontend
    # et l'API restent compatibles.

    def test_payload_ecran_avantages_nature(self):
        payload = {
            "mois": 6, "annee": "2025",
            "logement_fourni": True, "mobilier_fourni": False,
            "electricite_prise_en_charge": True, "eau_prise_en_charge": False,
            "nombre_pieces": 3, "nombre_climatiseurs": 2.0, "piscine": False,
            "nombre_gardiens": 0.0, "nombre_employes_maison": 0.0, "nombre_cuisiniers": 0.0,
            "cout_mensuel_repas": 0.0, "exoneration_repas_applicable": False,
            "autres_avantages_cout_reel": 0.0, "participation_salarie_hors_vehicule": 0.0,
            "vehicule_type": None, "vehicule_carburant": 0.0, "vehicule_entretien": 0.0,
            "vehicule_assurance": 0.0, "vehicule_vignette": 0.0, "vehicule_autres": 0.0,
            "vehicule_nombre_beneficiaires": 1, "vehicule_forfait_mensuel": 0.0,
            "vehicule_valeur_reelle": 0.0, "vehicule_participation": 0.0,
            "vehicule_valeur_reelle_cnps": 0.0,
            "valeur_reelle_hors_vehicule_cnps": None,
            "est_persistant": True,
        }
        r = client.post(self._url("/avantages-nature"), headers=self.entetes, json=payload)
        self.assertEqual(r.status_code, 200, r.text)
        # 160 000 (logement 3 pièces) + 30 000 (électricité) + 40 000 (2 clim)
        self.assertAlmostEqual(r.json()["total_avant_participation"], 230_000.0, places=2)

    def test_payload_ecran_depart_licenciement(self):
        payload = {
            "motif_fin_contrat": "licenciement",
            "sous_motif_fin_cdd": None,
            "date_sortie": "2025-12-31",
            "anciennete_mois": 104,
            "faute_lourde": False,
            "conditions_retraite_remplies": False,
            "smhc_mensuel": 125_000.0,
            "indemnite_preavis": 300_000.0,
            "indemnite_autre": 0.0,
            "conges_mois_service": 12,
            "conges_jours_pris": 15,
            "conges_jours_supplementaires": 0,
            "conges_methode": "conventionnelle",
            "salaires_12_mois": [300_000.0] * 11 + [None],
            "gratification_annee": 2025,
            "gratification_taux_entreprise": 0.0,
            "gratification_jours_service": 360.0,
        }
        r = client.post(self._url("/solde-tout-compte/complet"), headers=self.entetes, json=payload)
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        self.assertAlmostEqual(corps["indemnite_licenciement"], 835_000.0, places=2)
        self.assertAlmostEqual(corps["gratification"], 93_750.0, places=2)
        # Congés : journalier 10 000 × 14,25 jours calendaires
        self.assertAlmostEqual(corps["indemnite_conges_payes"], 142_500.0, places=2)
        self.assertAlmostEqual(
            corps["total"], 835_000.0 + 93_750.0 + 142_500.0 + 300_000.0, places=2
        )

    def test_payload_ecran_depart_avec_valeurs_vides(self):
        """Champs facultatifs omis ou vides : l'API doit rester permissive."""
        payload = {
            "motif_fin_contrat": "demission",
            "sous_motif_fin_cdd": None,
            "date_sortie": "2025-12-31",
            "anciennete_mois": None,
            "smhc_mensuel": None,
            "indemnite_preavis": 0.0,
            "indemnite_autre": 0.0,
            "conges_mois_service": 24.0,
            "conges_jours_pris": 0.0,
            "conges_jours_supplementaires": 0.0,
            "conges_methode": "decret",
        }
        r = client.post(self._url("/solde-tout-compte/complet"), headers=self.entetes, json=payload)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertAlmostEqual(r.json()["indemnite_licenciement"], 0.0, places=2)

    def test_stc_complet_respecte_le_cloisonnement(self):
        autre = make_tenant(self.db, "cabinet-autre-calculs")
        r = client.post(
            f"{API}/contrats/{autre['contrat'].id}/solde-tout-compte/complet",
            headers=self.entetes, json={"motif_fin_contrat": "licenciement"},
        )
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
