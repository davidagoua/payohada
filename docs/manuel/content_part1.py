"""Partie I du manuel : introduction et premiers pas."""
from __future__ import annotations

from pathlib import Path

from docx import Document

import manuel_kit as k

IMAGES = Path(__file__).resolve().parent.parent / "captures" / "manuel"


def render(doc: Document) -> None:
    k.add_part_divider(
        doc,
        "I",
        "Démarrer avec payohada",
        "Prendre en main la plateforme : se connecter, créer un espace cabinet, "
        "retrouver ses marques et adopter les bons réflexes de sécurité.",
        [
            "**1. Introduction** — à qui s'adresse le manuel et comment le lire.",
            "**2. Premiers pas** — connexion, inscription, mot de passe et navigation.",
        ],
    )

    # ── Chapitre 1 ─────────────────────────────────────────────────────────
    k.add_heading(doc, "1. Introduction", level=1, page_break=True)
    k.add_lead(
        doc,
        "payohada est une plateforme de gestion de la paie conforme à l'environnement "
        "OHADA. Elle relie un cabinet comptable, les entreprises clientes et leurs "
        "salariés autour d'un registre de paie unique, traçable et sécurisé.",
    )

    k.add_heading(doc, "1.1 Objet du manuel", level=2)
    k.add_para(
        doc,
        "Ce manuel décrit les tâches courantes de chaque utilisateur, écran par écran. "
        "Il répond à trois questions : **où aller**, **quoi faire** et **ce qui se passe "
        "ensuite**. Il ne remplace pas les règles légales ou conventionnelles applicables "
        "à chaque entreprise : en cas de doute, rapprochez-vous de votre responsable paie "
        "ou de votre conseil.",
    )

    k.add_heading(doc, "1.2 À qui s'adresse ce manuel", level=2)
    k.add_table(
        doc,
        ["Profil", "Ce que vous faites dans payohada", "Où lire"],
        [
            ["**Propriétaire du cabinet**",
             "Pilote le cabinet, crée les dossiers, affecte les gestionnaires et administre les comptes.",
             "Chapitres 2 et 3 (sections 3.1 à 3.15)"],
            ["**Administrateur du cabinet**",
             "Même périmètre que le propriétaire, sans pouvoir modifier le propriétaire.",
             "Chapitres 2 et 3"],
            ["**Gestionnaire de paie**",
             "Gère la paie des sociétés qui lui sont affectées : salariés, contrats, calculs, bulletins.",
             "Chapitres 2 et 3 (sections 3.3 à 3.14)"],
            ["**Entreprise cliente**",
             "Saisit les variables du mois, transmet au cabinet, consulte les bulletins et valide les demandes.",
             "Chapitres 2 et 4"],
            ["**Salarié**",
             "Consulte ses bulletins, demande des congés ou un acompte et dépose une réclamation.",
             "Chapitres 2 et 5"],
            ["**Administrateur plateforme**",
             "Maintient les référentiels globaux et supervise les comptes de tous les cabinets.",
             "Chapitres 2, 6 et 7"],
        ],
        widths=[3.8, 8.8, 4.4],
        font_size=8.8,
    )

    k.add_heading(doc, "1.3 Les quatre espaces de travail", level=2)
    k.add_para(
        doc,
        "L'interface s'adapte automatiquement au rôle du compte connecté. Un même "
        "utilisateur ne voit jamais les menus d'un autre espace.",
    )
    k.add_table(
        doc,
        ["Espace", "Compte", "Adresse d'accueil", "Missions principales"],
        [
            ["Cabinet", "cabinet ou gestionnaire_paie", "/dossiers",
             "Créer les dossiers, établissements, salariés et contrats ; calculer et valider la paie ; éditer les états."],
            ["Entreprise", "client", "/client",
             "Saisir les variables du mois, transmettre la grille, consulter les bulletins, valider congés et acomptes."],
            ["Salarié", "salarie", "/salaries/bulletins",
             "Consulter ses bulletins, suivre ses congés, demander un acompte, déposer une réclamation."],
            ["Plateforme", "Compte is_admin", "/admin",
             "Gérer les constantes de paie, le plan comptable et les comptes de tous les cabinets."],
        ],
        widths=[2.6, 3.6, 4.2, 6.6],
        font_size=8.8,
    )
    k.add_callout(
        doc,
        "info",
        "À savoir",
        "Un compte est rattaché à un seul espace. Si vous devez intervenir dans "
        "plusieurs espaces, utilisez des comptes distincts : ne partagez jamais "
        "vos identifiants.",
    )

    k.add_heading(doc, "1.4 Parcours recommandé", level=2)
    k.add_table(
        doc,
        ["Votre rôle", "Lisez en priorité", "Pour aller plus loin"],
        [
            ["Propriétaire / administrateur du cabinet", "2. Premiers pas, 3.1 à 3.6, 3.15",
             "3.8 à 3.14, 7. Sécurité, 9. Matrice des rôles"],
            ["Gestionnaire de paie", "2. Premiers pas, 3.3 à 3.14", "3.15 (lecture), 8. FAQ"],
            ["Entreprise cliente", "2. Premiers pas, 4. Guide Entreprise", "5. Guide Salarié (pour comprendre leurs demandes)"],
            ["Salarié", "2. Premiers pas, 5. Guide Salarié", "10. Glossaire"],
            ["Administrateur plateforme", "2. Premiers pas, 6. Guide Administrateur", "3.15 (constantes en lecture), 7. Sécurité"],
        ],
        widths=[4.6, 7.0, 5.4],
        font_size=8.8,
    )

    k.add_heading(doc, "1.5 Conventions de lecture", level=2)
    k.add_table(
        doc,
        ["Repère", "Signification"],
        [
            ["**Gras**", "Nom d'un bouton, d'un menu ou d'un champ à utiliser tel quel."],
            ["/dossiers", "Chemin d'une page dans l'application (adresse après le nom de domaine)."],
            ["Encadré « Astuce »", "Conseil pratique pour gagner du temps."],
            ["Encadré « À savoir »", "Règle de fonctionnement ou point de vigilance."],
            ["Encadré « Attention »", "Action à éviter ou conséquence irréversible."],
            ["Capture d'écran", "Exemple d'écran ; les données affichées sont fictives."],
        ],
        widths=[5.0, 12.0],
        font_size=8.8,
        first_col_bold=False,
    )

    k.add_heading(doc, "1.6 Le vocabulaire de la paie", level=2)
    k.add_para(
        doc,
        "Les termes techniques utilisés dans ce manuel sont définis dans le "
        "**glossaire** (chapitre 10). Les plus fréquents sont : **bulletin de paie**, "
        "**brut**, **net à payer**, **ITS**, **CNPS**, **CMU**, **période de paie** et "
        "**édition**.",
    )

    # ── Chapitre 2 ─────────────────────────────────────────────────────────
    k.add_heading(doc, "2. Premiers pas", level=1, page_break=True)
    k.add_lead(
        doc,
        "Tout commence par une connexion. Ce chapitre couvre la création d'un espace "
        "cabinet, la récupération d'un mot de passe et les repères communs à tous les "
        "espaces.",
    )

    k.add_heading(doc, "2.1 Se connecter", level=2)
    k.add_figure(
        doc,
        IMAGES / "01-connexion.png",
        "Figure 1 — Écran de connexion à payohada.",
    )
    k.add_steps(doc, [
        "Ouvrez l'adresse de la plateforme communiquée par votre administrateur.",
        "Saisissez votre **adresse email** professionnelle.",
        "Saisissez votre **mot de passe**, puis cliquez sur **Se connecter**.",
        "Vous êtes redirigé vers l'accueil correspondant à votre rôle : dossier pour "
        "le cabinet, tableau de bord pour l'entreprise, bulletins pour le salarié.",
    ])
    k.add_callout(
        doc,
        "warning",
        "Attention",
        "Ne partagez jamais votre mot de passe et ne restez pas connecté sur un poste "
        "partagé. Utilisez **Se déconnecter** en fin de session.",
    )

    k.add_heading(doc, "2.2 Créer un espace cabinet", level=2)
    k.add_para(
        doc,
        "L'inscription est réservée au cabinet. Elle se fait en deux étapes : les "
        "informations du cabinet, puis le compte du **gestionnaire référent** — le futur "
        "propriétaire du cabinet.",
    )
    k.add_steps(doc, [
        "Depuis l'écran de connexion, cliquez sur **Inscrivez votre cabinet**.",
        "Renseignez les informations du cabinet : nom, téléphone, ville, adresse email.",
        "Renseignez le gestionnaire référent : prénom, nom, email et mot de passe.",
        "Validez : votre espace est créé et vous êtes connecté en tant que propriétaire.",
    ])
    k.add_table(
        doc,
        ["Champ", "Rôle", "Conseil"],
        [
            ["Nom du cabinet", "Affiché dans l'en-tête et sur les documents", "Utilisez la raison sociale exacte."],
            ["Email du cabinet", "Contact et identifiant de connexion", "Utilisez une boîte professionnelle partagée avec l'équipe paie."],
            ["Mot de passe", "Sécurise le compte", "8 caractères minimum, avec lettres et chiffres."],
        ],
        widths=[4.2, 7.6, 5.2],
        font_size=8.8,
    )
    k.add_callout(
        doc,
        "info",
        "À savoir",
        "Le premier compte est le **propriétaire** du cabinet. Il ne peut être ni "
        "rétrogradé ni désactivé. Il peut ensuite inviter des collaborateurs depuis "
        "**Administration > Utilisateurs** (voir 3.15).",
    )

    k.add_heading(doc, "2.3 Mot de passe oublié", level=2)
    k.add_steps(doc, [
        "Sur l'écran de connexion, cliquez sur **Mot de passe oublié ?**.",
        "Saisissez l'adresse email du compte, puis validez.",
        "Consultez votre boîte email : un lien sécurisé vous permet de définir un nouveau mot de passe.",
        "Revenez à la connexion et identifiez-vous avec le nouveau mot de passe.",
    ])
    k.add_callout(
        doc,
        "info",
        "À savoir",
        "Si le message de réinitialisation n'arrive pas, vérifiez les indésirables et "
        "l'orthographe de l'adresse. Contactez ensuite votre administrateur : "
        "l'envoi d'emails dépend de la configuration du serveur.",
    )

    k.add_heading(doc, "2.4 Première connexion et changement de mot de passe", level=2)
    k.add_para(
        doc,
        "Lorsqu'un compte est créé par un administrateur, un **mot de passe temporaire** "
        "est envoyé par email (ou transmis par un autre canal si l'envoi automatique "
        "échoue). À la première connexion, la plateforme vous invite à le remplacer.",
    )
    k.add_steps(doc, [
        "Connectez-vous avec le mot de passe temporaire reçu.",
        "Dans la fenêtre **Changer le mot de passe**, saisissez le mot de passe actuel, "
        "puis le nouveau deux fois.",
        "Validez : le nouveau mot de passe est actif immédiatement.",
    ])
    k.add_para(
        doc,
        "Vous pouvez aussi changer votre mot de passe à tout moment depuis le menu de "
        "votre profil (icône en haut à droite) ou le bouton **Modifier mon mot de passe** "
        "de l'espace salarié.",
    )

    k.add_heading(doc, "2.5 Se repérer dans l'interface", level=2)
    k.add_para(
        doc,
        "Tous les espaces partagent la même structure : une en-tête bleu nuit, une barre "
        "d'onglets et une zone de contenu.",
    )
    k.add_table(
        doc,
        ["Zone", "Contenu", "À quoi elle sert"],
        [
            ["En-tête (haut)", "Logo, badge de l'espace, fil d'Ariane, nom de la société, profil et déconnexion",
             "Savoir où vous êtes et changer de contexte."],
            ["Barre d'onglets", "Menus propres à votre rôle",
             "Naviguer entre les fonctions principales."],
            ["Zone de contenu", "Listes, formulaires, tableaux de bord",
             "Travailler au quotidien."],
            ["Notifications", "Messages en bas à droite (succès, erreur, avertissement)",
             "Confirmer une action ou signaler un problème."],
            ["Profil", "Initiales en haut à droite",
             "Changer de mot de passe ou se déconnecter."],
        ],
        widths=[3.2, 7.8, 6.0],
        font_size=8.8,
    )

    k.add_heading(doc, "2.6 Navigateur et sécurité de session", level=2)
    k.add_bullets(doc, [
        "Utilisez un navigateur récent (Chrome, Edge, Firefox ou Safari) et maintenez-le à jour.",
        "Autorisez les fenêtres surgissantes de la plateforme si vous téléchargez des bulletins ou des états.",
        "Ne dupliquez pas un onglet pour changer d'utilisateur : déconnectez-vous puis reconnectez-vous.",
        "Fermez la session avant de quitter votre poste, surtout sur un ordinateur partagé.",
    ])

    k.add_heading(doc, "2.7 En cas de problème de connexion", level=2)
    k.add_table(
        doc,
        ["Symptôme", "Cause probable", "Que faire"],
        [
            ["« Identifiants incorrects »", "Email ou mot de passe erroné",
             "Vérifiez l'orthographe, puis utilisez **Mot de passe oublié ?**."],
            ["Compte désactivé", "L'administrateur a suspendu l'accès",
             "Contactez le propriétaire du cabinet ou l'administrateur plateforme."],
            ["Page blanche ou erreur serveur", "Connexion interrompue",
             "Rechargez la page, vérifiez votre réseau, puis reconnectez-vous."],
            ["Aucun email de réinitialisation", "Envoi SMTP indisponible ou adresse inconnue",
             "Vérifiez les indésirables ; demandez à l'administrateur de réinitialiser le compte."],
        ],
        widths=[4.6, 5.8, 6.6],
        font_size=8.8,
    )
