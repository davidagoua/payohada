# Sécurité — PayOHADA Paie

## 1. Procédure d'urgence : rotation des secrets

> **À faire en priorité.** Les secrets de production (mot de passe PostgreSQL,
> clés Supabase et surtout `SUPABASE_JWT_SECRET`) ont été committés dans
> l'historique Git, qui est publié sur GitHub. **Toute personne ayant accès au
> dépôt peut forger un jeton d'authentification valide.**

L'ordre des étapes est important : révoquer d'abord, purger ensuite.

> **Avant de déployer le correctif** : appliquer la migration de schéma sur la
> base Supabase (section `MIGRATION INCREMENTALE` de `backend/schema.sql`), puis
> reprendre les comptes sans mot de passe (§1.2.1). Voir
> [`DOCUMENTATION.md`](DOCUMENTATION.md#-migrations-de-base-de-données).

### 1.1 Révoquer et régénérer

| Secret | Action |
|---|---|
| `SUPABASE_JWT_SECRET` | Régénérer le secret JWT Supabase (dashboard → Settings → API → JWT Secret). **Tous les jetons en circulation sont invalidés** : les utilisateurs devront se reconnecter. |
| Mot de passe PostgreSQL | `ALTER USER <user> WITH PASSWORD '<nouveau>';` puis mettre à jour `DATABASE_URL`. |
| `SUPABASE_ANON_KEY` / `SERVICE_ROLE_KEY` | Régénérer les clés API Supabase. |
| `SMTP_PASSWORD` | Régénérer le mot de passe du compte d'envoi. |
| `BUGSINK_DSN` / `NUXT_PUBLIC_N8N_CHAT_WEBHOOK` | Recréer le projet / changer l'URL du webhook (il était public et sans authentification). |

Générer un secret solide :

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 1.2 Vérifier les accès non autorisés

```sql
-- Comptes créés hors procédure (l'auto-provisioning est désormais supprimé,
-- mais les comptes créés avant la correction subsistent)
SELECT id, email, role, is_admin, is_active, created_at
FROM utilisateurs
ORDER BY created_at DESC;

-- Comptes sans mot de passe (ancienne backdoor « Payohada@123 »)
SELECT id, email, role FROM utilisateurs WHERE hashed_password IS NULL;

-- Les comptes de démonstration éventuels
SELECT id, email, role FROM utilisateurs WHERE email LIKE '%liugong%';
```

Désactiver ou supprimer tout compte non reconnu :

```sql
UPDATE utilisateurs SET is_active = false WHERE email = '<suspect>';
```

### 1.2.1 Reprendre la main sur un compte sans mot de passe

L'ancienne backdoor acceptait `Payohada@123` dès que `hashed_password` était
`NULL`. Ce n'est plus le cas : **ces comptes sont désormais inaccessibles et
doivent être repris explicitement.** Le cas est réel — la base actuelle contient
notamment un compte `cabinet` **administrateur** sans mot de passe, qui était
donc entièrement compromis.

**Symptôme** : `POST /api/v1/auth/login` répond `401` alors que le mot de passe
semble correct — c'était l'ancien mot de passe par défaut. La cause exacte est
désormais écrite dans les logs du serveur, par exemple :

```
WARNING app.routers.auth: Connexion refusée : le compte x@y.ci n'a aucun mot de
passe défini (ancien compte créé avec la backdoor « Payohada@123 »).
Définissez-en un : python set_password.py --email x@y.ci --password '<secret>'
```

**Diagnostic** (lecture seule, aucune modification) :

```bash
cd backend
python set_password.py --lister
```

**Reprise** — définir un mot de passe sans changer le rôle ni recréer le compte
(donc sans perdre l'historique rattaché) :

```bash
# Compte client ou salarié (8 caractères minimum)
python set_password.py --email <email> --password '<secret-solide>'

# Compte administrateur : 12 caractères minimum exigés
python set_password.py --email <email> --password '<secret-solide>' --promouvoir
```

`create_admin.py` reste disponible pour créer un administrateur **supplémentaire**
(et non pour reprendre un compte existant).

### 1.3 Purger l'historique Git

Le script `scripts/purge_git_secrets.sh` prépare la purge avec `git-filter-repo`.
Il est volontairement **non exécuté automatiquement** : réécrire l'historique
casse tous les clones existants et nécessite un `git push --force`.

```bash
./scripts/purge_git_secrets.sh            # simulation (dry-run)
./scripts/purge_git_secrets.sh --apply    # réécriture réelle + instructions de push
```

Après la purge : demander à tous les contributeurs de re-cloner le dépôt, puis
activer la protection de branche et l'analyse `gitleaks` (déjà câblée dans
`.github/workflows/ci.yml`).

## 2. Modèle d'authentification et d'autorisation

- **Jeton** : JWT HS256 signé avec `SUPABASE_JWT_SECRET`, durée 24 h.
- **Aucune création implicite de compte** : un `sub` inconnu est rejeté
  (`app/services/security.py`). C'était auparavant une voie d'escalade.
- **Mots de passe** : PBKDF2-SHA256, 100 000 itérations, comparaison en temps
  constant. Minimum 8 caractères, mix lettres/chiffres.
- **Aucun mot de passe partagé** : les comptes créés par le cabinet reçoivent un
  mot de passe aléatoire, retourné **une seule fois** dans
  `mot_de_passe_initial`, avec obligation de le changer
  (`must_change_password`).
- **Anti brute-force** : 10 tentatives / 5 minutes par IP et par compte
  (`app/services/rate_limit.py`).
- **Mot de passe oublié** : jeton aléatoire de 256 bits transmis par email,
  stocké **uniquement sous forme de condensat SHA-256**, à usage unique et valable
  30 minutes (`PASSWORD_RESET_EXPIRE_MINUTES`). La réponse est identique que
  l'adresse existe ou non (pas d'énumération), un échec d'envoi n'est pas révélé
  au client, une nouvelle demande invalide le lien précédent, et tout changement
  de mot de passe invalide les jetons en attente. Quotas dédiés : 5 demandes /
  15 min par compte, 20 / 15 min par IP, 20 / 15 min sur la consommation du jeton.

### Matrice des rôles

| Action | cabinet | client | salarié | admin |
|---|:--:|:--:|:--:|:--:|
| Voir les bulletins de son périmètre | ✅ | ✅ (son dossier) | ✅ (les siens) | ✅ |
| Calculer / recalculer un bulletin | ✅ | ❌ | ❌ | ✅ |
| Calculer la paie en lot | ✅ (son dossier) | ❌ | ❌ | ✅ |
| Valider / invalider / supprimer un bulletin | ✅ | ❌ | ❌ | ✅ |
| Créer un dossier, un compte client | ✅ | ❌ | ❌ | ✅ |
| Modifier les constantes / le plan de paie | ❌ | ❌ | ❌ | ✅ |
| Traiter une réclamation | ✅ (ses dossiers) | ❌ | ❌ | ✅ |
| Téléverser une pièce jointe | ✅ | ✅ (son dossier) | ✅ (la sienne) | ✅ |

Ces règles sont appliquées **côté API**. Le middleware Nuxt
(`frontend/app/middleware/auth.global.ts`) n'est qu'un confort d'interface.

### Règle d'intégrité : bulletins validés

Un bulletin au statut `valide` ne peut plus être recalculé. Pour corriger une
période clôturée, il faut d'abord l'**invalider** : cette opération restaure les
remboursements de prêts appliqués lors de la validation, ce qui rend le cycle
`invalider → recalculer → valider` idempotent.

## 3. Durcissement en place

| Sujet | Mesure |
|---|---|
| CORS | Origines explicites via `CORS_ORIGINS` (plus de `*` avec credentials). |
| Pièces jointes | Extensions en liste blanche, taille maximale (10 Mo), nom généré côté serveur, téléchargement via `GET /api/v1/salaries/documents/{fichier}` avec contrôle de portée. Le montage statique public `/uploads` a été supprimé. |
| Erreurs | Message générique côté client, trace complète côté serveur. |
| Journalisation | La chaîne `DATABASE_URL` n'est plus imprimée (identifiants masqués). |
| En-têtes HTTP | CSP de `nuxt-security` construite à partir des seules variables configurées. |
| Dépendances externes | Aucun DSN ni webhook codé en dur : la fonctionnalité est désactivée si la variable est absente. |

## 4. Points de vigilance restants

1. **Jeton en `localStorage`** (`frontend/app/composables/useSupabase.ts`) : une
   XSS permet de l'exfiltrer. Cible : cookie `httpOnly` + `SameSite=Strict` émis
   par le backend.
2. **`ssr: false`** : la SPA ne rend rien côté serveur ; tout le contrôle d'accès
   d'interface est client. L'API reste la seule autorité.
3. **Limiteur de débit en mémoire** : par instance. Un déploiement multi-instances
   nécessite un compteur partagé (Redis, déjà présent dans `coolify-compose.yaml`).
4. **Artefacts versionnés** : `paie.db`, `backend/test.db` et `backend/dist/`
   sont encore suivis par Git alors qu'ils sont désormais ignorés. Les retirer
   de l'index quand c'est possible :
   ```bash
   git rm -r --cached paie.db backend/test.db backend/dist
   ```
5. **Montants en `Float`** : à migrer vers `Numeric(14, 2)` pour éviter les
   dérives d'arrondi sur les cumuls annuels.
