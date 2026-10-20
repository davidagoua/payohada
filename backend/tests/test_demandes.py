"""Demandes du salarié : dépôt, décision de l'entreprise, effet sur la paie.

Deux exigences :

* **la décision appartient à l'entreprise** — le cabinet ne valide pas, un
  salarié ne valide pas, une autre entreprise ne voit rien ;
* **ce qui est validé entre dans la paie** — le congé crée une absence, l'acompte
  est retenu sur le bulletin, sans ressaisie.
"""
import unittest
from datetime import date, timedelta

from tests.base import (
    API, SessionLocal, auth_headers, client, make_user, make_tenant, reset_database,
)

from app.models import models as M
from app.services.payroll import calculate_payslip


class DemandesBase(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-demandes")

        # Les trois profils qui entrent en jeu.
        self.entreprise = make_user(
            self.db, "rh@entreprise.ci", role="client",
            dossier_id=self.t["dossier"].id,
        )
        self.salarie = make_user(
            self.db, "salarie@exemple.ci", role="salarie",
            dossier_id=self.t["dossier"].id, salarie_id=self.t["salarie"].id,
        )
        self.db.commit()

        self.entetes_salarie = auth_headers(self.salarie)
        self.entetes_entreprise = auth_headers(self.entreprise)
        self.entetes_cabinet = auth_headers(self.t["user"])

    def tearDown(self):
        self.db.close()

    # ── helpers ──────────────────────────────────────────────────────────

    def _deposer_conge(self, debut=date(2025, 6, 2), fin=date(2025, 6, 8), **extra):
        return client.post(
            f"{API}/demandes/conges", headers=self.entetes_salarie,
            json={
                "date_debut": debut.isoformat(),
                "date_fin": fin.isoformat(),
                "motif": "Congés annuels",
                **extra,
            },
        )

    def _deposer_acompte(self, montant=50_000.0, mois=6, annee=2025, **extra):
        return client.post(
            f"{API}/demandes/acomptes", headers=self.entetes_salarie,
            json={"montant": montant, "mois": mois, "annee": annee, **extra},
        )

    def _valider(self, type_demande: str, demande_id: int, entetes=None, **extra):
        return client.post(
            f"{API}/demandes/{type_demande}/{demande_id}/valider",
            headers=entetes or self.entetes_entreprise, json=extra or None,
        )

    def _refuser(self, type_demande: str, demande_id: int, commentaire=None):
        return client.post(
            f"{API}/demandes/{type_demande}/{demande_id}/refuser",
            headers=self.entetes_entreprise,
            json={"commentaire": commentaire} if commentaire else None,
        )

    def _bulletin(self, mois=6, annee=2025):
        return calculate_payslip(self.db, self.t["contrat"].id, mois, annee)


class DepotDemandeTests(DemandesBase):
    def test_le_salarie_depose_un_conge(self):
        r = self._deposer_conge()
        self.assertEqual(r.status_code, 201, r.text[:300])
        corps = r.json()
        self.assertEqual(corps["statut"], "en_attente")
        self.assertEqual(corps["nombre_jours"], 7.0)  # du 2 au 8 inclus
        self.assertEqual(corps["salarie_id"], self.t["salarie"].id)

    def test_un_chevauchement_est_refuse(self):
        self.assertEqual(self._deposer_conge().status_code, 201)
        r = self._deposer_conge(debut=date(2025, 6, 5), fin=date(2025, 6, 12))
        self.assertEqual(r.status_code, 409, r.text[:200])

    def test_dates_inversees_refusees(self):
        r = self._deposer_conge(debut=date(2025, 6, 10), fin=date(2025, 6, 3))
        self.assertEqual(r.status_code, 422)

    def test_le_gestionnaire_entreprise_ne_depose_pas(self):
        r = client.post(
            f"{API}/demandes/conges", headers=self.entetes_entreprise,
            json={"date_debut": "2025-06-02", "date_fin": "2025-06-08"},
        )
        self.assertEqual(r.status_code, 403)

    def test_le_cabinet_ne_depose_pas(self):
        r = client.post(
            f"{API}/demandes/conges", headers=self.entetes_cabinet,
            json={"date_debut": "2025-06-02", "date_fin": "2025-06-08"},
        )
        self.assertEqual(r.status_code, 403)

    def test_le_salarie_ne_voit_que_ses_demandes(self):
        self._deposer_conge()
        # Demande d'un autre salarié du même établissement
        autre = M.Salarie(
            etablissement_id=self.t["etablissement"].id, matricule="AUTRE",
            nom="Autre", prenom="Salarie",
        )
        self.db.add(autre)
        self.db.commit()
        self.db.add(M.DemandeConge(
            salarie_id=autre.id, date_debut=date(2025, 7, 1),
            date_fin=date(2025, 7, 5), nombre_jours=5.0, statut="en_attente",
        ))
        self.db.commit()

        r = client.get(f"{API}/demandes/conges", headers=self.entetes_salarie)
        self.assertEqual(r.status_code, 200)
        self.assertEqual([d["salarie_id"] for d in r.json()], [self.t["salarie"].id])


class SoldeCongesTests(DemandesBase):
    def _solde(self):
        r = client.get(f"{API}/demandes/conges/solde", headers=self.entetes_salarie)
        self.assertEqual(r.status_code, 200, r.text[:300])
        return r.json()

    def test_le_solde_est_calcule_pour_le_mois_en_cours(self):
        corps = self._solde()
        self.assertEqual(corps["annee"], date.today().year)
        self.assertEqual(corps["mois"], date.today().month)
        self.assertAlmostEqual(
            corps["acquis"], round(corps["mois_anciennete"] * 2.5, 2), places=2
        )
        self.assertAlmostEqual(
            corps["solde"], round(corps["acquis"] - corps["pris"], 2), places=2
        )

    def test_le_solde_de_l_api_est_celui_du_bulletin(self):
        """L'espace salarié et la paie doivent afficher le même solde."""
        from app.routers.bulletins import compute_bulletin_cumuls

        aujourdhui = date.today()
        bulletin = calculate_payslip(
            self.db, self.t["contrat"].id, aujourdhui.month, aujourdhui.year
        )
        cumuls = compute_bulletin_cumuls(self.db, bulletin)
        self.assertAlmostEqual(
            self._solde()["solde"], cumuls.annuel.conges_solde, places=2
        )

    def test_une_demande_validee_reduit_le_solde(self):
        avant = self._solde()["solde"]

        debut = date.today().replace(day=1)
        fin = debut + timedelta(days=2)  # 3 jours
        demande = self._deposer_conge(debut=debut, fin=fin).json()
        self.assertEqual(self._valider("conges", demande["id"]).status_code, 200)

        apres = self._solde()
        self.assertAlmostEqual(apres["pris"] - 3.0, 0.0, places=2)
        self.assertAlmostEqual(apres["solde"], round(avant - 3.0, 2), places=2)

    def test_le_solde_est_reserve_au_salarie(self):
        r = client.get(f"{API}/demandes/conges/solde", headers=self.entetes_entreprise)
        self.assertEqual(r.status_code, 403)


class ValidationCongeTests(DemandesBase):
    def test_la_validation_cree_l_absence(self):
        demande = self._deposer_conge().json()
        r = self._valider("conges", demande["id"])
        self.assertEqual(r.status_code, 200, r.text[:300])
        corps = r.json()
        self.assertEqual(corps["statut"], "validee")
        self.assertTrue(corps["absence_id"])

        absence = self.db.get(M.SalarieAbsence, corps["absence_id"])
        self.assertEqual(absence.type_absence, "Congés payés")
        self.assertEqual(absence.date_debut_absence, date(2025, 6, 2))
        self.assertEqual(absence.date_fin_absence, date(2025, 6, 8))

    def test_le_conge_valide_entre_dans_le_bulletin(self):
        """Le bulletin porte les jours pris, sans amputer le net."""
        reference = self._bulletin()
        net_sans_conge = round(reference.net_a_payer, 2)

        demande = self._deposer_conge().json()
        self.assertEqual(self._valider("conges", demande["id"]).status_code, 200)

        bulletin = self._bulletin()
        codes = {ligne.code for ligne in bulletin.lignes}
        # « Congés payés » est normalisé en CONGES_PAYES par le moteur.
        self.assertIn("CONGES_PRIS", codes)
        self.assertIn("ABS_CONGES_PAYES", codes)
        # Les deux lignes se compensent : le net est inchangé.
        self.assertAlmostEqual(round(bulletin.net_a_payer, 2), net_sans_conge, places=2)

    def test_un_salarie_ne_valide_pas(self):
        demande = self._deposer_conge().json()
        r = self._valider("conges", demande["id"], entetes=self.entetes_salarie)
        self.assertEqual(r.status_code, 403)

    def test_le_cabinet_ne_valide_pas(self):
        demande = self._deposer_conge().json()
        r = self._valider("conges", demande["id"], entetes=self.entetes_cabinet)
        self.assertEqual(r.status_code, 403)

    def test_une_autre_entreprise_ne_valide_pas(self):
        demande = self._deposer_conge().json()
        autre = make_tenant(self.db, "cabinet-demandes-autre")
        r = self._valider("conges", demande["id"], entetes=auth_headers(autre["user"]))
        self.assertEqual(r.status_code, 403)

    def test_une_demande_deja_traitee_ne_se_revalide_pas(self):
        demande = self._deposer_conge().json()
        self.assertEqual(self._valider("conges", demande["id"]).status_code, 200)
        r = self._valider("conges", demande["id"])
        self.assertEqual(r.status_code, 409)

    def test_un_bulletin_valide_bloque_la_decision(self):
        demande = self._deposer_conge().json()
        bulletin = self._bulletin()
        bulletin.statut = "valide"
        self.db.commit()

        r = self._valider("conges", demande["id"])
        self.assertEqual(r.status_code, 409, r.text[:200])
        self.assertIn("validé", r.json()["detail"])

    def test_le_refus_est_motive_et_sans_absence(self):
        demande = self._deposer_conge().json()
        r = self._refuser("conges", demande["id"], "Effectif insuffisant sur la période")
        self.assertEqual(r.status_code, 200, r.text[:200])
        corps = r.json()
        self.assertEqual(corps["statut"], "refusee")
        self.assertEqual(corps["commentaire_gestionnaire"], "Effectif insuffisant sur la période")
        self.assertIsNone(corps["absence_id"])
        self.assertEqual(self.db.query(M.SalarieAbsence).count(), 0)


class AcompteTests(DemandesBase):
    def test_l_acompte_valide_est_retenu_sur_le_bulletin(self):
        reference = self._bulletin()
        net_avant = round(reference.net_a_payer, 2)

        demande = self._deposer_acompte(montant=50_000.0).json()
        self.assertEqual(demande["statut"], "en_attente")

        r = self._valider("acomptes", demande["id"])
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(r.json()["statut"], "validee")

        bulletin = self._bulletin()
        lignes = [ligne for ligne in bulletin.lignes if ligne.code == "ACOMPTE"]
        self.assertTrue(lignes, "aucune ligne d'acompte sur le bulletin")
        self.assertAlmostEqual(lignes[0].montant_cs, 50_000.0, places=2)
        self.assertAlmostEqual(round(bulletin.net_a_payer, 2), round(net_avant - 50_000.0, 2), places=2)

    def test_un_acompte_non_valide_n_est_pas_retenu(self):
        self._bulletin()
        self._deposer_acompte(montant=80_000.0)
        bulletin = self._bulletin()
        self.assertFalse([l for l in bulletin.lignes if l.code == "ACOMPTE"])

    def test_l_acompte_d_un_autre_mois_ne_s_applique_pas(self):
        self._deposer_acompte(montant=80_000.0, mois=7)
        demande = self.db.query(M.DemandeAcompte).first()
        r = self._valider("acomptes", demande.id)
        self.assertEqual(r.status_code, 200, r.text[:200])

        bulletin_juin = self._bulletin(mois=6)
        self.assertFalse([l for l in bulletin_juin.lignes if l.code == "ACOMPTE"])
        bulletin_juillet = self._bulletin(mois=7)
        self.assertTrue([l for l in bulletin_juillet.lignes if l.code == "ACOMPTE"])

    def test_montant_nul_refuse(self):
        r = self._deposer_acompte(montant=0)
        self.assertEqual(r.status_code, 422)

    def test_l_entreprise_voit_les_demandes_de_ses_salaries(self):
        self._deposer_conge()
        self._deposer_acompte()
        r = client.get(f"{API}/demandes/acomptes", headers=self.entetes_entreprise)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 1)
        self.assertEqual(r.json()[0]["salarie_nom"], self.t["salarie"].nom)


if __name__ == "__main__":
    unittest.main()
