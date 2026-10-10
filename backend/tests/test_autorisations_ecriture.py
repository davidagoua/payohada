"""Contrôles d'autorisation sur les routes d'écriture.

Ces tests existent parce que leur absence a permis une **escalade de
privilèges** : les gardes de propriété (`check_contrat_ownership`,
`check_salarie_ownership`) autorisent volontairement les rôles « client » et
« salarié » — c'est légitime en **lecture** (consulter son bulletin), mais elles
servaient de protection unique en **écriture**. Un salarié authentifié pouvait
donc modifier son propre contrat, s'octroyer une prime ou changer sa situation
familiale, donc son assiette d'impôt.

Chaque route d'écriture doit désormais refuser ces deux rôles.
"""
import unittest

from tests import base
from tests.base import (
    API, SessionLocal, auth_headers, client, make_contrat, make_salarie,
    make_tenant, make_user, reset_database,
)

from app.models import models as M


class AutorisationsEcritureTests(unittest.TestCase):
    """Un client ou un salarié ne doit jamais pouvoir écrire."""

    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-autorisations")
        self.dossier = self.t["dossier"]
        self.etab = self.t["etablissement"]
        self.contrat = self.t["contrat"]
        self.salarie = self.t["salarie"]

        # Un salarié rattaché au dossier, et son compte nominatif
        self.compte_salarie = make_user(
            self.db, "salarie-autorisations@exemple.ci", role="salarie",
            dossier_id=self.dossier.id, salarie_id=self.salarie.id,
        )
        self.compte_client = make_user(
            self.db, "client-autorisations@exemple.ci", role="client",
            dossier_id=self.dossier.id,
        )
        self.compte_admin = make_user(
            self.db, "admin-autorisations@exemple.ci", role="cabinet", is_admin=True,
        )
        self.db.commit()

        self.entetes_salarie = auth_headers(self.compte_salarie)
        self.entetes_client = auth_headers(self.compte_client)
        self.entetes_cabinet = auth_headers(self.t["user"])
        self.entetes_admin = auth_headers(self.compte_admin)

    def tearDown(self):
        self.db.close()

    # ── Contrat ───────────────────────────────────────────────────────

    def test_modification_de_contrat_refusee_au_salarie(self):
        """Il pouvait auparavant modifier son propre salaire."""
        r = client.put(
            f"{API}/contrats/{self.contrat.id}", headers=self.entetes_salarie,
            json={"salaire_mensuel": 5_000_000.0},
        )
        self.assertEqual(r.status_code, 403, r.text[:200])
        self.db.refresh(self.contrat)
        self.assertNotEqual(self.contrat.salaire_mensuel, 5_000_000.0)

    def test_modification_de_contrat_refusee_au_client(self):
        r = client.put(
            f"{API}/contrats/{self.contrat.id}", headers=self.entetes_client,
            json={"salaire_mensuel": 5_000_000.0},
        )
        self.assertEqual(r.status_code, 403)

    def test_suppression_de_contrat_refusee_au_salarie(self):
        r = client.delete(f"{API}/contrats/{self.contrat.id}",
                          headers=self.entetes_salarie)
        self.assertEqual(r.status_code, 403)
        self.assertIsNotNone(
            self.db.query(M.Contrat).filter(M.Contrat.id == self.contrat.id).first()
        )

    def test_declaration_de_depart_refusee_au_salarie(self):
        r = client.post(
            f"{API}/contrats/{self.contrat.id}/depart", headers=self.entetes_salarie,
            json={"date_sortie": "2025-12-31", "motif_sortie": 10},
        )
        self.assertEqual(r.status_code, 403)

    def test_solde_tout_compte_refuse_au_salarie(self):
        r = client.put(
            f"{API}/contrats/{self.contrat.id}/solde-tout-compte",
            headers=self.entetes_salarie,
            json={"indemnite_licenciement": 9_999_999.0},
        )
        self.assertEqual(r.status_code, 403)

    # ── Variables de paie ─────────────────────────────────────────────

    def test_prime_refusee_au_salarie(self):
        """L'exploit mesuré : une prime de 500 000 F créée par le salarié."""
        r = client.post(
            f"{API}/contrats/{self.contrat.id}/primes", headers=self.entetes_salarie,
            json={"code": "PRIME_FRAUDE", "montant": 500_000.0,
                  "mois": 6, "annee": "2025"},
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(
            self.db.query(M.Prime).filter(M.Prime.code == "PRIME_FRAUDE").count(), 0
        )

    def test_absence_refusee_au_salarie(self):
        r = client.post(
            f"{API}/contrats/{self.contrat.id}/absences", headers=self.entetes_salarie,
            json={"code": "ABS_NP", "date_debut": "2025-06-02",
                  "date_fin": "2025-06-30", "mois": 6, "annee": "2025",
                  "nbr_jour_by_user": 20.0},
        )
        self.assertEqual(r.status_code, 403)

    def test_heures_supplementaires_refusees_au_salarie(self):
        r = client.post(
            f"{API}/contrats/{self.contrat.id}/heures-supplementaires",
            headers=self.entetes_salarie,
            json={"code": "HS_50", "nombre": 40.0, "mois": 6, "annee": "2025"},
        )
        self.assertEqual(r.status_code, 403)

    def test_option_refusee_au_salarie(self):
        r = client.post(
            f"{API}/contrats/{self.contrat.id}/options", headers=self.entetes_salarie,
            json={"code": "OPT_FRAUDE", "libelle": "Option", "montant": 500_000.0,
                  "mois": 6, "annee": "2025"},
        )
        self.assertEqual(r.status_code, 403)

    def test_avantages_nature_refuses_au_salarie(self):
        r = client.post(
            f"{API}/contrats/{self.contrat.id}/avantages-nature",
            headers=self.entetes_salarie,
            json={"mois": 6, "annee": "2025", "logement_fourni": True,
                  "nombre_pieces": 7},
        )
        self.assertEqual(r.status_code, 403)

    # ── Salarié ───────────────────────────────────────────────────────

    def test_modification_de_salarie_refusee_au_client(self):
        """Le client pouvait modifier sa propre fiche, dont la situation familiale."""
        r = client.put(
            f"{API}/salaries/{self.salarie.id}", headers=self.entetes_client,
            json={"enfants_charge": 12, "situation_matrimoniale": "Marié"},
        )
        self.assertEqual(r.status_code, 403, r.text[:200])
        self.db.refresh(self.salarie)
        self.assertNotEqual(self.salarie.enfants_charge, 12)

    def test_modification_de_salarie_refusee_au_salarie(self):
        r = client.put(
            f"{API}/salaries/{self.salarie.id}", headers=self.entetes_salarie,
            json={"enfants_charge": 12},
        )
        self.assertEqual(r.status_code, 403)

    def test_suppression_de_salarie_refusee_au_client(self):
        r = client.delete(f"{API}/salaries/{self.salarie.id}",
                          headers=self.entetes_client)
        self.assertEqual(r.status_code, 403)
        self.assertIsNotNone(
            self.db.query(M.Salarie).filter(M.Salarie.id == self.salarie.id).first()
        )

    # ── Données RH ────────────────────────────────────────────────────

    def test_donnees_rh_refusees_au_salarie(self):
        """Les routes RH sont montées sous /salaries et réservées au staff."""
        r = client.post(
            f"{API}/salaries/{self.salarie.id}/entretiens",
            headers=self.entetes_salarie,
            json={"date_entretien": "2025-06-01", "type_entretien": "Annuel",
                  "nom_evaluateur": "Direction"},
        )
        self.assertEqual(r.status_code, 403, r.text[:150])

    def test_l_upload_de_document_est_refuse_au_salarie(self):
        r = client.post(
            f"{API}/salaries/{self.salarie.id}/upload-document",
            headers=self.entetes_salarie,
            files={"file": ("contrat.pdf", b"%PDF-1.4 test", "application/pdf")},
        )
        self.assertIn(r.status_code, (401, 403), r.text[:150])

    # ── Structure du dossier (établissements, départements) ───────────

    def test_creation_d_etablissement_refusee_au_client(self):
        """Le rôle client pouvait créer un établissement dans son dossier."""
        r = client.post(
            f"{API}/dossiers/{self.dossier.id}/etablissements",
            headers=self.entetes_client,
            json={"code": "ETAB01", "raison_sociale": "Établissement client"},
        )
        self.assertEqual(r.status_code, 403, r.text[:200])

    def test_modification_d_etablissement_refusee_au_client(self):
        r = client.put(
            f"{API}/etablissements/{self.etab.id}", headers=self.entetes_client,
            json={"raison_sociale": "Détourné"},
        )
        self.assertEqual(r.status_code, 403)

    def test_suppression_d_etablissement_refusee_au_client(self):
        r = client.delete(f"{API}/etablissements/{self.etab.id}",
                          headers=self.entetes_client)
        self.assertEqual(r.status_code, 403)
        self.assertIsNotNone(
            self.db.query(M.Etablissement).filter(
                M.Etablissement.id == self.etab.id
            ).first()
        )

    def test_creation_de_departement_refusee_au_client(self):
        r = client.post(
            f"{API}/dossiers/{self.dossier.id}/departements",
            headers=self.entetes_client, json={"nom": "Département client"},
        )
        self.assertEqual(r.status_code, 403)

    def test_creation_de_salarie_refusee_au_client(self):
        r = client.post(
            f"{API}/etablissements/{self.etab.id}/salaries",
            headers=self.entetes_client,
            json={"nom": "Intrus", "prenom": "Faux", "matricule": "FRAUDE1"},
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(
            self.db.query(M.Salarie).filter(M.Salarie.matricule == "FRAUDE1").count(), 0
        )

    def test_liste_des_comptes_refusee_au_client(self):
        """La liste expose les adresses email des comptes du dossier."""
        r = client.get(f"{API}/dossiers/{self.dossier.id}/comptes-clients",
                       headers=self.entetes_client)
        self.assertEqual(r.status_code, 403, r.text[:200])

    # ── Dossiers ──────────────────────────────────────────────────────

    def test_creation_de_dossier_refusee_au_salarie(self):
        r = client.post(f"{API}/dossiers", headers=self.entetes_salarie,
                        json={"nom_dossier": "Dossier frauduleux", "code": "FRAUDE01"})
        self.assertEqual(r.status_code, 403, r.text[:200])
        self.assertEqual(
            self.db.query(M.Dossier).filter(M.Dossier.code == "FRAUDE01").count(), 0
        )

    def test_creation_de_dossier_refusee_au_client(self):
        r = client.post(f"{API}/dossiers", headers=self.entetes_client,
                        json={"nom_dossier": "Dossier client", "code": "CLI01"})
        self.assertEqual(r.status_code, 403)

    # ── Les rôles légitimes doivent continuer de fonctionner ──────────

    def test_le_cabinet_conserve_ses_droits(self):
        r = client.put(
            f"{API}/contrats/{self.contrat.id}", headers=self.entetes_cabinet,
            json={"salaire_mensuel": 350_000.0},
        )
        self.assertEqual(r.status_code, 200, r.text[:200])
        self.db.refresh(self.contrat)
        self.assertAlmostEqual(self.contrat.salaire_mensuel, 350_000.0, places=2)

    def test_l_admin_conserve_ses_droits(self):
        r = client.put(
            f"{API}/salaries/{self.salarie.id}", headers=self.entetes_admin,
            json={"enfants_charge": 3},
        )
        self.assertEqual(r.status_code, 200, r.text[:200])

    def test_le_salarie_conserve_l_acces_en_lecture(self):
        """La restriction porte sur l'écriture : consulter reste permis."""
        r = client.get(f"{API}/contrats/{self.contrat.id}",
                       headers=self.entetes_salarie)
        self.assertEqual(r.status_code, 200)

    def test_le_client_conserve_l_acces_en_lecture(self):
        r = client.get(f"{API}/salaries/{self.salarie.id}",
                       headers=self.entetes_client)
        self.assertEqual(r.status_code, 200)


class InvariantAutorisationsTests(unittest.TestCase):
    """Invariant structurel sur l'ensemble des routeurs.

    Un test fonctionnel ne couvre que les routes dont on sait construire un
    appel valide. Cet invariant, lui, balaie **toutes** les routes d'écriture :
    c'est précisément ce qui manquait lorsque la faille a été introduite.
    """

    #: Routes en lecture seule malgré un verbe HTTP d'écriture : aucune
    #: modification en base, donc accès légitime pour qui voit la donnée.
    LECTURE_SEULE = {
        ("calculs_ci.py", "/contrats/{contrat_id}/calculs/rupture"),
        ("calculs_ci.py", "/contrats/{contrat_id}/calculs/deces"),
        ("calculs_ci.py", "/contrats/{contrat_id}/calculs/fin-cdd"),
        ("calculs_ci.py", "/contrats/{contrat_id}/calculs/avantages-nature"),
        ("bulletins.py", "/bulletins/pdf-lot"),
    }

    #: Motif générique : une liste fermée de gardes avait laissé passer
    #: `check_dossier_ownership` et `check_etablissement_ownership`.
    MOTIF_GARDE = r"check_\w*ownership"

    def test_toute_route_d_ecriture_est_reservee_au_staff(self):
        import pathlib
        import re

        routeurs = pathlib.Path(__file__).resolve().parent.parent / "app" / "routers"
        fautives = []

        for fichier in sorted(routeurs.glob("*.py")):
            source = fichier.read_text(encoding="utf-8")
            blocs = re.split(r"\n(?=@router\.(?:get|post|put|delete|patch))", source)
            for bloc in blocs[1:]:
                entete = re.match(
                    r'@router\.(get|post|put|delete|patch)\("([^"]+)"', bloc
                )
                if not entete:
                    continue
                methode, chemin = entete.group(1).upper(), entete.group(2)
                if methode == "GET":
                    continue
                # Seules les routes protégées par une garde de propriété sont
                # concernées : les autres ont leur propre contrôle.
                if not re.search(self.MOTIF_GARDE, bloc):
                    continue
                if (fichier.name, chemin) in self.LECTURE_SEULE:
                    continue
                if not any(
                    garde in bloc
                    for garde in ("require_staff", "require_admin", "is_admin")
                ):
                    fautives.append(f"{fichier.name} {methode} {chemin}")

        self.assertEqual(
            fautives, [],
            "Routes d'écriture sans autorisation explicite du staff "
            "(une garde de propriété autorise aussi les rôles client et salarié) :\n"
            + "\n".join(f"  - {f}" for f in fautives),
        )


class AucunMotDePassePartageTests(unittest.TestCase):
    """Aucun compte ne doit être créé avec un mot de passe présent dans le code."""

    def test_aucun_mot_de_passe_en_dur_dans_les_routeurs(self):
        import pathlib
        import re

        routeurs = pathlib.Path(__file__).resolve().parent.parent / "app" / "routers"
        # Motifs de mots de passe en clair passés à la création de compte
        suspects = re.compile(
            r"""(register_user_in_supabase|get_password_hash|hashed_password)\s*\(
                [^)]*["'][A-Za-z0-9!@#$%*_\-]{6,}["']""",
            re.VERBOSE,
        )
        trouves = []
        for fichier in routeurs.glob("*.py"):
            for numero, ligne in enumerate(
                fichier.read_text(encoding="utf-8").splitlines(), 1
            ):
                if suspects.search(ligne):
                    trouves.append(f"{fichier.name}:{numero} → {ligne.strip()}")
        self.assertEqual(
            trouves, [],
            "Mot de passe en clair détecté à la création d'un compte :\n"
            + "\n".join(trouves),
        )

    def test_le_compte_salarie_cree_a_un_mot_de_passe_propre(self):
        """La synchronisation crée un compte utilisable et non partagé."""
        reset_database()
        db = SessionLocal()
        t = make_tenant(db, "cabinet-mot-de-passe")
        salarie = make_salarie(db, t["etablissement"], matricule="MDP01")
        salarie.email = "salarie-mdp@exemple.ci"
        db.commit()

        from app.routers.salaries import sync_salarie_user

        sync_salarie_user(salarie, db)

        utilisateur = db.query(M.Utilisateur).filter(
            M.Utilisateur.email == "salarie-mdp@exemple.ci"
        ).first()
        self.assertIsNotNone(utilisateur)
        # Le compte doit être utilisable localement…
        self.assertTrue(utilisateur.hashed_password)
        # …avec obligation de changer ce mot de passe à la première connexion…
        self.assertTrue(utilisateur.must_change_password)
        # …et le mot de passe public d'autrefois ne doit plus ouvrir la porte.
        from app.services.security import verify_password

        self.assertFalse(verify_password("Payohada@123", utilisateur.hashed_password))
        db.close()


if __name__ == "__main__":
    unittest.main()
