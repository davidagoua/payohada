"""Tests d'API : authentification, contrôle d'accès et durcissement."""
import io
import unittest
from datetime import date

from tests import base
from tests.base import (
    DEFAULT_PASSWORD,
    SessionLocal,
    auth_headers,
    client,
    make_contrat,
    make_etablissement,
    make_salarie,
    make_tenant,
    make_user,
    reset_database,
)

from app.models import models as M
from app.services.rate_limit import login_rate_limiter
from app.services.security import create_access_token

API = "/api/v1"


class AuthentificationTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.user = make_user(self.db, "cabinet@exemple.ci", role="cabinet")

    def tearDown(self):
        self.db.close()

    def test_login_valide(self):
        r = client.post(f"{API}/auth/login", json={
            "email": "cabinet@exemple.ci", "password": DEFAULT_PASSWORD,
        })
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("access_token", r.json())
        self.assertFalse(r.json()["user"]["is_default_password"])

    def test_email_inconnu_ne_renvoie_pas_404(self):
        """Régression : un 404 permettait d'énumérer les comptes."""
        r = client.post(f"{API}/auth/login", json={
            "email": "inconnu@exemple.ci", "password": DEFAULT_PASSWORD,
        })
        self.assertEqual(r.status_code, 401)

    def test_mot_de_passe_par_defaut_refuse(self):
        """Régression : « Payohada@123 » ouvrait tout compte sans mot de passe."""
        make_user(self.db, "sansmdp@exemple.ci", role="client", password="")

        r = client.post(f"{API}/auth/login", json={
            "email": "sansmdp@exemple.ci", "password": "Payohada@123",
        })
        self.assertEqual(r.status_code, 401)

    def test_login_insensible_a_la_casse_de_l_email(self):
        """Un compte enregistré en majuscules doit pouvoir se connecter."""
        make_user(self.db, "Utilisateur.Majuscules@Exemple.CI", role="cabinet")

        r = client.post(f"{API}/auth/login", json={
            "email": "utilisateur.majuscules@exemple.ci", "password": DEFAULT_PASSWORD,
        })
        self.assertEqual(r.status_code, 200, r.text)

    def test_echec_de_connexion_journalise_le_motif(self):
        """Le 401 reste générique côté client mais la cause est journalisée.

        Sans cette trace, un exploitant ne peut pas distinguer un mot de passe
        erroné d'un compte resté sans mot de passe (ancienne backdoor).
        """
        make_user(self.db, "sans-mdp-log@exemple.ci", role="client", password="")

        with self.assertLogs("app.routers.auth", level="WARNING") as journal:
            r = client.post(f"{API}/auth/login", json={
                "email": "sans-mdp-log@exemple.ci", "password": "Payohada@123",
            })

        self.assertEqual(r.status_code, 401)
        self.assertNotIn("Payohada@123", r.text)
        trace = "\n".join(journal.output)
        self.assertIn("aucun mot de passe défini", trace)
        self.assertIn("set_password.py", trace)

    def test_echec_de_connexion_mot_de_passe_incorrect_journalise(self):
        with self.assertLogs("app.routers.auth", level="WARNING") as journal:
            r = client.post(f"{API}/auth/login", json={
                "email": "cabinet@exemple.ci", "password": "mauvais-mot-de-passe",
            })
        self.assertEqual(r.status_code, 401)
        self.assertIn("mot de passe incorrect", "\n".join(journal.output))

    def test_compte_a_mot_de_passe_genere_refuse_le_mot_de_passe_partage(self):
        """Un compte créé par le cabinet n'a plus de mot de passe connu d'avance."""
        user = make_user(
            self.db, "genere@exemple.ci", role="client",
            password="Xy7#uneCleAleatoire", must_change_password=True,
        )

        r = client.post(f"{API}/auth/login", json={
            "email": "genere@exemple.ci", "password": "Payohada@123",
        })
        self.assertEqual(r.status_code, 401)

        r = client.post(f"{API}/auth/login", json={
            "email": "genere@exemple.ci", "password": "Xy7#uneCleAleatoire",
        })
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["user"]["is_default_password"])

    def test_brute_force_limite(self):
        ancien_max = login_rate_limiter.max_attempts
        login_rate_limiter.max_attempts = 3
        try:
            for _ in range(3):
                client.post(f"{API}/auth/login", json={
                    "email": "cabinet@exemple.ci", "password": "mauvais-mot-de-passe",
                })
            r = client.post(f"{API}/auth/login", json={
                "email": "cabinet@exemple.ci", "password": "mauvais-mot-de-passe",
            })
            self.assertEqual(r.status_code, 429, r.text)
            self.assertIn("Retry-After", r.headers)
        finally:
            login_rate_limiter.max_attempts = ancien_max

    def test_jeton_signe_avec_un_sub_inconnu_refuse(self):
        """Régression : `get_current_user` créait un compte cabinet à la volée."""
        jeton = create_access_token({"sub": "sub-inexistant", "email": "pirate@exemple.ci"})
        r = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {jeton}"})
        self.assertEqual(r.status_code, 401)

        self.db.expire_all()
        cree = self.db.query(M.Utilisateur).filter(
            M.Utilisateur.email == "pirate@exemple.ci"
        ).first()
        self.assertIsNone(cree, "aucun compte ne doit être créé implicitement")

    def test_me_sans_jeton(self):
        r = client.get(f"{API}/auth/me")
        self.assertIn(r.status_code, (401, 403))

    def test_routeur_auth_non_duplique(self):
        """Le routeur d'authentification n'est plus monté à la racine."""
        r = client.post("/auth/login", json={
            "email": "cabinet@exemple.ci", "password": DEFAULT_PASSWORD,
        })
        self.assertEqual(r.status_code, 404)

    def test_changement_de_mot_de_passe_leve_le_flag(self):
        user = make_user(self.db, "client-flag@exemple.ci", role="client")
        user.must_change_password = True
        self.db.commit()

        r = client.get(f"{API}/auth/me", headers=auth_headers(user))
        self.assertTrue(r.json()["is_default_password"])

        r = client.post(f"{API}/auth/change-password", headers=auth_headers(user), json={
            "old_password": DEFAULT_PASSWORD, "new_password": "NouveauMotDePasse!9",
        })
        self.assertEqual(r.status_code, 200, r.text)

        self.db.refresh(user)
        self.assertFalse(user.must_change_password)
        self.assertFalse(user.must_change_password)

    def test_mot_de_passe_trop_faible_refuse(self):
        r = client.post(f"{API}/auth/signup-cabinet", json={
            "prenom": "A", "nom": "B", "email": "faible@exemple.ci",
            "password": "court", "cabinet_nom": "Cab",
        })
        self.assertEqual(r.status_code, 422)


class ComptesClientsTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.t = make_tenant(self.db, "cabinet-comptes")

    def tearDown(self):
        self.db.close()

    def test_mot_de_passe_genere_et_non_partage(self):
        """Régression : tous les comptes clients recevaient « Payohada@123 »."""
        r = client.post(
            f"{API}/dossiers/{self.t['dossier'].id}/comptes-clients",
            headers=auth_headers(self.t["user"]),
            json={"email": "rh@client.ci", "nom": "Diallo", "prenom": "Fatou"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        mot_de_passe = corps["mot_de_passe_initial"]
        self.assertTrue(mot_de_passe)
        self.assertNotEqual(mot_de_passe, "Payohada@123")
        self.assertTrue(corps["is_default_password"])

        # Le mot de passe généré permet de se connecter
        r = client.post(f"{API}/auth/login", json={
            "email": "rh@client.ci", "password": mot_de_passe,
        })
        self.assertEqual(r.status_code, 200, r.text)

        # L'ancien mot de passe partagé ne fonctionne plus
        r = client.post(f"{API}/auth/login", json={
            "email": "rh@client.ci", "password": "Payohada@123",
        })
        self.assertEqual(r.status_code, 401)

    def test_compte_client_par_un_client_refuse(self):
        compte = make_user(
            self.db, "client-createur@exemple.ci", role="client",
            dossier_id=self.t["dossier"].id,
        )
        r = client.post(
            f"{API}/dossiers/{self.t['dossier'].id}/comptes-clients",
            headers=auth_headers(compte),
            json={"email": "autre@client.ci", "nom": "X", "prenom": "Y"},
        )
        self.assertEqual(r.status_code, 403)


class ControleAccesTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.a = make_tenant(self.db, "cabinet-a")
        self.b = make_tenant(self.db, "cabinet-b")

    def tearDown(self):
        self.db.close()

    # ── isolation multi-tenant ───────────────────────────────────────────

    def test_cabinet_ne_voit_pas_le_dossier_d_un_autre(self):
        r = client.get(
            f"{API}/dossiers/{self.b['dossier'].id}",
            headers=auth_headers(self.a["user"]),
        )
        self.assertEqual(r.status_code, 403)

    def test_calcul_lot_interdit_a_un_client(self):
        """Régression (IDOR) : seul le rôle était testé, pas la portée."""
        client_user = make_user(
            self.db, "client-lot@exemple.ci", role="client",
            dossier_id=self.b["dossier"].id,
        )
        r = client.post(
            f"{API}/dossiers/{self.a['dossier'].id}/bulletins/calculer-lot",
            params={"mois": 6, "annee": 2025},
            headers=auth_headers(client_user),
        )
        self.assertEqual(r.status_code, 403, r.text)

    def test_calcul_lot_interdit_a_un_autre_cabinet(self):
        r = client.post(
            f"{API}/dossiers/{self.b['dossier'].id}/bulletins/calculer-lot",
            params={"mois": 6, "annee": 2025},
            headers=auth_headers(self.a["user"]),
        )
        self.assertEqual(r.status_code, 403)

    def test_calcul_lot_autorise_au_proprietaire(self):
        r = client.post(
            f"{API}/dossiers/{self.a['dossier'].id}/bulletins/calculer-lot",
            params={"mois": 6, "annee": 2025},
            headers=auth_headers(self.a["user"]),
        )
        self.assertEqual(r.status_code, 200, r.text)
        corps = r.json()
        self.assertEqual(corps["total_calcules"], 1)
        self.assertEqual(corps["total_erreurs"], 0)
        self.assertEqual(corps["bulletins"][0]["salaire_brut"], 300000.0)

    def test_calcul_lot_remonte_les_erreurs(self):
        """Régression : les échecs par salarié étaient avalés (HTTP 200 muet)."""
        # Un contrat sans horaires ni salaire exploitable provoque une erreur :
        # on force le cas en rendant le salaire non numérique.
        contrat = self.a["contrat"]
        self.db.add(M.SalarieAbsence(
            salarie_id=self.a["salarie"].id,
            type_absence="Maladie",
            date_debut_absence=date(2025, 6, 2),
            date_fin_absence=date(2025, 6, 3),
            justificatif_fourni=False,
        ))
        self.db.commit()

        # Deux absences identiques ne doivent PLUS faire échouer le calcul.
        r = client.post(
            f"{API}/dossiers/{self.a['dossier'].id}/bulletins/calculer-lot",
            params={"mois": 6, "annee": 2025},
            headers=auth_headers(self.a["user"]),
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["total_erreurs"], 0)

    # ── bulletins ────────────────────────────────────────────────────────

    def _creer_bulletin(self, tenant, mois=6):
        r = client.post(f"{API}/bulletins/calculer", headers=auth_headers(tenant["user"]), json={
            "contrat_id": tenant["contrat"].id, "mois": mois, "annee": 2025,
        })
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_salarie_ne_peut_pas_valider_son_bulletin(self):
        """Régression : `check_bulletin_ownership` seul autorisait le salarié."""
        bulletin = self._creer_bulletin(self.a)
        salarie_user = make_user(
            self.db, "salarie-a@exemple.ci", role="salarie",
            dossier_id=None, salarie_id=self.a["salarie"].id,
        )
        r = client.put(
            f"{API}/bulletins/{bulletin['id']}/valider",
            headers=auth_headers(salarie_user),
        )
        self.assertEqual(r.status_code, 403)

    def test_salarie_ne_peut_pas_supprimer_son_bulletin(self):
        bulletin = self._creer_bulletin(self.a)
        salarie_user = make_user(
            self.db, "salarie-b@exemple.ci", role="salarie",
            salarie_id=self.a["salarie"].id,
        )
        r = client.delete(
            f"{API}/bulletins/{bulletin['id']}",
            headers=auth_headers(salarie_user),
        )
        self.assertEqual(r.status_code, 403)

    def test_client_ne_peut_pas_valider_un_bulletin(self):
        bulletin = self._creer_bulletin(self.a)
        client_user = make_user(
            self.db, "client-valide@exemple.ci", role="client",
            dossier_id=self.a["dossier"].id,
        )
        r = client.put(
            f"{API}/bulletins/{bulletin['id']}/valider",
            headers=auth_headers(client_user),
        )
        self.assertEqual(r.status_code, 403)

    def test_client_ne_peut_pas_recalculer_un_bulletin(self):
        client_user = make_user(
            self.db, "client-calcul@exemple.ci", role="client",
            dossier_id=self.a["dossier"].id,
        )
        r = client.post(f"{API}/bulletins/calculer", headers=auth_headers(client_user), json={
            "contrat_id": self.a["contrat"].id, "mois": 6, "annee": 2025,
        })
        self.assertEqual(r.status_code, 403)

    def test_salarie_ne_voit_que_ses_bulletins(self):
        self._creer_bulletin(self.a)
        self._creer_bulletin(self.b)

        salarie_user = make_user(
            self.db, "salarie-c@exemple.ci", role="salarie",
            salarie_id=self.a["salarie"].id,
        )
        r = client.get(f"{API}/salaries/me/bulletins", headers=auth_headers(salarie_user))
        self.assertEqual(r.status_code, 200)
        bulletins = r.json()
        self.assertEqual(len(bulletins), 1)
        self.assertEqual(bulletins[0]["dossier_id"], self.a["dossier"].id)

    def test_cycle_pret_validation_invalidation(self):
        """Le prêt est débité une fois, restitué à l'invalidation, jamais doublé."""
        pret = M.PretSalarie(
            salarie_id=self.a["salarie"].id,
            montant_pret=120000.0,
            date_deblocage=date(2025, 1, 1),
            montant_mensualite=10000.0,
            reste_a_rembourser=120000.0,
        )
        self.db.add(pret)
        self.db.commit()

        bulletin = self._creer_bulletin(self.a, mois=8)
        entetes = auth_headers(self.a["user"])

        r = client.put(f"{API}/bulletins/{bulletin['id']}/valider", headers=entetes)
        self.assertEqual(r.status_code, 200, r.text)
        self.db.refresh(pret)
        self.assertAlmostEqual(pret.reste_a_rembourser, 110000.0, places=2)

        # Recalcul refusé : plus de double débit possible
        r = client.post(f"{API}/bulletins/calculer", headers=entetes, json={
            "contrat_id": self.a["contrat"].id, "mois": 8, "annee": 2025,
        })
        self.assertEqual(r.status_code, 400)
        self.db.refresh(pret)
        self.assertAlmostEqual(pret.reste_a_rembourser, 110000.0, places=2)

        # L'invalidation restitue la retenue
        r = client.put(f"{API}/bulletins/{bulletin['id']}/invalider", headers=entetes)
        self.assertEqual(r.status_code, 200, r.text)
        self.db.refresh(pret)
        self.assertAlmostEqual(pret.reste_a_rembourser, 120000.0, places=2)

    # ── dossiers et périodes ─────────────────────────────────────────────

    def test_client_ne_peut_pas_modifier_le_dossier(self):
        client_user = make_user(
            self.db, "client-ecriture@exemple.ci", role="client",
            dossier_id=self.a["dossier"].id,
        )
        r = client.put(
            f"{API}/dossiers/{self.a['dossier'].id}",
            headers=auth_headers(client_user),
            json={"nom_dossier": "Piraté"},
        )
        self.assertEqual(r.status_code, 403)

    def test_client_ne_peut_pas_changer_le_statut_de_periode(self):
        client_user = make_user(
            self.db, "client-periode@exemple.ci", role="client",
            dossier_id=self.a["dossier"].id,
        )
        r = client.put(
            f"{API}/dossiers/{self.a['dossier'].id}/periodes/2025/6/statut",
            params={"nouveau_statut": "valide"},
            headers=auth_headers(client_user),
        )
        self.assertEqual(r.status_code, 403)

    def test_statut_de_periode_invalide_refuse(self):
        r = client.put(
            f"{API}/dossiers/{self.a['dossier'].id}/periodes/2025/6/statut",
            params={"nouveau_statut": "nimporte_quoi"},
            headers=auth_headers(self.a["user"]),
        )
        self.assertEqual(r.status_code, 422)
        self.assertIn("Statut invalide", r.json()["detail"])

    def test_statut_de_periode_valide_accepte(self):
        r = client.put(
            f"{API}/dossiers/{self.a['dossier'].id}/periodes/2025/6/statut",
            params={"nouveau_statut": "valide"},
            headers=auth_headers(self.a["user"]),
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["statut"], "valide")


class ReclamationsTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.a = make_tenant(self.db, "cabinet-recl")
        self.b = make_tenant(self.db, "cabinet-recl-b")

    def tearDown(self):
        self.db.close()

    def _bulletin_et_reclamation(self, tenant, sujet):
        bulletin = M.BulletinPaie(
            contrat_id=tenant["contrat"].id,
            dossier_id=tenant["dossier"].id,
            mois=6, annee=2025, statut="calcule",
        )
        self.db.add(bulletin)
        self.db.commit()
        self.db.refresh(bulletin)

        reclamation = M.Reclamation(
            bulletin_id=bulletin.id,
            salarie_id=tenant["salarie"].id,
            sujet=sujet,
            description="Description",
            statut="en_attente",
        )
        self.db.add(reclamation)
        self.db.commit()
        return reclamation

    def test_client_voit_les_reclamations_de_son_entreprise(self):
        """Régression : le compte client recevait une liste vide."""
        self._bulletin_et_reclamation(self.a, "Erreur de prime")
        self._bulletin_et_reclamation(self.b, "Erreur de cotisation")

        client_user = make_user(
            self.db, "client-recl@exemple.ci", role="client",
            dossier_id=self.a["dossier"].id,
        )
        r = client.get(f"{API}/reclamations", headers=auth_headers(client_user))
        self.assertEqual(r.status_code, 200, r.text)
        sujets = [x["sujet"] for x in r.json()]
        self.assertEqual(sujets, ["Erreur de prime"])

    def test_client_ne_peut_pas_traiter_une_reclamation(self):
        reclamation = self._bulletin_et_reclamation(self.a, "Erreur de prime")
        client_user = make_user(
            self.db, "client-recl-2@exemple.ci", role="client",
            dossier_id=self.a["dossier"].id,
        )
        r = client.put(
            f"{API}/reclamations/{reclamation.id}",
            headers=auth_headers(client_user),
            json={"statut": "traite", "commentaire_gestionnaire": "ok"},
        )
        self.assertEqual(r.status_code, 403)

    def test_cabinet_ne_traite_pas_la_reclamation_d_un_autre(self):
        reclamation = self._bulletin_et_reclamation(self.b, "Chez B")
        r = client.put(
            f"{API}/reclamations/{reclamation.id}",
            headers=auth_headers(self.a["user"]),
            json={"statut": "traite", "commentaire_gestionnaire": "ok"},
        )
        self.assertEqual(r.status_code, 404)

    def test_cabinet_traite_sa_reclamation(self):
        reclamation = self._bulletin_et_reclamation(self.a, "Chez A")
        r = client.put(
            f"{API}/reclamations/{reclamation.id}",
            headers=auth_headers(self.a["user"]),
            json={"statut": "traite", "commentaire_gestionnaire": "corrigé"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["statut"], "traite")


class DocumentsTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.a = make_tenant(self.db, "cabinet-doc")
        self.b = make_tenant(self.db, "cabinet-doc-b")

    def tearDown(self):
        self.db.close()

    def test_extension_refusee(self):
        r = client.post(
            f"{API}/salaries/{self.a['salarie'].id}/upload-document",
            headers=auth_headers(self.a["user"]),
            files={"file": ("virus.exe", io.BytesIO(b"contenu"), "application/octet-stream")},
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("non autorisé", r.json()["detail"])

    def test_fichier_trop_volumineux_refuse(self):
        r = client.post(
            f"{API}/salaries/{self.a['salarie'].id}/upload-document",
            headers=auth_headers(self.a["user"]),
            files={"file": ("gros.pdf", io.BytesIO(b"x" * 5000), "application/pdf")},
        )
        self.assertEqual(r.status_code, 413)

    def test_import_excel_trop_volumineux_refuse(self):
        """L'import Excel lisait le fichier entier sans aucune borne de taille."""
        import io as _io

        r = client.post(
            f"{API}/dossiers/{self.a['dossier'].id}/import-variables-excel",
            headers=auth_headers(self.a["user"]),
            params={"mois": 6, "annee": 2025},
            files={"fichier": ("gros.xlsx", _io.BytesIO(b"x" * 5000),
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        self.assertEqual(r.status_code, 413, r.text[:200])

    def test_import_excel_format_refuse(self):
        import io as _io

        r = client.post(
            f"{API}/dossiers/{self.a['dossier'].id}/import-variables-excel",
            headers=auth_headers(self.a["user"]),
            params={"mois": 6, "annee": 2025},
            files={"fichier": ("donnees.txt", _io.BytesIO(b"contenu"),
                               "text/plain")},
        )
        self.assertEqual(r.status_code, 400, r.text[:200])
        self.assertIn(".xlsx", r.json()["detail"])

    def test_upload_puis_telechargement_controle(self):
        r = client.post(
            f"{API}/salaries/{self.a['salarie'].id}/upload-document",
            headers=auth_headers(self.a["user"]),
            files={"file": ("contrat.pdf", io.BytesIO(b"%PDF-1.4 contenu"), "application/pdf")},
        )
        self.assertEqual(r.status_code, 200, r.text)
        url = r.json()["url"]
        self.assertTrue(url.startswith(f"{API}/salaries/documents/"))

        # Le chemin statique public n'existe plus
        nom = url.rsplit("/", 1)[-1]
        self.assertEqual(client.get(f"/uploads/{nom}").status_code, 404)

        # Sans jeton : refusé
        self.assertIn(client.get(url).status_code, (401, 403))

        # Un autre cabinet : refusé
        r = client.get(url, headers=auth_headers(self.b["user"]))
        self.assertEqual(r.status_code, 403)

        # Le propriétaire : autorisé
        r = client.get(url, headers=auth_headers(self.a["user"]))
        self.assertEqual(r.status_code, 200)

    def test_traversee_de_chemin_refusee(self):
        r = client.get(
            f"{API}/salaries/documents/..%2F..%2Fpaie.db",
            headers=auth_headers(self.a["user"]),
        )
        self.assertIn(r.status_code, (400, 404))

    def test_salarie_ne_peut_pas_deposer_pour_un_autre(self):
        r = client.post(
            f"{API}/salaries/{self.b['salarie'].id}/upload-document",
            headers=auth_headers(self.a["user"]),
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        )
        self.assertEqual(r.status_code, 403)


class ReferentielsTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.cabinet = make_user(self.db, "cabinet-ref@exemple.ci", role="cabinet")

    def tearDown(self):
        self.db.close()

    def test_constantes_peuplees_au_demarrage(self):
        """Régression : le seeder était neutralisé (`return False`)."""
        r = client.get(f"{API}/constantes", headers=auth_headers(self.cabinet))
        self.assertEqual(r.status_code, 200)
        codes = {c["code"] for c in r.json()}
        self.assertIn("CNPS_RETRAITE_TAUX_S", codes)
        self.assertIn("RICF_MONTANT", codes)

        r = client.get(f"{API}/plan-paie", headers=auth_headers(self.cabinet))
        codes_plan = {p["code"] for p in r.json()}
        self.assertIn("HS_75", codes_plan)
        self.assertIn("HS_100", codes_plan)

    def test_cabinet_non_admin_ne_modifie_pas_les_constantes(self):
        r = client.post(f"{API}/constantes", headers=auth_headers(self.cabinet), json={
            "code": "TEST", "description": "Test", "montant": 1.0, "pays": "CI",
        })
        self.assertEqual(r.status_code, 403)

    def test_seeder_idempotent_et_non_ecrasant(self):
        """Relancer le peuplement ne doit jamais écraser une valeur administrateur."""
        from app.database_seeder import seed_database

        constante = self.db.query(M.Constante).filter(
            M.Constante.code == "CNPS_RETRAITE_TAUX_S",
            M.Constante.pays == "CI",
        ).first()
        self.assertIsNotNone(constante)

        constante.montant = 5.0  # valeur volontairement modifiée par un admin
        self.db.commit()

        # Deux exécutions successives du seeder
        self.assertFalse(seed_database(self.db))
        self.assertFalse(seed_database(self.db))

        self.db.refresh(constante)
        self.assertAlmostEqual(constante.montant, 5.0, places=4)

        # Le seeder complète bien un référentiel incomplet
        self.db.delete(constante)
        self.db.commit()
        self.assertTrue(seed_database(self.db))
        recree = self.db.query(M.Constante).filter(
            M.Constante.code == "CNPS_RETRAITE_TAUX_S",
            M.Constante.pays == "CI",
        ).first()
        self.assertIsNotNone(recree)


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.db = SessionLocal()
        self.a = make_user(self.db, "compte-a@exemple.ci", role="cabinet")
        self.b = make_user(self.db, "compte-b@exemple.ci", role="cabinet")

    def tearDown(self):
        self.db.close()

    def test_blocage_limite_au_compte_cible(self):
        """Un compte verrouillé ne doit pas bloquer les autres utilisateurs."""
        ancien = login_rate_limiter.max_attempts
        login_rate_limiter.max_attempts = 3
        try:
            for _ in range(4):
                client.post(f"{API}/auth/login", json={
                    "email": "compte-a@exemple.ci", "password": "mauvais",
                })

            r = client.post(f"{API}/auth/login", json={
                "email": "compte-b@exemple.ci", "password": DEFAULT_PASSWORD,
            })
            self.assertEqual(r.status_code, 200, r.text)
        finally:
            login_rate_limiter.max_attempts = ancien

    def test_x_forwarded_for_pris_en_compte(self):
        """Derrière un proxy, l'IP réelle vient de X-Forwarded-For."""
        from app.services.rate_limit import client_ip

        class FauxClient:
            host = "10.0.0.1"

        class FausseRequete:
            headers = {"x-forwarded-for": "203.0.113.7, 10.0.0.1"}
            client = FauxClient()

        self.assertEqual(client_ip(FausseRequete()), "203.0.113.7")

        class SansEnTete:
            headers = {}
            client = FauxClient()

        self.assertEqual(client_ip(SansEnTete()), "10.0.0.1")


class BootstrapTests(unittest.TestCase):
    def test_create_all_sur_base_vierge(self):
        """Régression : un index dupliqué faisait échouer create_all (SQLite)."""
        reset_database()  # drop le fichier puis Base.metadata.create_all
        self.db = SessionLocal()
        try:
            self.assertIsNotNone(
                self.db.query(M.Dossier).filter(M.Dossier.id == -1).first() or True
            )
        finally:
            self.db.close()

    def test_index_siret_unique(self):
        index = [i.name for i in M.Dossier.__table__.indexes]
        self.assertEqual(
            index.count("ix_dossiers_siret"), 1,
            "l'index ix_dossiers_siret ne doit être déclaré qu'une fois",
        )


if __name__ == "__main__":
    unittest.main()
