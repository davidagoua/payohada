#!/usr/bin/env bash
#
# Purge des secrets committés dans l'historique Git.
#
# ATTENTION : la réécriture d'historique est irréversible et casse tous les
# clones existants. Elle doit être précédée de la ROTATION des secrets
# (voir SECURITY.md) : purger l'historique ne protège pas des secrets déjà
# copiés.
#
# Usage :
#   ./scripts/purge_git_secrets.sh           # simulation (dry-run, aucune écriture)
#   ./scripts/purge_git_secrets.sh --apply   # réécriture réelle
#
set -euo pipefail

APPLY=0
if [[ "${1:-}" == "--apply" ]]; then
  APPLY=1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Chemins de fichiers sensibles présents dans l'historique.
PATHS_FILE="$(mktemp)"
trap 'rm -f "$PATHS_FILE"' EXIT

cat > "$PATHS_FILE" <<'EOF'
.env
backend/.env
frontend/.env
supabase/.env
EOF

echo "==> Dépôt : $REPO_ROOT"
echo "==> Fichiers ciblés :"
sed 's/^/    - /' "$PATHS_FILE"
echo

if ! command -v git-filter-repo >/dev/null 2>&1; then
  cat <<'MSG'
git-filter-repo est requis et absent du système.

Installation :
    pip install git-filter-repo
    # ou : brew install git-filter-repo

Alternative sans dépendance (moins performante) :
    git filter-branch --force --index-filter \
      'git rm --cached --ignore-unmatch .env backend/.env frontend/.env' \
      --prune-empty --tag-name-filter cat -- --all
MSG
  exit 1
fi

if [[ "$APPLY" -eq 0 ]]; then
  cat <<MSG
--- MODE SIMULATION ---
Aucune modification n'a été appliquée.

Pour lancer réellement la purge :
    $0 --apply

Étapes qui seront exécutées :
  1. git filter-repo --invert-paths --path <chaque fichier>
  2. git reflog expire --expire=now --all
  3. git gc --prune=now --aggressive
  4. affichage des instructions de push forcé
MSG
  exit 0
fi

echo "==> Sauvegarde de l'état actuel dans refs/original (git filter-repo crée un backup automatique)"
echo "==> Réécriture de l'historique..."

ARGS=()
while IFS= read -r p; do
  [[ -z "$p" ]] && continue
  ARGS+=(--path "$p")
done < "$PATHS_FILE"

git filter-repo --force --invert-paths "${ARGS[@]}"

echo "==> Nettoyage des objets inaccessibles..."
git reflog expire --expire=now --all || true
git gc --prune=now --aggressive || true

cat <<'MSG'

==> Historique réécrit.

Vérification :
    git log --all --oneline -- .env backend/.env frontend/.env   # doit être vide

Publication (DESTRUCTIF) :
    git remote add origin <url>            # filter-repo retire l'origine
    git push --force --all
    git push --force --tags

Ensuite, impérativement :
  - prévenir tous les contributeurs de re-cloner le dépôt ;
  - supprimer les forks et les caches GitHub si nécessaire ;
  - considérer les anciens secrets comme définitivement compromis.
MSG
