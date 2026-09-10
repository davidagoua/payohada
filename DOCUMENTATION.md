# 📖 Documentation — PayOHADA Paie

##  Vue d'ensemble
**PayOHADA** est une solution moderne de gestion de la paie et des ressources humaines conforme aux normes juridiques, fiscales et sociales de l'espace **OHADA** (notamment la Côte d'Ivoire et les pays de la zone UEMOA). La solution repose sur un backend **FastAPI (Python)** avec base de données relationnelle (PostgreSQL / SQLite) et un frontend **Nuxt 4 / Vue 3** propulsé par TailwindCSS et `@nuxt/ui`.

##  Démarrage rapide

### Prérequis
- Python 3.10+
- Bun (`bun --version`) ou Node.js 18+
- PostgreSQL ou SQLite

### Lancement du Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python alter_db.py       # Exécute les migrations du schéma
uvicorn app.main:app --reload --port 8000
```

### Lancement du Frontend
```bash
cd frontend
bun install
bun run dev              # Lance le serveur sur http://localhost:3000
```

##  Configuration

### Variables d'environnement Backend (`backend/.env`)
- `DATABASE_URL` : Chaîne de connexion PostgreSQL (`postgresql://...`) ou SQLite (`sqlite:///./paie.db`).
- `SUPABASE_URL` : URL du projet Supabase pour l'authentification externe.
- `SUPABASE_ANON_KEY` : Clé anonyme Supabase.
- `SUPABASE_JWT_SECRET` : Clé secrète pour la signature des JWT locaux et Supabase.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` : Configuration d'envoi d'emails.

### Variables d'environnement Frontend (`frontend/.env`)
- `NUXT_PUBLIC_API_BASE` : URL de l'API backend (ex: `http://localhost:8000`).
- `NUXT_PUBLIC_SUPABASE_URL` : URL Supabase frontend.
- `NUXT_PUBLIC_SUPABASE_ANON_KEY` : Clé anon Supabase.

---

##  Fonctionnalités

### 1. Architecture à 3 Plateformes Distinctes

Le système est cloisonné en trois espaces dédiés avec contrôles d'accès stricts (RBAC) basés sur le champ `role` (`cabinet`, `client`, `salarie`) :

####  Plateforme Cabinet (Expertise Comptable / Gestionnaire de Paie)
- **Rôle** : `cabinet` (et administrateurs).
- **Accès** : `/dossiers`, `/simulation`, `/admin/reclamations`, `/admin`.
- **Fonctionnalités** :
  - Supervision et administration multi-dossiers (création, modification, archivage).
  - Gestion des comptes d'accès pour les entreprises clientes (`POST /dossiers/{id}/comptes-clients`).
  - Configuration globale de la paie : Constantes (SMIG, plafonds CNPS, CMU, barèmes fiscaux), Plan de paie, Secteurs et grilles conventionnelles.
  - Suivi des variables saisies et transmises par les clients pour chaque mois.
  - Calcul individuel et **calcul en lot** des bulletins pour toute l'entreprise (`POST /dossiers/{id}/bulletins/calculer-lot`).
  - Validation et clôture des périodes de paie.
  - Traitement des réclamations déposées par les salariés (réponse, statut `traite` ou `rejete`).
  - Sélecteur rapide dans le header permettant de prévisualiser l'application en mode Cabinet, Client ou Salarié.

####  Plateforme Client (Entreprise / Dossier)
- **Rôle** : `client` (rattaché à son entreprise via `dossier_id`).
- **Accès** : `/client`, `/client/variables`, `/client/bulletins`, `/client/salaries`, `/client/reclamations`.
- **Fonctionnalités** :
  - **Tableau de bord Entreprise** : Indicateurs de la période active (Mois / Année), effectif, statut d'avancement du cycle de paie.
  - **Saisie des Variables de Paie du Mois** :
    - Grille collective interactive de tous les salariés avec ajout rapide d'éléments :
      * **Heures supplémentaires** (HS15, HS25, HS50, HS75, HS100) avec calcul des majorations.
      * **Congés & Absences** (Congés payés, maladie ordinaire, accident du travail, maternité, absence injustifiée, avec dates et nombre de jours/heures).
      * **Primes & Indemnités** (rendement, transport exceptionnel, panier, gratification, acomptes).
    - Téléchargement de la **Maquette Excel QPXL1501** pré-remplie avec le personnel de l'entreprise.
    - Réimportation directe du fichier Excel complété.
    - **Bouton officiel de transmission au cabinet** (`POST .../transmettre`), marquant la période comme transmise et prête pour le calcul.
  - **Consultation des Bulletins de Paie Entreprise** :
    - Vue globale de la masse salariale brute, du total net à verser et des cotisations patronales.
    - Consultation détaillée et impression/téléchargement des bulletins calculés par le cabinet.
  - **Gestion de l'Effectif** : Annuaire des salariés de l'entreprise et détails des contrats.
  - **Suivi des Réclamations Salariés** : Vue sur les demandes des salariés et les retours du cabinet.

####  Plateforme Employé (Salarié)
- **Rôle** : `salarie` (rattaché à sa fiche salarié via `salarie_id`).
- **Accès** : `/salaries/bulletins`.
- **Fonctionnalités** :
  - Consultation chronologique de tous ses bulletins de paie.
  - Visualisation détaillée conforme (Salaire de base, sursalaire, primes, cotisations CNPS/CMU, impôts IBS/RICF, net à payer).
  - Impression et téléchargement individuel.
  - Suivi des compteurs de congés acquis, pris et restants.
  - **Dépôt de réclamations** : Formulaire pour contester une anomalie sur un bulletin ou un congé avec suivi en direct de la réponse du gestionnaire.
  - Modification sécurisée du mot de passe personnel.

---

##  API / Interfaces

### Authentification & Utilisateurs (`/api/v1/auth`)
- `GET /api/v1/auth/me` : Récupère le profil de l'utilisateur connecté avec son rôle (`cabinet`, `client`, `salarie`), son `dossier_id` et son `nom_dossier`.
- `POST /api/v1/auth/login` : Authentification locale (email + mot de passe) renvoyant le token JWT et les métadonnées de rôle.
- `POST /api/v1/auth/change-password` : Modification du mot de passe.

### Dossiers & Comptes Clients (`/api/v1/dossiers`)
- `GET /api/v1/dossiers` : Liste les dossiers (filtrés par propriétaire pour le cabinet, ou restreint au dossier assigné pour le client).
- `POST /api/v1/dossiers` : Création d'un dossier client (réservé au cabinet).
- `GET /api/v1/dossiers/{id}/comptes-clients` : Liste les utilisateurs clients attachés à un dossier.
- `POST /api/v1/dossiers/{id}/comptes-clients` : Création par le cabinet d'un compte client d'accès à l'entreprise.

### Variables Collectives & Périodes (`/api/v1/dossiers/{id}`)
- `GET /api/v1/dossiers/{id}/periodes/{annee}/{mois}/statut` : État de la période (`saisie_en_cours`, `transmis`, `calcule`, `valide`).
- `POST /api/v1/dossiers/{id}/periodes/{annee}/{mois}/transmettre` : Action de transmission des variables saisies au cabinet.
- `PUT /api/v1/dossiers/{id}/periodes/{annee}/{mois}/statut` : Mise à jour du statut de la période par le cabinet.
- `GET /api/v1/dossiers/{id}/variables-mensuelles` : Grille consolidée des salariés avec heures sup, absences, primes et statut bulletin pour le mois.
- `GET /api/v1/dossiers/{id}/export-variables-excel` : Téléchargement de la matrice Excel QPXL1501 pré-remplie.
- `POST /api/v1/dossiers/{id}/import-variables-excel` : Importation de la matrice Excel pour peupler les variables.

### Bulletins de Paie (`/api/v1/bulletins` & `/api/v1/dossiers/{id}/bulletins`)
- `GET /api/v1/dossiers/{id}/bulletins` : Bulletins du dossier (accessible au cabinet et au client de ce dossier).
- `POST /api/v1/dossiers/{id}/bulletins/calculer-lot` : Calcul en masse de tous les bulletins d'un dossier pour un mois.
- `GET /api/v1/salaries/me/bulletins` : Bulletins personnels du salarié connecté.
- `POST /api/v1/bulletins/calculer` : Calcul d'un bulletin individuel.
- `PUT /api/v1/bulletins/{id}/valider` : Validation définitive d'un bulletin.

### Réclamations (`/api/v1/reclamations`)
- `POST /api/v1/reclamations` : Création d'une réclamation par un salarié sur l'un de ses bulletins.
- `GET /api/v1/reclamations` : Liste des réclamations (ses réclamations pour le salarié, toutes celles du dossier pour le client et le cabinet).
- `PUT /api/v1/reclamations/{id}` : Réponse et traitement de la réclamation par le cabinet.

---

##  Architecture

```text
logiciel_paie/
├── backend/
│   ├── app/
│   │   ├── models/models.py       # Utilisateur (rôles), PeriodePaie, Dossier, Salarie, Contrat, BulletinPaie...
│   │   ├── routers/
│   │   │   ├── auth.py            # Authentification et enrichissement de profil (rôles)
│   │   │   ├── dossiers.py        # Gestion des dossiers et comptes clients
│   │   │   ├── variables.py       # Saisie des variables individuelles et collectives, statut des périodes
│   │   │   ├── bulletins.py       # Calcul unitaire et en lot, consultation multi-rôles
│   │   │   ├── import_export_excel.py # Export/import matrice QPXL1501
│   │   │   └── reclamations.py    # Dépôt et traitement des réclamations
│   │   ├── schemas/               # Modèles Pydantic pour validation
│   │   └── services/payroll.py    # Moteur de calcul de paie OHADA / UEMOA
│   ├── alter_db.py                # Script de migration automatique SQLite / PostgreSQL
│   └── schema.sql                 # Schéma SQL de référence complet
├── frontend/
│   ├── app/
│   │   ├── composables/           # useSupabase.ts (gestion des rôles & redirection), useApi.ts
│   │   ├── layouts/default.vue    # Layout adaptatif avec barre de navigation par plateforme & switcher de preview
│   │   └── pages/
│   │       ├── client/            # 🏬 Espace Entreprise (Dashboard, Saisie Variables, Bulletins, Salariés, Réclamations)
│   │       ├── dossiers/          # 🏢 Espace Cabinet (Dossiers, Gestion des paies)
│   │       ├── salaries/          # 👤 Espace Salarié (Bulletins personnels, Réclamations)
│   │       └── login.vue          # Page de connexion unifiée avec cartes d'accès rapide 1-clic pour chaque rôle
└── DOCUMENTATION.md               # Ce fichier unique de documentation
```

---

##  Changelog

### [Unreleased]

#### Added
- Implémentation complète de l'architecture à 3 plateformes : **Cabinet**, **Client (Entreprise)** et **Employé (Salarié)**.
- Champ `role` (`cabinet`, `client`, `salarie`) et clé étrangère `dossier_id` sur le modèle `utilisateurs`.
- Modèle et table `periodes_paie` pour le suivi du statut de transmission de la paie mensuelle (`saisie_en_cours`, `transmis`, `calcule`, `valide`).
- Endpoints de gestion des variables collectives (`GET /dossiers/{id}/variables-mensuelles`) et de transmission officielle au cabinet (`POST /dossiers/{id}/periodes/{annee}/{mois}/transmettre`).
- Endpoint de calcul groupé de tous les bulletins d'un dossier en un clic (`POST /dossiers/{id}/bulletins/calculer-lot`).
- Interface client complète sous `/client` avec tableau de bord, saisie collective des variables (heures sup, congés, absences, primes), consultation des bulletins, annuaire du personnel et suivi des réclamations.
- Barre de navigation adaptative dans `default.vue` avec commutateur d'espaces (Cabinet, Client, Salarié) pour les gestionnaires et administrateurs.
- Cartes d'accès rapide en mode démo sur `/login` pour tester immédiatement chaque plateforme avec 1 clic.
- Mise à jour du fichier de schéma SQL central [`backend/schema.sql`](file:///Users/macbookpro/devspace/logiciel_paie/backend/schema.sql).
