"""Partie III du manuel : sécurité, références et annexes."""
from __future__ import annotations

from docx import Document

import manuel_kit as k


def render(doc: Document) -> None:
    k.add_part_divider(
        doc,
        "III",
        "Sécurité et références",
        "Adopter les bons réflexes, retrouver une réponse rapide et disposer des "
        "tableaux de référence au quotidien.",
        [
            "**6. Sécurité et confidentialité** — comptes, données et bonnes pratiques.",
            "**7. Questions fréquentes** — réponses aux situations courantes.",
            "**8. Matrice des rôles** — qui peut faire quoi, en un tableau.",
            "**9. Glossaire** — le vocabulaire de la paie.",
            "**10. Annexes** — calendrier type, checklist et statuts.",
        ],
    )

    # ── Chapitre 7 ─────────────────────────────────────────────────────────
    k.add_heading(doc, "6. Sécurité et confidentialité", level=1, page_break=True)
    k.add_lead(
        doc,
        "La paie manipule des données personnelles et financières sensibles : identité, "
        "situation familiale, numéro de sécurité sociale, IBAN, rémunérations. Leur "
        "protection repose sur des règles simples, appliquées par tous.",
    )

    k.add_heading(doc, "6.1 Comptes et mots de passe", level=2)
    k.add_bullets(doc, [
        "Un compte nominatif par utilisateur : jamais de compte partagé ni de compte générique.",
        "Mot de passe d'au moins **8 caractères**, mélangeant lettres et chiffres ; évitez les mots courants.",
        "Ne communiquez jamais un mot de passe par email ou messagerie : utilisez le canal prévu par votre organisation.",
        "Changez votre mot de passe dès que vous suspectez une compromission.",
        "L'administrateur peut désactiver un compte immédiatement en cas de départ ou d'incident.",
    ])

    k.add_heading(doc, "6.2 Rôles et moindre privilège", level=2)
    k.add_para(
        doc,
        "Chaque rôle ne donne accès qu'à ce qui lui est nécessaire. Attribuez le rôle le "
        "plus restreint possible et vérifiez les affectations lors des arrivées, départs "
        "et changements de fonction.",
    )
    k.add_table(
        doc,
        ["Rôle", "À attribuer à", "À éviter"],
        [
            ["**Propriétaire du cabinet**", "Le responsable du cabinet", "Un compte partagé par l'équipe."],
            ["**Administrateur du cabinet**", "Un associé ou responsable de production", "Un stagiaire ou un prestataire ponctuel."],
            ["**Gestionnaire de paie**", "Un gestionnaire paie, sur ses sociétés", "Un accès à toutes les sociétés sans nécessité."],
            ["**Entreprise cliente**", "La direction ou le RH de l'entreprise", "Un compte générique sans responsable identifié."],
            ["**Salarié**", "Chaque salarié, sur sa fiche", "Un compte pour plusieurs salariés."],
        ],
        widths=[4.6, 6.4, 6.0],
        font_size=8.8,
    )

    k.add_heading(doc, "6.3 Données personnelles et confidentielles", level=2)
    k.add_bullets(doc, [
        "Ne consultez que les dossiers et salariés nécessaires à votre mission.",
        "Ne communiquez pas les bulletins à un tiers non autorisé (hors obligations légales).",
        "Les exports (PDF, Excel, CSV) contiennent des données personnelles : stockez-les dans un espace sécurisé et supprimez les copies inutiles.",
        "Ne diffusez pas de captures d'écran contenant des noms, IBAN ou montants sur des canaux non maîtrisés.",
        "Respectez la durée de conservation définie par votre organisation.",
    ])

    k.add_heading(doc, "6.4 Poste de travail et session", level=2)
    k.add_bullets(doc, [
        "Verrouillez votre poste dès que vous vous absentez.",
        "Déconnectez-vous explicitement en fin de journée, surtout sur un poste partagé.",
        "N'installez pas d'extension de navigateur non validée sur le poste utilisé pour la paie.",
        "Privilégiez un réseau de confiance ; évitez les Wi-Fi publics pour manipuler des bulletins.",
    ])

    k.add_heading(doc, "6.5 Pièces jointes et téléchargements", level=2)
    k.add_bullets(doc, [
        "Les pièces jointes sont contrôlées par la plateforme : extensions autorisées et taille limitée.",
        "N'ouvrez que les documents attendus ; en cas de doute, vérifiez l'expéditeur.",
        "Les téléchargements de bulletins et d'états peuvent être bloqués par le navigateur : autorisez les fenêtres surgissantes pour la plateforme.",
        "Supprimez les fichiers téléchargés qui ne sont plus utiles.",
    ])

    k.add_heading(doc, "6.6 Incident ou suspicion de compromission", level=2)
    k.add_steps(doc, [
        "Changez immédiatement votre mot de passe.",
        "Signalez l'incident à votre administrateur (cabinet) ou au support payohada.",
        "Précisez la date, l'action constatée et, si possible, l'écran ou le message affiché.",
        "N'effacez pas les traces : ne supprimez pas les emails ni les fichiers concernés avant instruction.",
    ])
    k.add_callout(
        doc,
        "danger",
        "Attention",
        "Aucun agent payohada ne vous demandera votre mot de passe par téléphone ou "
        "par email. Toute demande de ce type doit être considérée comme suspecte.",
    )

    # ── Chapitre 8 ─────────────────────────────────────────────────────────
    k.add_heading(doc, "7. Questions fréquentes", level=1, page_break=True)
    k.add_lead(
        doc,
        "Les réponses ci-dessous couvrent les situations les plus fréquentes. Si le "
        "problème persiste, contactez votre administrateur en précisant l'écran, la "
        "période et le message affiché.",
    )

    faq = [
        ("Je ne vois pas le menu Administration.",
         "Le menu n'est visible que pour le propriétaire et les administrateurs du cabinet. "
         "Un gestionnaire de paie ne le voit pas. "
         "Si vous êtes propriétaire et ne le voyez pas, rechargez la page ou vérifiez que "
         "vous êtes bien connecté avec le bon compte."),
        ("Les constantes et le plan de paie sont en lecture seule.",
         "C'est le fonctionnement prévu : le cabinet peut consulter les référentiels "
         "globaux, mais leur modification est réservée au support payohada. "
         "Contactez le support si une valeur doit évoluer."),
        ("Un salarié n'apparaît pas dans la grille de variables.",
         "Vérifiez qu'il a une fiche salarié active dans l'établissement et un contrat "
         "actif sur la période. Un salarié sans contrat n'est pas proposé à la saisie."),
        ("Le calcul de paie ne produit aucun bulletin.",
         "Contrôlez la période, le statut des contrats et l'existence d'au moins un "
         "salarié rattaché à l'établissement. Les contrats doivent être actifs sur le "
         "mois calculé."),
        ("Un bulletin validé contient une erreur.",
         "Un bulletin validé ne peut pas être recalculé directement. Le cabinet doit "
         "l'invalider, corriger la cause (variable, contrat, constante), recalculer puis "
         "valider à nouveau. Signalez l'écart au cabinet si vous êtes l'entreprise."),
        ("Pourquoi le net à payer a-t-il changé entre deux consultations ?",
         "Le bulletin a probablement été recalculé avant validation, ou des variables "
         "ont été corrigées. Un bulletin validé est définitif ; les montants affichés "
         "peuvent évoluer tant que la période n'est pas validée."),
        ("Comment retrouver un bulletin ancien ?",
         "Utilisez le sélecteur de période dans **Bulletins de Paie** (entreprise) ou "
         "**Mes Bulletins** (salarié). Les périodes antérieures restent consultables."),
        ("Le téléchargement d'un PDF ou d'un Excel ne démarre pas.",
         "Autorisez les fenêtres surgissantes et les téléchargements pour la plateforme, "
         "puis réessayez. Vérifiez aussi que le navigateur n'a pas bloqué le fichier."),
        ("Je n'ai pas reçu l'email contenant mes identifiants.",
         "Vérifiez les indésirables et l'adresse saisie. Si l'envoi automatique est "
         "indisponible, l'administrateur peut vous transmettre le mot de passe "
         "temporaire par un autre canal ; changez-le à la première connexion."),
        ("Comment créer une entreprise cliente ?",
         "Le cabinet crée un **dossier** (Entreprises > Nouveau Dossier), puis un "
         "**établissement**, puis les salariés et les contrats. L'entreprise reçoit un "
         "accès depuis l'onglet **Accès Client** du dossier."),
        ("Puis-je utiliser payohada sur téléphone ou tablette ?",
         "L'interface est optimisée pour ordinateur. Sur mobile, certaines grilles et "
         "tableaux restent lisibles mais l'expérience est limitée ; privilégiez un "
         "ordinateur pour la saisie et la validation."),
        ("L'import signale des lignes en erreur : que faire ?",
         "Téléchargez le rapport, corrigez les lignes concernées dans le fichier source "
         "en suivant le numéro de ligne et le message, puis redéposez le fichier. "
         "L'analyse ne modifie rien : vous pouvez itérer autant que nécessaire. Si des "
         "erreurs subsistent, le bouton **Importer les lignes valides** permet de ne "
         "charger que les lignes correctes."),
        ("Puis-je réimporter le même fichier ?",
         "Oui. L'import est idempotent : le même code établissement, le même matricule "
         "ou le même numéro de contrat met à jour l'enregistrement existant au lieu de "
         "créer un doublon. Vérifiez toutefois le rapport avant d'exécuter."),
        ("L'import reprend-il les cumuls de paie et les soldes de congés ?",
         "Oui pour les cumuls de paie : choisissez le type **Cumuls de reprise** et "
         "chargez le brut, les cotisations, l'ITS, les congés et les heures repris de "
         "l'ancien logiciel. Les soldes de congés d'ouverture, prêts et absences "
         "antérieurs ne sont pas encore couverts : à traiter séparément."),
        ("Combien de lignes puis-je importer ?",
         "Le fichier est limité à 25 Mo et l'exécution est synchrone : l'assistant est "
         "adapté à quelques milliers de lignes. Pour des volumes plus importants ou "
         "récurrents, découpez le fichier par établissement ou utilisez l'API/ETL."),
    ]
    for question, answer in faq:
        k.add_heading(doc, question, level=3)
        k.add_para(doc, answer)

    # ── Chapitre 9 ─────────────────────────────────────────────────────────
    k.add_heading(doc, "8. Matrice des rôles", level=1, page_break=True)
    k.add_lead(
        doc,
        "Ce tableau récapitule les droits par action. Il reflète les règles appliquées "
        "côté serveur : l'interface ne fait que les rendre visibles.",
    )
    k.add_table(
        doc,
        ["Action", "Propriétaire / admin cabinet", "Gestionnaire de paie", "Entreprise", "Salarié"],
        [
            ["Créer un dossier", "Oui", "Oui", "Non", "Non"],
            ["Créer un établissement", "Oui", "Oui (sociétés affectées)", "Non", "Non"],
            ["Créer un salarié / contrat", "Oui", "Oui (sociétés affectées)", "Non", "Non"],
            ["Saisir les variables", "Oui", "Oui (sociétés affectées)", "Oui", "Non"],
            ["Calculer les bulletins", "Oui", "Oui (sociétés affectées)", "Non", "Non"],
            ["Valider les bulletins", "Oui", "Oui (sociétés affectées)", "Non", "Non"],
            ["Consulter les bulletins", "Oui", "Oui (sociétés affectées)", "Oui (son dossier)", "Oui (les siens)"],
            ["Consulter les constantes / plan de paie", "Oui (lecture)", "Oui (lecture)", "Non", "Non"],
            ["Gérer les utilisateurs du cabinet", "Oui", "Non", "Non", "Non"],
            ["Traiter une réclamation", "Oui", "Oui (sociétés affectées)", "Non", "Non"],
            ["Déposer une réclamation", "Non", "Non", "Non", "Oui"],
            ["Valider un congé / acompte", "Non", "Non", "Oui", "Non"],
        ],
        widths=[5.6, 3.8, 3.4, 2.4, 2.2],
        font_size=8.2,
        align_center=True,
    )
    k.add_para(doc, "La modification des constantes et du plan de paie relève du support payohada ; les cabinets y accèdent uniquement en lecture.", space_after=6)

    # ── Chapitre 9 ────────────────────────────────────────────────────────
    k.add_heading(doc, "9. Glossaire", level=1, page_break=True)
    k.add_lead(
        doc,
        "Les termes ci-dessous sont utilisés dans l'application et dans ce manuel.",
    )
    glossary = [
        ("**Bulletin de paie**", "Document récapitulant la rémunération d'un salarié pour une période : gains, retenues et net à payer."),
        ("**Salaire brut**", "Rémunération avant déduction des cotisations salariales et de l'impôt."),
        ("**Net à payer**", "Montant effectivement versé au salarié après déductions."),
        ("**Net imposable**", "Base de calcul de l'impôt sur le revenu, après déductions autorisées."),
        ("**ITS**", "Impôt sur les traitements et salaires : impôt progressif retenu à la source."),
        ("**CNPS**", "Caisse nationale de prévoyance sociale : retraite, prestations familiales, accidents du travail, maternité."),
        ("**CMU**", "Couverture maladie universelle : cotisation de santé."),
        ("**RICF**", "Réduction d'impôt pour charges de famille, appliquée selon la situation et les enfants à charge."),
        ("**SMIG**", "Salaire minimum interprofessionnel garanti."),
        ("**CCN**", "Convention collective nationale applicable à l'entreprise."),
        ("**Période de paie**", "Mois et année auxquels se rattachent les variables et les bulletins."),
        ("**Variable de paie**", "Élément du mois saisi hors contrat : heures supplémentaires, absence, prime, acompte."),
        ("**Bulletin en brouillon**", "Bulletin calculé mais encore modifiable."),
        ("**Bulletin validé**", "Bulletin définitif, mis à disposition de l'entreprise et du salarié."),
        ("**Invalider**", "Rouvrir une période validée pour corriger puis recalculer un bulletin."),
        ("**Édition**", "État collectif produit à partir des bulletins (journal, livre, CNPS, ITS, charges)."),
        ("**DSN / NetEntreprise**", "Déclaration sociale nominative et plateforme de dépôt associée."),
        ("**RCCM**", "Registre du commerce et du crédit mobilier : identifiant légal de l'entreprise."),
        ("**NIR**", "Numéro d'inscription au répertoire (numéro de sécurité sociale)."),
        ("**IBAN**", "Identifiant bancaire international du compte de versement."),
        ("**Matricule**", "Identifiant du salarié au sein de l'établissement."),
        ("**Établissement**", "Site de l'entreprise (siège, filiale, agence) auquel sont rattachés les salariés."),
        ("**Journal de paie**", "État récapitulatif par salarié et par mois."),
        ("**Livre de paie**", "État détaillé de toutes les rubriques, ligne à ligne."),
        ("**OHADA**", "Organisation pour l'harmonisation en Afrique du droit des affaires."),
    ]
    k.add_table(
        doc,
        ["Terme", "Définition"],
        glossary,
        widths=[4.6, 12.4],
        font_size=8.6,
    )

    # ── Chapitre 10 ────────────────────────────────────────────────────────
    k.add_heading(doc, "10. Annexes", level=1, page_break=True)
    k.add_lead(
        doc,
        "Calendrier type, checklist de clôture et rappel des statuts : à imprimer ou à "
        "garder sous la main.",
    )

    k.add_heading(doc, "Annexe A — Calendrier mensuel type", level=2)
    k.add_table(
        doc,
        ["Période", "Cabinet", "Entreprise", "Salarié"],
        [
            ["Début du mois", "Vérifie les contrats et les arrivées/départs.", "Prépare les éléments variables.", "Signale les absences."],
            ["J-5 avant clôture", "Relance les variables manquantes.", "Saisit et transmet la grille.", "Dépose les demandes de congés/acomptes."],
            ["Jour de clôture", "Calcule et contrôle les bulletins.", "Valide les demandes en attente.", "—"],
            ["J+1", "Corrige si besoin et valide.", "Consulte les bulletins.", "—"],
            ["J+2", "Édite et exporte les états.", "Télécharge les bulletins.", "Consulte ses bulletins."],
        ],
        widths=[3.4, 4.8, 4.6, 4.2],
        font_size=8.6,
    )

    k.add_heading(doc, "Annexe B — Checklist de clôture de paie", level=2)
    k.add_table(
        doc,
        ["Fait", "Point de contrôle"],
        [
            ["☐", "Tous les salariés présents ont une fiche et un contrat actif."],
            ["☐", "Les heures supplémentaires, absences, primes et acomptes sont saisis."],
            ["☐", "Les demandes de congés et d'acomptes en attente sont traitées."],
            ["☐", "Les bulletins sont calculés sans erreur."],
            ["☐", "Les totaux (brut, cotisations, net) sont cohérents avec le mois précédent."],
            ["☐", "Les bulletins sont validés."],
            ["☐", "Le journal de paie, le livre de paie et les états CNPS/ITS sont exportés."],
            ["☐", "Les documents sont archivés dans l'espace prévu."],
        ],
        widths=[1.2, 15.8],
        font_size=8.8,
        align_center=False,
    )

    k.add_heading(doc, "Annexe C — Statuts et significations", level=2)
    k.add_table(
        doc,
        ["Domaine", "Statuts"],
        [
            ["Période de paie", "Saisie en cours · Transmis · Calculé · Validé"],
            ["Bulletin", "Brouillon · Calculé · Validé"],
            ["Demande de congé", "En attente · Validée · Refusée"],
            ["Demande d'acompte", "En attente · Validée · Refusée"],
            ["Réclamation", "À traiter · Traitée · Rejetée"],
            ["Compte utilisateur", "Actif · Désactivé"],
            ["Import de données", "Analyse · Prêt · Mapping requis · Terminé · Échec"],
        ],
        widths=[4.4, 12.6],
        font_size=8.8,
    )

    k.add_heading(doc, "Annexe D — Support", level=2)
    k.add_para(
        doc,
        "Avant de contacter le support, munissez-vous des informations suivantes : "
        "votre rôle et votre email de connexion, le nom du dossier ou du salarié concerné, "
        "la période de paie, l'écran où le problème survient et le message exact affiché.",
    )
    k.add_table(
        doc,
        ["Interlocuteur", "Quand le contacter"],
        [
            ["**Administrateur du cabinet**", "Comptes, rôles, affectations, accès aux dossiers."],
            ["**Support payohada**", "Anomalie reproductible, message d'erreur, problème d'export ou d'email."],
        ],
        widths=[5.4, 11.6],
        font_size=8.8,
    )

    k.add_spacer(doc, 18)
    k.add_callout(
        doc,
        "success",
        "Fin du manuel",
        "Vous disposez désormais des repères essentiels pour chaque rôle. Ce document "
        "est versionné : consultez la version la plus récente avant toute formation ou "
        "prise de poste.",
    )
