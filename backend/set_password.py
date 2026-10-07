#!/usr/bin/env python
"""Définit (ou réinitialise) le mot de passe d'un compte existant.

Outil de reprise destiné aux comptes créés avant la fermeture de la backdoor
« Payohada@123 » : ces comptes ont `hashed_password` à NULL et ne peuvent plus
se connecter. Il permet de leur redonner un accès sans changer leur rôle ni
recréer le compte (donc sans perdre l'historique qui y est rattaché).

Usage :
    python set_password.py --email utilisateur@exemple.ci --password '<secret>'
    python set_password.py --email admin@exemple.ci --password '<secret>' --promouvoir
    python set_password.py --lister

Options :
    --promouvoir   Accorde en plus les droits d'administration (mot de passe
                   de 12 caractères minimum exigé dans ce cas).
    --activer      Réactive un compte désactivé.
    --lister       Affiche les comptes et indique lesquels n'ont pas de mot de
                   passe (aucune modification).
"""
import argparse
import sys

from app.database import SessionLocal
from app.models.models import Utilisateur
from app.services.security import get_password_hash, validate_password_strength
from fastapi import HTTPException


def _lister(db) -> int:
    comptes = db.query(Utilisateur).order_by(Utilisateur.id).all()
    print(f"{len(comptes)} compte(s) :")
    sans_mdp = 0
    for u in comptes:
        vide = u.hashed_password is None
        if vide:
            sans_mdp += 1
        print(
            f"  id={u.id:<4} {u.email:<44} rôle={u.role or '?':<8}"
            f" admin={'oui' if u.is_admin else 'non':<4}"
            f" actif={'oui' if u.is_active else 'non':<4}"
            f" mot_de_passe={'ABSENT' if vide else 'défini'}"
        )
    if sans_mdp:
        print(
            f"\n⚠️  {sans_mdp} compte(s) sans mot de passe : connexion impossible "
            "tant qu'aucun mot de passe n'est défini."
        )
        print("    Exemple : python set_password.py --email <email> --password '<secret>'")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Définit le mot de passe d'un compte PayOHADA existant."
    )
    parser.add_argument("--email")
    parser.add_argument("--password")
    parser.add_argument("--promouvoir", action="store_true",
                        help="Accorde aussi les droits d'administration.")
    parser.add_argument("--activer", action="store_true",
                        help="Réactive le compte s'il est désactivé.")
    parser.add_argument("--doit-changer", action="store_true",
                        help="Impose le changement de mot de passe à la prochaine connexion.")
    parser.add_argument("--lister", action="store_true",
                        help="Liste les comptes sans rien modifier.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.lister:
            return _lister(db)

        if not args.email or not args.password:
            parser.error("--email et --password sont requis (ou utilisez --lister).")

        from sqlalchemy import func

        email = args.email.strip().lower()
        user = (
            db.query(Utilisateur)
            .filter(func.lower(Utilisateur.email) == email)
            .first()
        )
        if not user:
            print(f"Aucun compte ne correspond à {email}.")
            print("Utilisez --lister pour voir les comptes existants.")
            return 1

        minimum = 12 if (args.promouvoir or user.is_admin) else 8
        try:
            validate_password_strength(args.password, minimum=minimum)
        except HTTPException as exc:
            print(f"Mot de passe refusé : {exc.detail}")
            return 2

        user.hashed_password = get_password_hash(args.password)
        user.must_change_password = bool(args.doit_changer)
        if args.promouvoir:
            user.is_admin = True
        if args.activer:
            user.is_active = True
        db.commit()

        print(f"Mot de passe défini pour {user.email}.")
        if args.promouvoir:
            print("  → droits d'administration accordés.")
        if args.activer:
            print("  → compte réactivé.")
        if args.doit_changer:
            print("  → changement imposé à la prochaine connexion.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
