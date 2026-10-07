#!/usr/bin/env python
"""Crée (ou promeut) un compte administrateur plateforme.

Le rôle administrateur donne accès à la gestion des référentiels globaux
(constantes de paie, plan de paie) et à tous les dossiers. Il n'est
volontairement pas attribuable via l'API publique.

Usage :
    python create_admin.py --email admin@moncabinet.ci --password 'MotDePasse!23' \
        [--prenom Ada] [--nom Lovelace] [--promouvoir]

Options :
    --promouvoir   Promeut un utilisateur existant au lieu d'en créer un.
"""
import argparse
import sys

from app.database import SessionLocal
from app.models.models import Utilisateur
from app.services.security import get_password_hash, validate_password_strength
from fastapi import HTTPException


def main() -> int:
    parser = argparse.ArgumentParser(description="Crée un compte administrateur PayOHADA.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--prenom", default="Admin")
    parser.add_argument("--nom", default="Plateforme")
    parser.add_argument(
        "--promouvoir",
        action="store_true",
        help="Promeut le compte existant au lieu d'échouer s'il existe déjà.",
    )
    args = parser.parse_args()

    email = args.email.strip().lower()

    try:
        validate_password_strength(args.password, minimum=12)
    except HTTPException as exc:
        print(f"Mot de passe refusé : {exc.detail}")
        return 2

    db = SessionLocal()
    try:
        user = db.query(Utilisateur).filter(Utilisateur.email == email).first()

        if user:
            if not args.promouvoir:
                print(
                    f"Un compte existe déjà pour {email}. "
                    "Relancez avec --promouvoir pour lui donner les droits d'administration."
                )
                return 1
            user.is_admin = True
            user.is_active = True
            user.must_change_password = False
            db.commit()
            print(f"Compte {email} promu administrateur.")
            return 0

        import uuid

        user = Utilisateur(
            email=email,
            nom=args.nom,
            prenom=args.prenom,
            hashed_password=get_password_hash(args.password),
            supabase_uid=f"local-admin-{uuid.uuid4()}",
            is_active=True,
            is_admin=True,
            must_change_password=False,
            role="cabinet",
        )
        db.add(user)
        db.commit()
        print(f"Compte administrateur créé : {email}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
