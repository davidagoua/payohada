#!/bin/sh
# Applique les migrations idempotentes avant de démarrer l'API.
# La table `imports` (et les colonnes ajoutées) doivent exister en production.
set -eu
echo "[payohada] Application des migrations de schéma..."
python apply_migrations.py
echo "[payohada] Démarrage de l'API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
