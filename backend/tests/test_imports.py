"""Imports de données de base : modèles, analyse à blanc et exécution."""
import io
import json
import unittest

from openpyxl import Workbook, load_workbook

from tests.base import (
    API, SessionLocal, auth_headers, client, make_tenant, make_user, reset_database,
)

from app.models import models as M


def fichier_xlsx(entetes, lignes):
    classeur = Workbook()
    feuille = classeur.active
    feuille.title = "Données"
    feuille.append(entetes)
    for ligne in lignes:
        feuille.append(ligne)
    flux = io.BytesIO()
    classeur.save(flux)
    return flux.getvalue()


def fichier_csv(entetes, lignes, separateur=";"):
    contenu = separateur.join(entetes) + "\n"
    contenu += "\n".join(separateur.join(str(c) for c in ligne) for ligne in lignes)
    return contenu.encode("utf-8-sig")


class ImportDonneesTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-imports")
        self.entetes = auth_headers(self.t["user"])
        self.dossier = self.t["dossier"]
        self.etab = self.t["etablissement"]

    def tearDown(self):
        self.db.close()

    # ── helpers ──────────────────────────────────────────────────────────

    def _analyser(self, type_import, contenu, nom="import.xlsx", mapping=None, dossier_id=None):
        data = {
            "dossier_id": str(dossier_id or self.dossier.id),
            "type_import": type_import,
        }
        if mapping is not None:
            data["mapping"] = json.dumps(mapping)
        return client.post(
            f"{API}/imports/analyser",
            headers=self.entetes,
            data=data,
            files={"fichier": (nom, contenu, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

    def _executer(self, job_id, ignorer_erreurs=False):
        return client.post(
            f"{API}/imports/{job_id}/executer",
            headers=self.entetes,
            json={"ignorer_erreurs": ignorer_erreurs},
        )

    def _etabs(self):
        return self.db.query(M.Etablissement).filter(M.Etablissement.dossier_id == self.dossier.id).all()

    # ── modèles ──────────────────────────────────────────────────────────

    def test_le_modele_excel_est_telechargeable(self):
        r = client.get(f"{API}/imports/modeles/salaries", headers=self.entetes)
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertIn("spreadsheetml", r.headers["content-type"])
        classeur = load_workbook(io.BytesIO(r.content), read_only=True)
        entetes = [cellule.value for cellule in next(classeur["Données"].iter_rows(max_row=1))]
        self.assertIn("Matricule *", entetes)
        self.assertIn("Code établissement *", entetes)
        self.assertIn("Instructions", classeur.sheetnames)

    def test_les_types_d_import_sont_exposes(self):
        r = client.get(f"{API}/imports/types", headers=self.entetes)
        self.assertEqual(r.status_code, 200, r.text[:300])
        codes = {item["code"] for item in r.json()}
        self.assertEqual(codes, {"etablissements", "salaries", "contrats"})

    # ── établissements ───────────────────────────────────────────────────

    def test_l_analyse_ne_modifie_rien(self):
        avant = len(self._etabs())
        contenu = fichier_xlsx(
            ["Code établissement", "Raison sociale", "Commune", "Email"],
            [["ETB2", "ETS SUD", "Bouaké", "sud@exemple.ci"],
             ["ETB3", "ETS EST", "Abengourou", "est@exemple.ci"]],
        )
        r = self._analyser("etablissements", contenu)
        self.assertEqual(r.status_code, 201, r.text[:500])
        corps = r.json()
        self.assertEqual(corps["job"]["total_lignes"], 2)
        self.assertEqual(corps["job"]["lignes_valides"], 2)
        self.assertEqual(corps["job"]["lignes_erreurs"], 0)
        self.assertEqual(len(self._etabs()), avant)

    def test_execution_des_etablissements(self):
        contenu = fichier_xlsx(
            ["Code établissement", "Raison sociale", "Commune", "Email", "Taux AT (%)"],
            [["ETB2", "ETS SUD", "Bouaké", "sud@exemple.ci", 2],
             ["ETB3", "ETS EST", "Abengourou", "est@exemple.ci", 1.5]],
        )
        analyse = self._analyser("etablissements", contenu).json()
        r = self._executer(analyse["job"]["id"])
        self.assertEqual(r.status_code, 200, r.text[:500])
        corps = r.json()
        self.assertEqual(corps["crees"], 2)
        self.assertEqual(corps["mis_a_jour"], 0)
        codes = {etab.code: etab for etab in self._etabs()}
        self.assertIn("ETB2", codes)
        self.assertIn("ETB3", codes)
        self.assertEqual(codes["ETB2"].raison_sociale, "ETS SUD")

        # Un second import du même fichier met à jour sans dupliquer.
        analyse2 = self._analyser("etablissements", contenu).json()
        r2 = self._executer(analyse2["job"]["id"])
        self.assertEqual(r2.status_code, 200, r2.text[:300])
        self.assertEqual(r2.json()["crees"], 0)
        self.assertEqual(r2.json()["mis_a_jour"], 2)
        self.assertEqual(len([etab for etab in self._etabs() if etab.code == "ETB2"]), 1)

    def test_les_erreurs_bloquent_l_execution(self):
        contenu = fichier_xlsx(
            ["Code établissement", "Raison sociale"],
            [["ETB2", "ETS SUD"], ["ETB2", "Doublon"], ["ETB3", ""]],
        )
        analyse = self._analyser("etablissements", contenu).json()
        self.assertEqual(analyse["job"]["lignes_erreurs"], 2)
        self.assertEqual(len(analyse["erreurs"]), 2)
        refus = self._executer(analyse["job"]["id"])
        self.assertEqual(refus.status_code, 400, refus.text[:300])

        force = self._executer(analyse["job"]["id"], ignorer_erreurs=True)
        self.assertEqual(force.status_code, 200, force.text[:300])
        self.assertEqual(force.json()["crees"], 1)
        self.assertIn("ETB2", {etab.code for etab in self._etabs()})

    # ── salariés ─────────────────────────────────────────────────────────

    def test_import_des_salaries(self):
        contenu = fichier_xlsx(
            ["Code établissement", "Matricule", "Nom", "Prénom", "Situation matrimoniale", "Enfants à charge", "Email personnel"],
            [[self.etab.code, "M100", "Kouadio", "Jean", "Marié(e)", 2, "jean@exemple.ci"],
             [self.etab.code, "M101", "Yao", "Aya", "Célibataire", 0, "aya@exemple.ci"]],
        )
        analyse = self._analyser("salaries", contenu)
        self.assertEqual(analyse.status_code, 201, analyse.text[:500])
        self.assertEqual(analyse.json()["job"]["lignes_valides"], 2)
        r = self._executer(analyse.json()["job"]["id"])
        self.assertEqual(r.status_code, 200, r.text[:500])
        self.assertEqual(r.json()["crees"], 2)
        salaries = (
            self.db.query(M.Salarie)
            .filter(M.Salarie.etablissement_id == self.etab.id)
            .all()
        )
        # Le tenant de test contient déjà un salarié : 1 existant + 2 importés.
        self.assertEqual(len(salaries), 3)
        self.assertEqual({s.matricule for s in salaries}, {self.t["salarie"].matricule, "M100", "M101"})
        jean = next(s for s in salaries if s.matricule == "M100")
        self.assertEqual(jean.enfants_charge, 2)
        self.assertEqual(jean.situation_matrimoniale, "Marié(e)")

        # Mise à jour idempotente.
        contenu2 = fichier_xlsx(
            ["Code établissement", "Matricule", "Nom", "Prénom"],
            [[self.etab.code, "M100", "Kouadio", "Jean-Baptiste"]],
        )
        analyse2 = self._analyser("salaries", contenu2).json()
        r2 = self._executer(analyse2["job"]["id"])
        self.assertEqual(r2.status_code, 200, r2.text[:300])
        self.assertEqual(r2.json()["mis_a_jour"], 1)
        self.db.refresh(jean)
        self.assertEqual(jean.prenom, "Jean-Baptiste")

    def test_salarie_sur_etablissement_inconnu(self):
        contenu = fichier_xlsx(
            ["Code établissement", "Matricule", "Nom", "Prénom"],
            [["INCONNU", "M200", "Koffi", "Awa"]],
        )
        analyse = self._analyser("salaries", contenu).json()
        self.assertEqual(analyse["job"]["lignes_erreurs"], 1)
        self.assertIn("Établissement introuvable", analyse["erreurs"][0]["message"])

    # ── contrats ─────────────────────────────────────────────────────────

    def test_import_des_contrats(self):
        contenu = fichier_xlsx(
            ["Code établissement", "Matricule salarié", "N° contrat", "Type de contrat",
             "Statut professionnel", "Date de début", "Salaire mensuel brut",
             "Indemnité de transport", "Poste / emploi"],
            [[self.etab.code, self.t["salarie"].matricule, "C100", "CDI", "Non-cadre",
              "2024-02-01", 350000, 30000, "Comptable"]],
        )
        analyse = self._analyser("contrats", contenu)
        self.assertEqual(analyse.status_code, 201, analyse.text[:500])
        self.assertEqual(analyse.json()["job"]["lignes_valides"], 1)
        r = self._executer(analyse.json()["job"]["id"])
        self.assertEqual(r.status_code, 200, r.text[:500])
        self.assertEqual(r.json()["crees"], 1)
        contrat = (
            self.db.query(M.Contrat)
            .filter(M.Contrat.dossier_id == self.dossier.id, M.Contrat.numero_contrat == "C100")
            .first()
        )
        self.assertIsNotNone(contrat)
        self.assertEqual(contrat.type_contrat_travail, 10)
        self.assertEqual(contrat.statut_professionnel, 2)
        self.assertEqual(contrat.salaire_mensuel, 350000)
        self.assertIsNotNone(
            self.db.query(M.Horaires).filter(M.Horaires.contrat_id == contrat.id).first()
        )
        self.assertIsNotNone(
            self.db.query(M.JoursHebdomadaires)
            .filter(M.JoursHebdomadaires.contrat_id == contrat.id)
            .first()
        )

    def test_contrat_sans_salarie_est_refuse(self):
        contenu = fichier_xlsx(
            ["Code établissement", "Matricule salarié", "N° contrat", "Type de contrat",
             "Statut professionnel", "Date de début", "Salaire mensuel brut"],
            [[self.etab.code, "M999", "C999", "CDI", "Cadre", "2024-01-01", 400000]],
        )
        analyse = self._analyser("contrats", contenu).json()
        self.assertEqual(analyse["job"]["lignes_erreurs"], 1)
        self.assertIn("Salarié introuvable", analyse["erreurs"][0]["message"])

    # ── mapping et CSV ───────────────────────────────────────────────────

    def test_mapping_personnalise_en_csv(self):
        contenu = fichier_csv(
            ["Mat", "Nom de famille", "Prénom", "Établissement"],
            [["M300", "Kone", "Adama", self.etab.code]],
        )
        mapping = {
            "matricule": "Mat",
            "nom": "Nom de famille",
            "prenom": "Prénom",
            "etablissement_code": "Établissement",
        }
        analyse = self._analyser("salaries", contenu, nom="salaries.csv", mapping=mapping)
        self.assertEqual(analyse.status_code, 201, analyse.text[:500])
        corps = analyse.json()
        self.assertEqual(corps["job"]["lignes_valides"], 1)
        r = self._executer(corps["job"]["id"])
        self.assertEqual(r.status_code, 200, r.text[:500])
        self.assertEqual(r.json()["crees"], 1)

    def test_mapping_manquant_est_signale(self):
        contenu = fichier_csv(["Mat", "Nom", "Prénom"], [["M400", "Koffi", "Awa"]])
        analyse = self._analyser("salaries", contenu, nom="salaries.csv").json()
        self.assertEqual(analyse["job"]["statut"], "mapping_requis")
        self.assertIn("Code établissement", analyse["champs_manquants"])

    # ── permissions et historique ────────────────────────────────────────

    def test_un_client_ne_peut_pas_importer(self):
        client_user = make_user(
            self.db, "client-import@exemple.ci", role="client", dossier_id=self.dossier.id,
        )
        contenu = fichier_xlsx(
            ["Code établissement", "Raison sociale"], [["ETBX", "Test"]],
        )
        r = client.post(
            f"{API}/imports/analyser",
            headers=auth_headers(client_user),
            data={"dossier_id": str(self.dossier.id), "type_import": "etablissements"},
            files={"fichier": ("etabs.xlsx", contenu, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        self.assertEqual(r.status_code, 403, r.text[:300])

    def test_un_autre_cabinet_ne_peut_pas_analyser(self):
        autre = make_tenant(self.db, "cabinet-imports-voisin")
        contenu = fichier_xlsx(
            ["Code établissement", "Raison sociale"], [["ETBX", "Test"]],
        )
        r = client.post(
            f"{API}/imports/analyser",
            headers=auth_headers(autre["user"]),
            data={"dossier_id": str(self.dossier.id), "type_import": "etablissements"},
            files={"fichier": ("etabs.xlsx", contenu, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        self.assertEqual(r.status_code, 403, r.text[:300])

    def test_historique_des_imports(self):
        contenu = fichier_xlsx(
            ["Code établissement", "Raison sociale"], [["ETB2", "ETS SUD"]],
        )
        self._analyser("etablissements", contenu)
        r = client.get(
            f"{API}/imports", headers=self.entetes, params={"dossier_id": self.dossier.id},
        )
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(len(r.json()), 1)
        self.assertEqual(r.json()[0]["type_import"], "etablissements")


if __name__ == "__main__":
    unittest.main()
