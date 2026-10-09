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
python create_admin.py --email admin@moncabinet.ci --password 'MotDePasse!23'  # 1er administrateur
uvicorn app.main:app --reload --port 8000
```

> Les constantes de paie (SMIG, plafonds et taux CNPS, CMU, RICF) et le plan de
> paie sont insérés **automatiquement et de façon idempotente** au démarrage :
> une valeur modifiée par un administrateur n'est jamais écrasée.

### Tests

```bash
cd backend
python -m unittest discover -s tests -t . -v
```

La suite couvre le moteur de paie (CNPS, ITS, RICF, heures supplémentaires,
absences, prêts, mode net→brut, idempotence) et le contrôle d'accès de l'API
(isolation multi-tenant, rôles, pièces jointes, anti brute-force).

##  Migrations de base de données

**La base de production est le PostgreSQL de Supabase : `backend/schema.sql` est
la source de vérité du schéma.** Toute modification de la base doit y être
ajoutée, **de manière incrémentale**, dans la section
`MIGRATION INCREMENTALE` située à la fin du fichier — sans réécrire les
`CREATE TABLE` d'origine, afin de préserver l'historique.

### Appliquer les migrations

Sur une base **existante**, exécuter uniquement la partie incrémentale du
fichier (à partir du repère `-- MIGRATION INCREMENTALE`) :

```bash
# Extraction de la partie incrémentale
sed -n '/-- MIGRATION INCREMENTALE/,$p' backend/schema.sql > /tmp/migration.sql

# Relecture puis application sur la base Supabase
psql "$DATABASE_URL" --single-transaction -f /tmp/migration.sql
```

Sur une base **vierge**, le fichier complet s'applique d'un bloc :

```bash
psql "$DATABASE_URL" --single-transaction -f backend/schema.sql
```

### Règles à respecter

- **Idempotence obligatoire** : `ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT
  EXISTS`, `CREATE INDEX IF NOT EXISTS`, `INSERT ... WHERE NOT EXISTS`, ou blocs
  `DO $$ ... IF NOT EXISTS (SELECT 1 FROM pg_constraint ...) $$`. La section
  incrémentale doit pouvoir être rejouée plusieurs fois sans erreur.
- **Pas de référence en avant** : une colonne ne peut référencer par clé
  étrangère qu'une table déjà créée plus haut dans le fichier.
- **Ordre de déploiement** : appliquer la migration **avant** de déployer le code
  correspondant.
- **Données sensibles** : ne jamais insérer de mot de passe ni de secret.

> Le fichier est validé en continu : il a été appliqué sur une base PostgreSQL
> vierge (40 tables, 97 index) puis sa section incrémentale rejouée trois fois
> de suite sans erreur.

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
- `CORS_ORIGINS` : origines autorisées, séparées par des virgules (obligatoire en production).
- `DEBUG` : `false` en production (désactive `/api/v1/docs` et le détail des erreurs).
- `LOGIN_MAX_ATTEMPTS` / `LOGIN_WINDOW_SECONDS` : quota anti brute-force sur la connexion.
- `MAX_UPLOAD_SIZE_BYTES` / `ALLOWED_UPLOAD_EXTENSIONS` : limites des pièces jointes.
- `BUGSINK_DSN` : facultatif ; si vide, la télémétrie d'erreurs est désactivée.

### Configuration du parcours « mot de passe oublié »

```bash
# URL publique du frontend : sert à construire le lien envoyé par email
FRONTEND_BASE_URL=https://app.payohada.ci
# Durée de validité d'un lien (minutes)
PASSWORD_RESET_EXPIRE_MINUTES=30
```

Le lien envoyé est de la forme
`{FRONTEND_BASE_URL}/reset-password?token=…`. Si `FRONTEND_BASE_URL` est absent
ou faux, l'email part mais le lien ne mène nulle part.

### Configuration de l'envoi d'emails (SMTP)

L'envoi des bulletins utilise `backend/app/services/email.py`. Deux modes sont
supportés :

| Mode | `SMTP_SECURE` | Port typique | Comportement |
|---|---|---|---|
| **SSL implicite** | `true` | `465` | Connexion chiffrée dès l'ouverture (`SMTP_SSL`) |
| **STARTTLS** | `false` | `587` | Connexion en clair puis négociation TLS |

Exemple validé avec Hostinger :

```bash
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=465
SMTP_USER=support@payohada.com
SMTP_PASSWORD=<mot-de-passe-de-la-boite>
SMTP_SECURE=true
SMTP_TIMEOUT=20
EMAIL_FROM=support@payohada.com
EMAIL_FROM_NAME=payohada Paie   # nom affiché chez le destinataire (espaces conseillés)
```

Points d'attention :

- **`SMTP_TIMEOUT`** (défaut 20 s) : l'envoi est synchrone dans la requête HTTP.
  Sans timeout, un serveur SMTP qui ne répond pas immobiliserait un worker
  FastAPI indéfiniment.
- `SMTP_USER` et `SMTP_PASSWORD` doivent correspondre à la **boîte** utilisée
  comme expéditeur, sinon le serveur renvoie `535` et l'API répond
  « Authentification SMTP refusée ».
- L'authentification `SMTPAuthenticationError` **n'expose jamais le mot de passe**
  dans la réponse HTTP ni dans les journaux.
- Sur un serveur de développement sans TLS (MailHog, Mailpit), `SMTP_SECURE=false`
  et l'absence de STARTTLS sont tolérées : l'envoi se poursuit en clair et
  l'événement est journalisé en niveau `INFO`.
- **Vérification rapide** : `POST /api/v1/bulletins/{id}/envoyer-employe`
  renvoie `500` avec un motif exploitable si la configuration est incorrecte.

### Variables d'environnement Frontend (`frontend/.env`)
- `NUXT_PUBLIC_API_BASE` : URL de base de l'API, **préfixe `/api/v1` inclus**
  (ex: `http://localhost:8000/api/v1`).
- `NUXT_PUBLIC_SUPABASE_URL` : URL Supabase frontend.
- `NUXT_PUBLIC_SUPABASE_ANON_KEY` : Clé anon Supabase.
- `NUXT_PUBLIC_BUGSINK_DSN` : facultatif (télémétrie d'erreurs).
- `NUXT_PUBLIC_N8N_CHAT_WEBHOOK` : facultatif ; si vide, le chatbot est masqué.

> ⚠️ **Sécurité** : les secrets de ce projet ont été exposés dans l'historique
> Git. La rotation est décrite dans [`SECURITY.md`](SECURITY.md) et doit être
> effectuée avant toute mise en production.

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
  - **Suivi des Réclamations Salariés** : Vue sur toutes les demandes des salariés de l'entreprise et les retours du cabinet (lecture seule : le traitement est réservé au cabinet).

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
- `POST /api/v1/auth/signup-cabinet` : Inscription d'un nouveau cabinet d'expertise comptable / RH (nom du cabinet, contact, localisation pays OHADA, prénom/nom du gestionnaire, email et mot de passe). Crée le compte avec le rôle `cabinet` et renvoie immédiatement un token JWT pour une connexion directe.
- `GET /api/v1/auth/me` : Récupère le profil de l'utilisateur connecté avec son rôle (`cabinet`, `client`, `salarie`), son `dossier_id`, son `nom_dossier` et les métadonnées cabinet (`cabinet_nom`, `cabinet_telephone`, `cabinet_ville`).
- `POST /api/v1/auth/login` : Authentification locale (email + mot de passe) renvoyant le token JWT et les métadonnées de rôle et cabinet.
- `POST /api/v1/auth/change-password` : Modification du mot de passe.

### Mot de passe oublié (`/api/v1/auth`)
- `POST /api/v1/auth/forgot-password` : Envoie par email un lien de réinitialisation. La réponse est **toujours identique**, que l'adresse existe ou non, afin de ne pas permettre de découvrir les comptes enregistrés.
- `GET /api/v1/auth/reset-password/valider?token=…` : Vérifie un lien **avant** d'afficher le formulaire et retourne l'email masqué (`cd*****@gm***.com`).
- `POST /api/v1/auth/reset-password` : Définit le nouveau mot de passe à partir du jeton.

Parcours utilisateur :

```text
/login  →  « Mot de passe oublié ? »  →  /forgot-password  (saisie de l'email)
        →  email contenant /reset-password?token=…
        →  /reset-password  (vérification du lien, puis nouveau mot de passe)
        →  /login
```

Propriétés de sécurité :

| Propriété | Mise en œuvre |
|---|---|
| Jeton non stocké en clair | Seul le condensat SHA-256 est enregistré (`password_reset_tokens.token_hash`) |
| Durée limitée | `PASSWORD_RESET_EXPIRE_MINUTES` (défaut 30 minutes) |
| Usage unique | `used_at` renseigné à la consommation ; un rejeu répond 400 |
| Un seul lien actif | Une nouvelle demande invalide les jetons précédents |
| Pas d'énumération | Réponse et statut identiques pour une adresse inconnue ; un échec SMTP n'est pas révélé |
| Anti brute-force | 5 demandes / 15 min par compte, 20 / 15 min par IP, 20 / 15 min sur la consommation |
| Jeton invalide après changement | Un changement de mot de passe (profil ou réinitialisation) invalide tous les jetons en attente |
| Ménage | Les jetons expirés depuis plus de 7 jours sont purgés automatiquement |

> Le lien pointe vers `FRONTEND_BASE_URL` : cette variable **doit** être renseignée
> avec l'URL publique du frontend, sinon le lien reçu par email sera inutilisable.

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
- `GET /api/v1/dossiers/{id}/bulletins` : Bulletins du dossier (cabinet propriétaire, client du dossier, salarié pour ses propres bulletins).
- `POST /api/v1/dossiers/{id}/bulletins/calculer-lot` : Calcul en masse des bulletins d'un dossier pour un mois. **Réservé au cabinet propriétaire.** Retourne `{ periode, bulletins, erreurs, total_contrats, total_calcules, total_erreurs }` : les échecs par salarié sont désormais explicites au lieu d'être silencieusement ignorés.
- `GET /api/v1/salaries/me/bulletins` : Bulletins personnels du salarié connecté.
- `POST /api/v1/bulletins/calculer` : Calcul d'un bulletin individuel (cabinet).
- `PUT /api/v1/bulletins/{id}/valider` : Validation définitive d'un bulletin (cabinet).
- `PUT /api/v1/bulletins/{id}/invalider` : Réouverture d'un bulletin validé ; restaure les remboursements de prêts appliqués (cabinet).
- `DELETE /api/v1/bulletins/{id}` : Suppression d'un bulletin non validé (cabinet).

> **Intégrité** : un bulletin au statut `valide` ne peut pas être recalculé. Il
> faut d'abord l'invalider — ce qui rend le cycle *invalider → recalculer →
> valider* idempotent et empêche tout double remboursement de prêt.

### Pièces jointes RH
- `POST /api/v1/salaries/{id}/upload-document` : Téléversement (extensions en liste blanche, 10 Mo maximum, nom de fichier généré côté serveur).
- `GET /api/v1/salaries/documents/{fichier}` : Téléchargement **authentifié et contrôlé** (le dossier `/uploads` n'est plus exposé publiquement).

### Réclamations (`/api/v1/reclamations`)
- `POST /api/v1/reclamations` : Création d'une réclamation par un salarié sur l'un de ses bulletins.
- `GET /api/v1/reclamations` : Liste des réclamations — les siennes pour un salarié, celles de son entreprise pour un compte client, celles de ses dossiers pour le cabinet.
- `PUT /api/v1/reclamations/{id}` : Réponse et traitement de la réclamation (**cabinet uniquement** ; un compte client ne peut pas traiter une réclamation).

### Calculateurs réglementaires CI (`/api/v1/contrats/{id}/...`)

Les six calculateurs issus du référentiel ivoirien sont exposés par l'API. Le
détail des règles et des sources est documenté dans
[`docs/REFERENTIEL_CALCULS_CI.md`](docs/REFERENTIEL_CALCULS_CI.md).

| Endpoint | Rôle |
|---|---|
| `POST /contrats/{id}/calculs/rupture` | Indemnité de licenciement ou de départ à la retraite (30/35/40 %, décret n° 2017-210) |
| `POST /contrats/{id}/calculs/deces` | Indemnité de décès + frais funéraires (3/4/6 × SMHC) |
| `POST /contrats/{id}/calculs/fin-cdd` | Indemnité de fin de CDD (3 %, art. 15.8) |
| `GET /contrats/{id}/calculs/gratification` | Gratification annuelle (75 % du SMHC, prorata 360 jours) |
| `GET /contrats/{id}/calculs/conges` | Droits à congés (2,2 j/mois) et indemnité, deux méthodes comparées |
| `POST /contrats/{id}/calculs/avantages-nature` | Simulation du barème DGI du 08/07/2024 |
| `GET/POST/DELETE /contrats/{id}/avantages-nature` | Saisie des avantages en nature d'un mois |
| `POST /contrats/{id}/solde-tout-compte/complet` | **Calcule et enregistre** le solde de tout compte selon le motif de fin |

Les endpoints `.../calculs/...` sont **sans effet de bord** : ils ne font que
produire un résultat et servir de simulateur. Seul
`solde-tout-compte/complet` écrit en base (départ + solde + détail du calcul).

### Autorisations
La matrice complète des rôles et les règles de portée sont documentées dans
[`SECURITY.md`](SECURITY.md#matrice-des-rôles). Ces contrôles sont appliqués
**côté API** ; le middleware Nuxt (`frontend/app/middleware/auth.global.ts`)
n'est qu'une aide à la navigation.

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
│   │   └── services/
│   │       ├── payroll.py         # Moteur de calcul de paie OHADA / UEMOA
│   │       ├── security.py        # JWT, hachage, génération de mots de passe
│   │       ├── permissions.py     # Rôles et portée multi-tenant
│   │       └── rate_limit.py      # Anti brute-force sur l'authentification
│   ├── tests/                     # Tests de non-régression (unittest)
│   ├── create_admin.py            # Création / promotion d'un administrateur
│   ├── alter_db.py                # Script de migration automatique SQLite / PostgreSQL
│   └── schema.sql                 # Schéma SQL de référence complet
├── frontend/
│   ├── app/
│   │   ├── composables/           # useSupabase.ts (session & rôles), useApi.ts
│   │   ├── middleware/auth.global.ts # Garde de navigation par rôle (confort, pas sécurité)
│   │   ├── layouts/default.vue    # Layout adaptatif avec barre de navigation par plateforme
│   │   └── pages/
│   │       ├── client/            # 🏬 Espace Entreprise (Dashboard, Saisie Variables, Bulletins, Salariés, Réclamations)
│   │       ├── dossiers/          # 🏢 Espace Cabinet (Dossiers, Gestion des paies)
│   │       ├── salaries/          # 👤 Espace Salarié (Bulletins personnels, Réclamations)
│   │       └── login.vue          # Page de connexion unifiée avec cartes d'accès rapide 1-clic pour chaque rôle
├── SECURITY.md                    # Procédure de rotation des secrets & matrice des rôles
├── scripts/purge_git_secrets.sh   # Purge des secrets de l'historique Git (dry-run par défaut)
├── .github/workflows/ci.yml       # Tests backend, build frontend, détection de secrets
└── DOCUMENTATION.md               # Ce fichier unique de documentation
```

---

##  Changelog

### [Unreleased] — Correctifs d'audit sécurité & intégrité

#### Security
- **Suppression de la backdoor mot de passe** : `Payohada@123` n'est plus accepté pour les comptes sans mot de passe, et il n'existe plus aucun mot de passe partagé. Les comptes créés par le cabinet reçoivent un mot de passe aléatoire retourné une seule fois (`mot_de_passe_initial`) avec obligation de le changer (`must_change_password`).
- **Suppression de la création implicite de compte** : un jeton dont le `sub` est inconnu est rejeté (auparavant, il créait un compte `cabinet`).
- **Anti brute-force** sur `/auth/login` (10 tentatives / 5 min par compte, 50 par IP) et message d'erreur unique pour empêcher l'énumération des comptes.
- **CORS restreint** aux origines de `CORS_ORIGINS` (fin du `*` avec credentials).
- **`/uploads` n'est plus public** : les pièces jointes passent par un endpoint authentifié avec contrôle de portée ; extensions en liste blanche et taille limitée à 10 Mo.
- Suppression du compte de démonstration créé sans mot de passe par `alter_db.py` ; la `DATABASE_URL` n'est plus journalisée en clair.
- DSN Bugsink et webhook n8n retirés du code : uniquement par variables d'environnement.
- Ajout de `SECURITY.md`, d'un script de purge d'historique et d'une détection de secrets en CI.

#### Fixed
- **Calcul en lot (IDOR)** : la restriction ne portait que sur le rôle `cabinet` ; un compte client pouvait recalculer la paie de n'importe quel dossier. Réservé au cabinet propriétaire.
- **Collision de codes de lignes** : deux absences (ou deux HS/primes) de même nature dans un mois faisaient échouer le bulletin entier (`UNIQUE constraint failed`). Les codes sont désormais suffixés (`ABS_MALADIE`, `ABS_MALADIE_2`).
- **Bulletins validés protégés** : un recalcul écrasait silencieusement un bulletin clôturé et permettait un double remboursement de prêt. Le recalcul exige une invalidation préalable.
- **Heures supplémentaires 75 % et 100 %** payées au taux de base ; le barème complet (15/25/50/75/100) est maintenant appliqué, avec journalisation des codes inconnus.
- **Cumuls d'heures supplémentaires** : le préfixe littéral `HS_` empêchait la prise en compte des codes `HS15`.
- **`net_imposable`** recalculé avec des taux codés en dur ; il provient désormais du calcul des cotisations, avec déduction de la CMU salariale.
- **`est_persistant` NULL** excluait silencieusement primes et options de la paie.
- **Journée d'absence** incohérente (7 h d'un côté, 8 h de l'autre) ; une base unique est utilisée. Défauts d'horaires alignés sur 40 h/semaine et 173,33 h/mois (au lieu de 35 h / 151,67 h).
- **Bootstrap SQLite** : un index dupliqué (`ix_dossiers_siret`) faisait échouer `create_all` sur une base vierge.
- **Seeder réactivé et rendu idempotent** : les constantes et le plan de paie sont insérés au démarrage, sans jamais écraser une valeur administrateur. Ajout de `create_admin.py` pour disposer d'un administrateur.
- **Entrées non validées** : statut de période contraint à `saisie_en_cours | transmis | calcule | valide` (réservé au cabinet), heures supplémentaires et absences positives, mois 1-12, montants de prime positifs.
- **Réclamations** : un compte client voyait une liste vide ; il voit désormais celles de son entreprise, sans pouvoir les traiter.
- **Rôles** : validation/invalidation/suppression de bulletin et envoi d'emails réservés au cabinet ; modification du dossier réservée au cabinet propriétaire.
- **Routeur `auth` monté deux fois** (`/api/v1/auth` et `/auth`) : montage unique.
- Échappement HTML des données d'état civil dans les emails de bulletins.
- Vérification du mot de passe en temps constant (`hmac.compare_digest`).

#### Base de données (`backend/schema.sql`)
- Ajout d'une section incrémentale idempotente couvrant les correctifs d'audit : colonne `utilisateurs.must_change_password`, défauts d'horaires `173.33` / `40.0`, et entrées `plan_paie` `HS_75` / `HS_100`.
- **Correction d'un défaut bloquant** : `lignes_bulletins_paies.pret_id` référençait `prets_salaries` avant sa création, ce qui faisait échouer toute installation sur base vierge (`relation "prets_salaries" does not exist`). La colonne est désormais ajoutée dans la section incrémentale.
- **Correction d'un fichier corrompu** : 35 lignes contenaient du balisage de document (`[span_N](start_span)`) qui avait fait perdre le préfixe `--` de 28 commentaires et polluait 7 lignes de valeurs de l'`INSERT` « GENS DE MAISON ». Le fichier est maintenant syntaxiquement valide et sans donnée polluée.
- Les deux contraintes de clé étrangère sur `utilisateurs` sont encapsulées dans des blocs `DO $$` idempotents : la section incrémentale est rejouable.
- Le plafond CNPS Prestations Familiales / AT / Maternité (75 000 → 70 000 FCFA) est fourni **commenté** : il modifie le montant des cotisations et doit être validé contre les textes officiels avant activation.

#### Added
- Suite de tests de non-régression (moteur de paie et API) : `python -m unittest discover -s tests -t . -v`.

#### Calculateurs réglementaires ivoiriens
- Nouveaux services purs : `app/services/indemnites_rupture.py` (licenciement, retraite, décès, fin de CDD), `app/services/conges_gratification.py` (congés payés, gratification annuelle) et `app/services/avantages_nature.py` (barème logement, domesticité, repas, véhicule).
- Table `avantages_en_nature` et nouvelles colonnes `contrats.smhc_mensuel`, `departs_salaries.motif_fin_contrat` / `sous_motif_fin_cdd` / `conditions_retraite_remplies`, `soldes_tout_compte.indemnite_fin_cdd` / `indemnite_deces` / `frais_funeraires` / `gratification` / `detail_calcul` — ajoutées en migration incrémentale dans `backend/schema.sql`.
- 9 endpoints API dont un solde de tout compte complet qui sélectionne automatiquement les composantes dues selon le motif de fin de contrat.
- **Intégration au bulletin** : les avantages en nature alimentent le brut imposable (donc la base de l'ITS) via des lignes `AN_*`, sont neutralisés sur le net par une retenue compensatoire (ce sont des gains non décaissés), et utilisent la **valeur réelle** pour l'assiette CNPS, distincte de l'évaluation forfaitaire fiscale.
- **Le calcul de l'indemnité de licenciement n'est plus figé à 0** : l'ancien code créait un solde de tout compte avec `indemnite_licenciement = 0.0`.
- `docs/REFERENTIEL_CALCULS_CI.md` : référentiel des règles, formules, exemples chiffrés et sources.
- 78 tests dédiés (calculateurs, API, intégration au bulletin) validés sur les montants exacts des classeurs fournis.

#### Mot de passe oublié
- Nouveau parcours complet : pages `/forgot-password` et `/reset-password`, lien « Mot de passe oublié ? » sur l'écran de connexion, et trois endpoints API (`forgot-password`, `reset-password/valider`, `reset-password`).
- Table `password_reset_tokens` ajoutée en migration incrémentale dans `backend/schema.sql` : jeton stocké **haché** (SHA-256), à **usage unique**, à durée limitée, avec cascade à la suppression du compte.
- Nouveau service `app/services/password_reset.py` (création, vérification, consommation, invalidation, purge) et `app/services/email_templates.py` pour le gabarit d'email.
- Réglages `FRONTEND_BASE_URL` et `PASSWORD_RESET_EXPIRE_MINUTES` ; la consommation d'un lien lève l'obligation de changer le mot de passe.
- 27 tests dédiés (usage unique, expiration, absence d'énumération, mot de passe faible, jeton haché, échappement HTML, limitation de débit) et 4 tests de navigation supplémentaires.

#### Emails (`app/services/email.py`)
- `send_email()` retourne désormais `(succès, message)` : les endpoints d'envoi de bulletin remontent un motif exploitable (« Authentification SMTP refusée », « Le destinataire … a été refusé ») au lieu d'un message générique.
- Ajout de `SMTP_TIMEOUT` (défaut 20 s) : sans lui, un serveur SMTP muet immobilisait un worker FastAPI, l'envoi étant synchrone dans la requête.
- Journalisation structurée (`logging`) à la place des `print`, erreurs typées et fermeture de connexion systématique (`finally`).
- `formataddr` pour le nom d'expéditeur et validation TLS explicite en mode SSL.
- 7 tests dédiés (envoi simulé) : retour, transmission du timeout, authentification refusée, serveur injoignable, destinataire refusé, SMTP non configuré, mode STARTTLS.
- Workflow CI GitHub Actions (tests backend, build frontend, détection de secrets).
- Endpoint `GET /api/v1/salaries/documents/{fichier}` (téléchargement contrôlé des pièces jointes).
- Middleware Nuxt `auth.global.ts` pour la navigation par rôle.

### [Unreleased] — Fonctionnalités initiales

#### Added
- Implémentation complète de l'architecture à 3 plateformes : **Cabinet**, **Client (Entreprise)** et **Employé (Salarié)**.
- Champ `role` (`cabinet`, `client`, `salarie`) et clé étrangère `dossier_id` sur le modèle `utilisateurs`.
- Modèle et table `periodes_paie` pour le suivi du statut de transmission de la paie mensuelle (`saisie_en_cours`, `transmis`, `calcule`, `valide`).
- Endpoints de gestion des variables collectives (`GET /dossiers/{id}/variables-mensuelles`) et de transmission officielle au cabinet (`POST /dossiers/{id}/periodes/{annee}/{mois}/transmettre`).
- Endpoint de calcul groupé de tous les bulletins d'un dossier en un clic (`POST /dossiers/{id}/bulletins/calculer-lot`).
- Interface client complète sous `/client` avec tableau de bord, saisie collective des variables (heures sup, congés, absences, primes), consultation des bulletins, annuaire du personnel et suivi des réclamations.
- Onglet « Accès Client (Entreprise) » intégré dans la vue détaillée d'un dossier cabinet ([`[id].vue`](file:///Users/macbookpro/devspace/logiciel_paie/frontend/app/pages/dossiers/%5Bid%5D.vue)) permettant de créer et administrer les accès RH des clients.
- Organisation incrémentale des migrations dans [`backend/schema.sql`](file:///Users/macbookpro/devspace/logiciel_paie/backend/schema.sql) à la fin du fichier, préservant l'historique et la structure des tables initiales.
- Cartes d'accès rapide en mode démo sur `/login` pour tester immédiatement chaque plateforme avec 1 clic.
- Mise à jour du fichier de schéma SQL central [`backend/schema.sql`](file:///Users/macbookpro/devspace/logiciel_paie/backend/schema.sql).

#### Fixed
- Ajout de la dépendance `psycopg[binary]>=3.1.0` dans [`backend/requirements.txt`](file:///Users/macbookpro/devspace/logiciel_paie/backend/requirements.txt) pour corriger l'erreur `ModuleNotFoundError: No module named 'psycopg'` lors de l'utilisation d'URLs `postgresql+psycopg://`.
- Normalisation automatique des schémas d'URL PostgreSQL (`postgres://` vers `postgresql://`) et compatibilité duale `psycopg` / `psycopg2` dans [`backend/app/database.py`](file:///Users/macbookpro/devspace/logiciel_paie/backend/app/database.py), [`backend/alembic/env.py`](file:///Users/macbookpro/devspace/logiciel_paie/backend/alembic/env.py) et [`backend/alter_db.py`](file:///Users/macbookpro/devspace/logiciel_paie/backend/alter_db.py).
