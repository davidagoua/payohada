#!/usr/bin/env python
"""Applique la section incrémentale de `schema.sql` à une base PostgreSQL.

`schema.sql` est la source de vérité du schéma. Sa première partie crée les
tables d'origine ; sa **section incrémentale**, à la fin du fichier, regroupe
toutes les évolutions ajoutées depuis (colonnes, tables, index). C'est elle que
ce script applique.

La section est **idempotente** : elle n'emploie que des `ADD COLUMN IF NOT
EXISTS`, `CREATE TABLE IF NOT EXISTS` et `CREATE INDEX IF NOT EXISTS`. La
relancer ne produit donc aucun effet de bord, et le script le vérifie.

Usage
-----
    python apply_migrations.py --dry-run          # montre l'état, n'écrit rien
    python apply_migrations.py                     # applique sur DATABASE_URL
    python apply_migrations.py --url postgresql://…  # applique sur une autre base

La base visée est celle de `DATABASE_URL` (fichier `.env` ou environnement)
lorsque `--url` n'est pas fourni.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Iterable

# Les valeurs sensibles ne sont pas nécessaires ici : on lit l'environnement
# sans passer par l'objet Settings de l'application, afin que ce script reste
# utilisable même si la configuration applicative est incomplète.
import os

RACINE = pathlib.Path(__file__).resolve().parent
CHEMIN_SCHEMA = RACINE / "schema.sql"

#: Tables et colonnes que l'application attend et qui proviennent de la section
#: incrémentale. Sert à vérifier le résultat après application.
ATTENDUS_TABLES = ("avantages_en_nature", "password_reset_tokens")
ATTENDUS_COLONNES = (
    ("utilisateurs", "must_change_password"),
    ("contrats", "smhc_mensuel"),
    ("departs_salaries", "motif_fin_contrat"),
    ("departs_salaries", "sous_motif_fin_cdd"),
    ("departs_salaries", "conditions_retraite_remplies"),
    ("soldes_tout_compte", "indemnite_fin_cdd"),
    ("soldes_tout_compte", "indemnite_deces"),
    ("soldes_tout_compte", "frais_funeraires"),
    ("soldes_tout_compte", "gratification"),
    ("soldes_tout_compte", "detail_calcul"),
)


def extraire_section_incrementale(contenu: str) -> str:
    """Retourne la section incrémentale, bandeau de titre compris."""
    marqueur = contenu.find("-- MIGRATION INCREMENTALE")
    if marqueur == -1:
        raise SystemExit(
            "Section incrémentale introuvable dans schema.sql : "
            "le fichier a-t-il été modifié ?"
        )
    debut = contenu.rindex("-- ===", 0, marqueur)
    return contenu[debut:]


def lire_url(depuis_option: str | None) -> str:
    if depuis_option:
        return depuis_option
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    env = RACINE / ".env"
    if env.exists():
        for ligne in env.read_text(encoding="utf-8").splitlines():
            if ligne.startswith("DATABASE_URL="):
                return ligne.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(
        "Aucune base indiquée. Utilisez --url ou définissez DATABASE_URL."
    )


def masquer(url: str) -> str:
    """Représentation affichable d'une URL de connexion, sans le mot de passe."""
    from urllib.parse import urlparse

    u = urlparse(url)
    hote = u.hostname or ""
    if u.port:
        hote = f"{hote}:{u.port}"
    return f"{u.scheme}://{u.username or ''}@{hote}/{u.path.lstrip('/')}"


def etat(moteur) -> tuple[set[str], dict[str, set[str]]]:
    """Tables présentes et colonnes par table."""
    from sqlalchemy import text

    with moteur.connect() as conn:
        tables = {
            r[0] for r in conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_type='BASE TABLE'"
            ))
        }
        colonnes: dict[str, set[str]] = {}
        for table in tables:
            colonnes[table] = {
                r[0] for r in conn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name=:t"
                ), {"t": table})
            }
    return tables, colonnes


def manquants(tables: set[str], colonnes: dict[str, set[str]]) -> tuple[list[str], list[str]]:
    tables_absentes = [t for t in ATTENDUS_TABLES if t not in tables]
    colonnes_absentes = [
        f"{t}.{c}" for t, c in ATTENDUS_COLONNES
        if t in tables and c not in colonnes.get(t, set())
    ]
    return tables_absentes, colonnes_absentes


def afficher_etat(titre: str, tables: set[str], colonnes: dict[str, set[str]]) -> bool:
    tables_absentes, colonnes_absentes = manquants(tables, colonnes)
    print(f"\n{titre}")
    print(f"  Tables au total : {len(tables)}")
    if not tables_absentes and not colonnes_absentes:
        print("  ✅ toutes les tables et colonnes attendues sont présentes")
        return True
    for t in tables_absentes:
        print(f"  ❌ table absente    : {t}")
    for c in colonnes_absentes:
        print(f"  ❌ colonne absente  : {c}")
    return False


def main(argv: Iterable[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(
        description="Applique la section incrémentale de schema.sql."
    )
    analyseur.add_argument("--url", help="URL de connexion (sinon DATABASE_URL).")
    analyseur.add_argument(
        "--dry-run", action="store_true",
        help="Affiche l'état et ce qui serait appliqué, sans rien modifier.",
    )
    arguments = analyseur.parse_args(argv)

    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        print("SQLAlchemy est requis (pip install -r requirements.txt).", file=sys.stderr)
        return 1

    url = lire_url(arguments.url)
    contenu = CHEMIN_SCHEMA.read_text(encoding="utf-8")
    section = extraire_section_incrementale(contenu)

    print(f"Base visée  : {masquer(url)}")
    print(f"Schéma      : {CHEMIN_SCHEMA}")
    print(f"Section     : {len(section.splitlines())} lignes")

    moteur = create_engine(url)
    try:
        tables, colonnes = etat(moteur)
    except Exception as erreur:
        print(f"\n❌ Connexion impossible : {type(erreur).__name__} — {erreur}", file=sys.stderr)
        return 1

    deja_a_jour = afficher_etat("État actuel", tables, colonnes)

    if arguments.dry_run:
        print("\nMode --dry-run : aucune modification appliquée.")
        return 0

    if deja_a_jour:
        print("\nRien à faire : la base est déjà à jour.")
        print("La section reste rejouable sans risque (elle est idempotente).")
        return 0

    print("\nApplication de la section incrémentale (transaction)…")
    try:
        with moteur.begin() as conn:
            conn.execute(text(section))
    except Exception as erreur:
        print(f"\n❌ Échec : {type(erreur).__name__} — {erreur}", file=sys.stderr)
        print("La transaction a été annulée : la base est inchangée.", file=sys.stderr)
        return 1

    tables, colonnes = etat(moteur)
    ok = afficher_etat("Après application", tables, colonnes)

    if ok:
        print("\n✅ Migration appliquée. La base correspond au schéma attendu.")
        return 0
    print("\n⚠️  Il reste des éléments manquants : vérifiez schema.sql.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
