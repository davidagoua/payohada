"""Modes de paiement des salaires.

Référentiel géré par la plateforme ; l'établissement choisit les modes qu'il
accepte ; le salarié est payé par l'un d'eux.
"""
import unittest

from tests.base import (
    API, SessionLocal, auth_headers, client, make_tenant, make_user, reset_database,
)
from app.models import models as M


class ModesPaiementTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.admin = make_user(self.db, "plateforme@payohada.ci", role="cabinet", is_admin=True)
        self.tenant = make_tenant(self.db)
        self.entetes_admin = auth_headers(self.admin)
        self.entetes_cabinet = auth_headers(self.tenant["user"])
        self.etab = self.tenant["etablissement"]
        self.modes = {m.code: m.id for m in self.db.query(M.ModePaiement).all()}

    def tearDown(self):
        self.db.close()

    def _definir_modes(self, codes, etab_id=None):
        return client.put(
            f"{API}/etablissements/{etab_id or self.etab.id}",
            headers=self.entetes_cabinet,
            json={"mode_paiement_ids": [self.modes[c] for c in codes]},
        )

    def _creer_salarie(self, mode_id):
        return client.post(
            f"{API}/etablissements/{self.etab.id}/salaries",
            headers=self.entetes_cabinet,
            json={"nom": "Traoré", "prenom": "Moussa", "mode_paiement_id": mode_id},
        )

    # ─── Référentiel (plateforme) ──────────────────────────

    def test_les_modes_de_depart_sont_proposes(self):
        self.assertEqual(set(self.modes), {"VIREMENT", "MOBILE_MONEY", "ESPECES", "CHEQUE"})

    def test_l_admin_cree_un_mode_avec_un_code_normalise(self):
        r = client.post(f"{API}/modes-paiement", headers=self.entetes_admin,
                        json={"code": "carte prépayée", "libelle": "Carte prépayée"})
        self.assertEqual(r.status_code, 201, r.text[:300])
        self.assertEqual(r.json()["code"], "CARTE_PREPAYEE")

    def test_code_en_double_refuse(self):
        r = client.post(f"{API}/modes-paiement", headers=self.entetes_admin,
                        json={"code": "virement", "libelle": "Autre virement"})
        self.assertEqual(r.status_code, 400)

    def test_seule_la_plateforme_modifie_le_referentiel(self):
        mode_id = self.modes["ESPECES"]
        self.assertEqual(client.post(f"{API}/modes-paiement", headers=self.entetes_cabinet,
                                     json={"code": "X", "libelle": "X"}).status_code, 403)
        self.assertEqual(client.put(f"{API}/modes-paiement/{mode_id}", headers=self.entetes_cabinet,
                                    json={"libelle": "Cash"}).status_code, 403)
        self.assertEqual(client.delete(f"{API}/modes-paiement/{mode_id}",
                                       headers=self.entetes_cabinet).status_code, 403)

    def test_un_cabinet_ne_voit_que_les_modes_actifs(self):
        client.put(f"{API}/modes-paiement/{self.modes['CHEQUE']}", headers=self.entetes_admin,
                   json={"est_actif": False})
        codes_cabinet = {m["code"] for m in client.get(f"{API}/modes-paiement", headers=self.entetes_cabinet).json()}
        codes_admin = {m["code"] for m in client.get(f"{API}/modes-paiement", headers=self.entetes_admin).json()}
        self.assertNotIn("CHEQUE", codes_cabinet)
        self.assertIn("CHEQUE", codes_admin)

    def test_un_mode_utilise_ne_se_supprime_pas(self):
        self._definir_modes(["ESPECES"])
        r = client.delete(f"{API}/modes-paiement/{self.modes['ESPECES']}", headers=self.entetes_admin)
        self.assertEqual(r.status_code, 409)
        r = client.delete(f"{API}/modes-paiement/{self.modes['CHEQUE']}", headers=self.entetes_admin)
        self.assertEqual(r.status_code, 204)

    # ─── Établissement ─────────────────────────────────────

    def test_l_etablissement_choisit_ses_modes(self):
        r = self._definir_modes(["VIREMENT", "MOBILE_MONEY"])
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual([m["code"] for m in r.json()["modes_paiement"]], ["VIREMENT", "MOBILE_MONEY"])
        lu = client.get(f"{API}/etablissements/{self.etab.id}", headers=self.entetes_cabinet).json()
        self.assertEqual(len(lu["modes_paiement"]), 2)

    def test_une_mise_a_jour_sans_la_liste_conserve_les_modes(self):
        self._definir_modes(["ESPECES"])
        r = client.put(f"{API}/etablissements/{self.etab.id}", headers=self.entetes_cabinet,
                       json={"raison_sociale": "Nouveau nom"})
        self.assertEqual([m["code"] for m in r.json()["modes_paiement"]], ["ESPECES"])

    def test_mode_inconnu_ou_desactive_refuse(self):
        r = client.put(f"{API}/etablissements/{self.etab.id}", headers=self.entetes_cabinet,
                       json={"mode_paiement_ids": [99999]})
        self.assertEqual(r.status_code, 400)
        client.put(f"{API}/modes-paiement/{self.modes['CHEQUE']}", headers=self.entetes_admin,
                   json={"est_actif": False})
        self.assertEqual(self._definir_modes(["CHEQUE"]).status_code, 400)

    def test_un_mode_desactive_deja_choisi_reste_en_place(self):
        self._definir_modes(["CHEQUE", "ESPECES"])
        client.put(f"{API}/modes-paiement/{self.modes['CHEQUE']}", headers=self.entetes_admin,
                   json={"est_actif": False})
        r = self._definir_modes(["CHEQUE", "ESPECES"])
        self.assertEqual(r.status_code, 200, r.text[:300])

    def test_retirer_un_mode_encore_utilise_est_refuse(self):
        self._definir_modes(["VIREMENT", "ESPECES"])
        self.assertEqual(self._creer_salarie(self.modes["ESPECES"]).status_code, 200)
        r = self._definir_modes(["VIREMENT"])
        self.assertEqual(r.status_code, 409)
        self.assertIn("Espèces", r.json()["detail"])

    # ─── Salarié ───────────────────────────────────────────

    def test_le_salarie_est_paye_par_un_mode_de_son_etablissement(self):
        self._definir_modes(["MOBILE_MONEY"])
        r = self._creer_salarie(self.modes["MOBILE_MONEY"])
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(r.json()["mode_paiement"]["code"], "MOBILE_MONEY")

    def test_un_mode_non_accepte_par_l_etablissement_est_refuse(self):
        self._definir_modes(["VIREMENT"])
        self.assertEqual(self._creer_salarie(self.modes["ESPECES"]).status_code, 400)

        salarie_id = self.tenant["salarie"].id
        r = client.put(f"{API}/salaries/{salarie_id}", headers=self.entetes_cabinet,
                       json={"mode_paiement_id": self.modes["ESPECES"]})
        self.assertEqual(r.status_code, 400)
        r = client.put(f"{API}/salaries/{salarie_id}", headers=self.entetes_cabinet,
                       json={"mode_paiement_id": self.modes["VIREMENT"]})
        self.assertEqual(r.status_code, 200, r.text[:300])

    def test_le_mode_reste_facultatif_pour_l_api(self):
        # Salariés existants et imports : le formulaire l'exige, pas l'API.
        self.assertEqual(self._creer_salarie(None).status_code, 200)

    def test_un_autre_cabinet_ne_modifie_pas_les_modes(self):
        autre = make_tenant(self.db, "autre-cabinet")
        r = client.put(f"{API}/etablissements/{self.etab.id}", headers=auth_headers(autre["user"]),
                       json={"mode_paiement_ids": [self.modes["ESPECES"]]})
        self.assertIn(r.status_code, (403, 404))


if __name__ == "__main__":
    unittest.main()
