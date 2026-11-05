"""Partie II du manuel : guides par rôle."""
from __future__ import annotations

from pathlib import Path

from docx import Document

import manuel_kit as k

IMAGES = Path(__file__).resolve().parent.parent / "captures" / "manuel"


def render(doc: Document) -> None:
    k.add_part_divider(
        doc,
        "II",
        "Guides par rôle",
        "Chaque espace est présenté de façon autonome : parcours quotidiens, "
        "champs à renseigner, actions à effectuer et points de vigilance.",
        [
            "**3. Guide Cabinet** — propriétaire, administrateur et gestionnaire de paie.",
            "**4. Guide Entreprise** — saisie des variables, bulletins et demandes.",
            "**5. Guide Salarié** — bulletins, congés, acomptes et réclamations.",
        ],
    )

    # ══════════════════════════════════════════════════════════════════════
    # Chapitre 3 — Cabinet
    # ══════════════════════════════════════════════════════════════════════
    k.add_heading(doc, "3. Guide Cabinet", level=1, page_break=True)
    k.add_lead(
        doc,
        "Le cabinet produit la paie des entreprises clientes. Il tient le registre "
        "des dossiers, des établissements, des salariés et des contrats, puis calcule, "
        "valide et édite les bulletins.",
    )

    k.add_heading(doc, "Fiche rôle — qui fait quoi au cabinet", level=2)
    k.add_table(
        doc,
        ["", "Propriétaire", "Administrateur du cabinet", "Gestionnaire de paie"],
        [
            ["Créé par", "Inscription du cabinet", "Invitation du propriétaire", "Invitation du propriétaire"],
            ["Sociétés accessibles", "Toutes ses sociétés", "Toutes les sociétés du propriétaire",
             "Uniquement les sociétés affectées"],
            ["Administration > Utilisateurs", "Oui", "Oui", "Non"],
            ["Constantes / Plan de paie", "Consultation seule", "Consultation seule", "Consultation seule"],
            ["Créer / modifier un dossier", "Oui", "Oui", "Selon affectation"],
            ["Calculer et valider la paie", "Oui", "Oui", "Oui, sur ses sociétés"],
        ],
        widths=[4.6, 3.9, 4.3, 4.2],
        font_size=8.6,
    )

    k.add_heading(doc, "3.1 Le tableau de bord des dossiers", level=2)
    k.add_figure(
        doc,
        IMAGES / "02-cabinet.png",
        "Figure 2 — Tableau de bord des dossiers du cabinet.",
    )
    k.add_para(
        doc,
        "La page **Entreprises** liste les dossiers auxquels vous avez accès. Chaque "
        "carte affiche le code du dossier, la raison sociale, le RCCM, le contact et "
        "l'exercice annuel.",
    )
    k.add_steps(doc, [
        "Cliquez sur la carte d'un dossier pour ouvrir son espace de travail.",
        "Utilisez **Nouveau Dossier** pour créer une entreprise cliente (voir 3.2).",
        "Le bouton d'actualisation recharge la liste sans quitter la page.",
    ])

    k.add_heading(doc, "3.2 Créer un dossier client", level=2)
    k.add_para(
        doc,
        "Un dossier représente une entreprise cliente. Il contient ses établissements, "
        "son personnel, ses contrats et ses bulletins.",
    )
    k.add_steps(doc, [
        "Depuis l'accueil, cliquez sur **Nouveau Dossier**.",
        "Renseignez le **code dossier** (identifiant court et unique) et l'**exercice annuel**.",
        "Saisissez la **raison sociale**, le **RCCM**, le **jour de virement** habituel des salaires et le **pays de référence**.",
        "Complétez le contact : nom, qualité, email et téléphone.",
        "Validez : le dossier apparaît immédiatement dans la liste.",
    ])
    k.add_table(
        doc,
        ["Champ", "Obligatoire", "Conseil"],
        [
            ["Code dossier", "Oui", "Ex. NORD01 : stable, sans espace ni accent."],
            ["Exercice annuel", "Oui", "Année de gestion du dossier (ex. 2026)."],
            ["Nom de l'entreprise", "Oui", "Raison sociale exacte, telle qu'elle figurera sur les bulletins."],
            ["RCCM", "Non", "Numéro d'immatriculation au registre du commerce."],
            ["Jour de virement", "Non", "Jour habituel de paiement des salaires (1 à 31)."],
            ["Pays de référence", "Oui", "Détermine les règles de paie proposées."],
            ["Contact", "Non", "Interlocuteur côté entreprise (direction, RH)."],
        ],
        widths=[4.2, 2.4, 10.4],
        font_size=8.8,
    )

    k.add_heading(doc, "3.3 Gérer un dossier", level=2)
    k.add_figure(
        doc,
        IMAGES / "03-dossier.png",
        "Figure 3 — Onglets d'un dossier client (Établissements, NetEntreprise, Départements, etc.).",
    )
    k.add_table(
        doc,
        ["Onglet", "À quoi il sert"],
        [
            ["**Établissements**", "Créer et gérer les sites (siège, filiales, agences) et leurs paramètres de paie."],
            ["**NetEntreprise (DSN)**", "Préparer la déclaration sociale nominative : paramètres et suivi."],
            ["**Départements**", "Organiser le personnel par service ou direction."],
            ["**Informations Générales**", "Modifier les informations du dossier (contact, RCCM, exercice…)."],
            ["**Accès Client (Entreprise)**", "Créer le compte de l'entreprise qui saisira les variables."],
            ["**Gestionnaires de paie**", "Affecter un ou plusieurs gestionnaires à cette société."],
        ],
        widths=[5.2, 11.8],
        font_size=8.8,
    )
    k.add_callout(
        doc,
        "success",
        "Astuce",
        "Travaillez toujours de haut en bas : dossier → établissement → salarié → "
        "contrat. Un bulletin ne peut pas être calculé sans contrat actif.",
    )

    k.add_heading(doc, "3.4 Créer un établissement", level=2)
    k.add_para(
        doc,
        "L'établissement est le niveau où sont rattachés les salariés et les contrats. "
        "Un dossier peut contenir plusieurs établissements.",
    )
    k.add_steps(doc, [
        "Ouvrez le dossier, puis l'onglet **Établissements**.",
        "Cliquez sur **Créer un établissement**.",
        "Renseignez l'identité : code, raison sociale, sigle, RCCM, date de création et secteur d'activité.",
        "Complétez l'adresse (pays, commune, quartier, îlot, boîte postale) et les contacts.",
        "Vérifiez les paramètres de paie et RH : adresse d'édition, mode d'ancienneté, période de congés, gestion des soldes.",
        "Enregistrez : l'établissement est prêt à recevoir des salariés.",
    ])
    k.add_table(
        doc,
        ["Bloc", "Champs principaux", "Pourquoi c'est important"],
        [
            ["Identité", "Code, raison sociale, sigle, RCCM, secteur",
             "Repris sur les états et certaines déclarations."],
            ["Adresse", "Pays, commune, quartier, îlot, BP, téléphone, email, site web",
             "Adresse légale et coordonnées de l'employeur."],
            ["Édition & RH", "Adresse d'édition, mode d'ancienneté, année civile, période de congés, mode de solde",
             "Détermine ce qui est imprimé et la façon dont les congés sont comptés."],
        ],
        widths=[3.4, 7.8, 5.8],
        font_size=8.8,
    )

    k.add_heading(doc, "3.5 Créer un salarié", level=2)
    k.add_para(
        doc,
        "Le salarié est rattaché à un établissement. Sa fiche alimente les bulletins, "
        "les déclarations et l'espace personnel du salarié.",
    )
    k.add_steps(doc, [
        "Ouvrez l'établissement, puis l'onglet **Salariés**.",
        "Cliquez sur **Nouvel employé**.",
        "Renseignez l'état civil : civilité, prénom, nom, matricule, date et lieu de naissance, nationalité.",
        "Complétez la situation familiale et le nombre d'enfants à charge (utiles au calcul de l'ITS).",
        "Ajoutez les coordonnées et le IBAN de versement du salaire.",
        "Enregistrez : la fiche du salarié est créée, ses onglets complémentaires sont disponibles.",
    ])
    k.add_table(
        doc,
        ["Onglet de la fiche salarié", "Contenu"],
        [
            ["**État Civil / Fiche**", "Identité, adresse, coordonnées, situation familiale, IBAN."],
            ["**Contrats**", "Contrats de travail successifs et leur statut."],
            ["**Entretiens**", "Entretiens d'évaluation."],
            ["**Visites Médicales**", "Suivi de la médecine du travail."],
            ["**Formations**", "Formations suivies."],
            ["**Absences**", "Absences et congés enregistrés."],
            ["**Prêts**", "Prêts et avances consentis au salarié."],
            ["**Contrats HR**", "Informations complémentaires de contrat."],
            ["**Services**", "Services et avantages."],
            ["**Archivage**", "Documents archivés du salarié."],
        ],
        widths=[5.0, 12.0],
        font_size=8.8,
    )
    k.add_callout(
        doc,
        "info",
        "À savoir",
        "Le **matricule** doit être unique au sein de l'établissement. La **situation "
        "familiale** et le **nombre d'enfants à charge** influencent le calcul de l'ITS : "
        "vérifiez-les avant le premier bulletin.",
    )

    k.add_heading(doc, "3.6 Créer un contrat de travail", level=2)
    k.add_para(
        doc,
        "Le contrat porte les éléments de rémunération et de temps de travail. C'est "
        "lui qui est utilisé par le moteur de paie pour produire les bulletins.",
    )
    k.add_steps(doc, [
        "Ouvrez la fiche du salarié, puis l'onglet **Contrats**.",
        "Cliquez sur **Nouveau contrat**.",
        "Saisissez le numéro de contrat, le poste, le type de contrat, le statut professionnel et les dates.",
        "Choisissez le type de salaire (mensuel ou horaire), la nature du salaire (brut) et l'unité de temps.",
        "Renseignez le salaire de base, le sursalaire éventuel, l'indemnité de transport et la dotation téléphonique.",
        "Ajoutez la convention collective (CCN) si elle s'applique, puis enregistrez.",
    ])
    k.add_table(
        doc,
        ["Champ", "Exemple / valeur", "Remarque"],
        [
            ["Type de contrat", "CDI (10), CDD (29), apprentissage (18), professionnalisation (28)", "Codes utilisés par les déclarations."],
            ["Statut professionnel", "Cadre (1), non-cadre (2), ouvrier/employé (3)", "Peut influencer les règles applicables."],
            ["Type de salaire", "Mensuel ou horaire", "Détermine la base de calcul."],
            ["Salaire de base", "350 000 FCFA", "Montant brut contractuel."],
            ["Indemnité de transport", "30 000 FCFA", "Élément non imposable dans les limites prévues."],
            ["CCN", "Identifiant de la convention collective", "À renseigner si l'entreprise est conventionnée."],
        ],
        widths=[4.4, 7.2, 5.4],
        font_size=8.8,
    )
    k.add_callout(
        doc,
        "warning",
        "Attention",
        "Un contrat doit être **actif** sur la période de paie pour qu'un bulletin puisse "
        "être calculé. Vérifiez les dates de début (et de fin pour un CDD) avant de lancer "
        "le calcul.",
    )

    k.add_heading(doc, "3.7 Affecter un gestionnaire de paie", level=2)
    k.add_para(
        doc,
        "Le propriétaire ou un administrateur du cabinet peut confier une société à un "
        "gestionnaire. Le gestionnaire ne voit que les sociétés qui lui sont affectées.",
    )
    k.add_steps(doc, [
        "Ouvrez le dossier, puis l'onglet **Gestionnaires de paie**.",
        "Saisissez l'email du gestionnaire, son nom et son prénom.",
        "Choisissez un mot de passe ou laissez la plateforme en générer un.",
        "Validez : le compte est créé (ou le compte existant est rattaché) et l'affectation est immédiate.",
    ])
    k.add_table(
        doc,
        ["Situation", "Résultat"],
        [
            ["Le gestionnaire a déjà un compte", "Il est rattaché à la société sans nouveau mot de passe."],
            ["Le gestionnaire est nouveau", "Un compte gestionnaire_paie est créé et les identifiants sont envoyés par email."],
            ["Le gestionnaire est déjà affecté", "L'affectation en double est refusée."],
        ],
        widths=[6.2, 10.8],
        font_size=8.8,
    )

    k.add_heading(doc, "3.8 Le cycle de paie mensuel", level=2)
    k.add_table(
        doc,
        ["Étape", "Acteur", "Ce qui se passe"],
        [
            ["1. Saisie des variables", "Entreprise cliente (ou cabinet)",
             "Heures supplémentaires, absences, primes et acomptes du mois sont saisis puis transmis."],
            ["2. Calcul des bulletins", "Cabinet",
             "Le moteur applique les règles de paie (cotisations, ITS, avantages) et produit les bulletins en brouillon."],
            ["3. Validation", "Cabinet",
             "Les bulletins sont vérifiés puis validés : ils deviennent définitifs et sont mis à disposition."],
            ["4. Mise à disposition", "Entreprise et salariés",
             "Les bulletins et les états de paie sont consultables, imprimables et téléchargeables."],
        ],
        widths=[4.4, 4.2, 8.4],
        font_size=8.8,
    )
    k.add_callout(
        doc,
        "info",
        "À savoir",
        "Le statut d'une période est visible côté entreprise : **saisie en cours**, "
        "**transmis**, **calculé**, **validé**. Le cabinet peut suivre l'avancement dans "
        "l'onglet **Bulletins de Salaire**.",
    )

    k.add_heading(doc, "3.9 Saisir ou compléter les variables", level=2)
    k.add_para(
        doc,
        "Les variables sont normalement saisies par l'entreprise. Le cabinet peut les "
        "compléter ou les corriger depuis l'écran des bulletins.",
    )
    k.add_table(
        doc,
        ["Type", "Exemples de codes", "Effet sur le bulletin"],
        [
            ["Heures supplémentaires", "HS15, HS25, HS50, HS75, HS100",
             "Majoration du salaire selon le taux applicable."],
            ["Absences et congés", "CP, MAL, AT, maternité, absence non autorisée",
             "Neutralisation ou déduction selon le motif."],
            ["Primes et indemnités", "Prime de rendement, panier, transport exceptionnel",
             "Ajout d'un gain imposable ou non imposable."],
            ["Acomptes", "Acompte sur salaire",
             "Déduction du net à payer du mois concerné."],
        ],
        widths=[4.4, 6.8, 5.8],
        font_size=8.8,
    )
    k.add_bullets(doc, [
        "Utilisez les boutons **+ HS**, **+ Absence** et **+ Prime** sur la ligne du salarié.",
        "Le bouton **Import / Export Variables de Paie** permet de travailler dans Excel puis de réimporter la grille.",
        "Contrôlez toujours les totaux affichés avant de calculer les bulletins.",
    ])

    k.add_heading(doc, "3.10 Calculer, valider et corriger les bulletins", level=2)
    k.add_steps(doc, [
        "Ouvrez le dossier, l'établissement, puis **Bulletins de Salaire**.",
        "Sélectionnez le **mois** et l'**année** de la période.",
        "Cliquez sur **Calculer les bulletins** pour traiter tous les contrats actifs, ou sur **Calculer** pour un seul salarié.",
        "Contrôlez les montants, les cotisations et le net à payer.",
        "Cliquez sur **Valider** (un bulletin ou une sélection) lorsque tout est correct.",
    ])
    k.add_table(
        doc,
        ["Statut", "Signification", "Actions possibles"],
        [
            ["**Brouillon**", "Bulletin calculé mais non validé", "Recalculer, corriger les variables, valider."],
            ["**Calculé**", "Bulletin produit par le moteur", "Vérifier, valider ; un recalcul reste possible avant validation."],
            ["**Validé**", "Bulletin définitif", "Imprimer, envoyer ; pour corriger, invalider puis recalculer."],
        ],
        widths=[3.2, 6.4, 7.4],
        font_size=8.8,
    )
    k.add_callout(
        doc,
        "warning",
        "Attention",
        "La validation est l'étape de contrôle : un bulletin validé ne peut plus être "
        "recalculé directement. Utilisez **Invalider** pour rouvrir la période, corriger, "
        "puis recalculer et valider à nouveau.",
    )

    k.add_heading(doc, "3.11 Consulter, imprimer et envoyer les bulletins", level=2)
    k.add_bullets(doc, [
        "**Visualiser** ouvre le bulletin au format officiel (modèle Sage Saari) dans un nouvel onglet.",
        "Le bouton **PDF** télécharge le bulletin du salarié.",
        "L'impression en lot permet de générer tous les bulletins de la période en un fichier.",
        "L'envoi par email met le bulletin à disposition du salarié et de l'entreprise, selon les droits.",
        "Les pièces jointes et documents de sortie (attestation, certificat, STC) se gèrent depuis la fiche du salarié.",
    ])

    k.add_heading(doc, "3.12 Éditions et états de paie", level=2)
    k.add_para(
        doc,
        "Les éditions agrègent les bulletins déjà calculés. Elles ne recalculent rien : "
        "un état ne peut donc pas diverger d'un bulletin.",
    )
    k.add_table(
        doc,
        ["Édition", "Ce qu'elle contient"],
        [
            ["**Journal de paie**", "Synthèse par salarié et par mois : brut, cotisations, net imposable, ITS et net à payer."],
            ["**Livre de paie**", "Détail de toutes les rubriques, ligne à ligne."],
            ["**État des cotisations CNPS**", "Bases et parts salariale et patronale par branche."],
            ["**État de l'ITS**", "Brut imposable, impôt brut, réduction pour charges de famille et impôt net."],
            ["**Récapitulatif des charges patronales**", "Toutes les contributions employeur, y compris les taxes sur salaires."],
        ],
        widths=[5.6, 11.4],
        font_size=8.8,
    )
    k.add_steps(doc, [
        "Ouvrez **Éditions** dans l'établissement.",
        "Sélectionnez la période et l'édition souhaitée.",
        "Choisissez le format : **PDF**, **Excel** ou **CSV**.",
        "Cliquez sur **Visualiser** pour un aperçu, ou **Télécharger** pour récupérer le fichier.",
        "Utilisez **Envoyer** pour expédier l'état par email à un destinataire.",
    ])

    k.add_heading(doc, "3.13 Le simulateur de paie", level=2)
    k.add_para(
        doc,
        "Le simulateur permet d'estimer un bulletin sans créer de données. Il est utile "
        "pour répondre à une question ou préparer une embauche.",
    )
    k.add_table(
        doc,
        ["Zone", "Champs"],
        [
            ["Rémunération", "Mode de calcul, salaire brut ou net, base mensuelle ou horaire, heures standard, taux AT patronal."],
            ["Éléments variables", "Sursalaire, régime expatrié, acompte déduit, transport, dotation téléphonique, absences."],
            ["Situation familiale", "Situation matrimoniale et nombre d'enfants à charge (réduction ITS)."],
        ],
        widths=[4.2, 12.8],
        font_size=8.8,
    )
    k.add_steps(doc, [
        "Ouvrez **Simulateur de Paie** dans le menu du cabinet.",
        "Renseignez les paramètres puis cliquez sur **Lancer le calcul**.",
        "Comparez le brut, le net et le détail des cotisations affichés.",
    ])
    k.add_callout(
        doc,
        "info",
        "À savoir",
        "Une simulation ne crée ni bulletin ni écriture comptable. Pour produire un "
        "bulletin réel, utilisez le dossier, l'établissement et le contrat du salarié.",
    )

    k.add_heading(doc, "3.14 Traiter les réclamations", level=2)
    k.add_steps(doc, [
        "Ouvrez **Réclamations** dans le menu du cabinet.",
        "Sélectionnez la réclamation : elle indique le salarié, le bulletin concerné et le motif.",
        "Choisissez le **statut du traitement** : À traiter, Acceptée & Traitée ou Rejetée.",
        "Rédigez la réponse, puis validez : le salarié voit immédiatement le retour.",
    ])
    k.add_table(
        doc,
        ["Statut", "Quand l'utiliser"],
        [
            ["**À traiter / En attente**", "La demande est reçue mais pas encore instruite."],
            ["**Acceptée & Traitée**", "La correction ou l'explication est apportée."],
            ["**Rejetée**", "La demande n'est pas fondée : la réponse doit expliquer pourquoi."],
        ],
        widths=[5.2, 11.8],
        font_size=8.8,
    )

    k.add_heading(doc, "3.15 Administrer le cabinet", level=2)
    k.add_para(
        doc,
        "Cette section est réservée au **propriétaire** et aux **administrateurs du "
        "cabinet**. Le menu **Administration** regroupe la gestion des utilisateurs et "
        "la consultation des référentiels globaux.",
    )
    k.add_figure(
        doc,
        IMAGES / "07-admin-utilisateurs.png",
        "Figure 4 — Gestion des utilisateurs du cabinet.",
    )

    k.add_heading(doc, "Inviter un collaborateur", level=3)
    k.add_steps(doc, [
        "Ouvrez **Administration > Utilisateurs**.",
        "Cliquez sur **Ajouter un membre**.",
        "Saisissez le prénom, le nom et l'email professionnel.",
        "Choisissez le rôle : **Gestionnaire de paie** ou **Administrateur du cabinet**.",
        "Laissez le mot de passe vide pour le générer et l'envoyer automatiquement, ou saisissez-le.",
        "Validez : le compte est créé et apparaît dans la liste.",
    ])
    k.add_table(
        doc,
        ["Rôle", "Accès", "À utiliser pour"],
        [
            ["**Administrateur du cabinet**", "Toutes les sociétés du propriétaire + administration des membres",
             "Un associé, un responsable de cabinet."],
            ["**Gestionnaire de paie**", "Uniquement les sociétés affectées",
             "Un gestionnaire paie ou un assistant."],
        ],
        widths=[4.8, 7.6, 4.6],
        font_size=8.8,
    )

    k.add_heading(doc, "Changer un rôle ou désactiver un compte", level=3)
    k.add_bullets(doc, [
        "Le sélecteur **Rôle** de chaque ligne permet de passer d'un rôle à l'autre ; l'effet est immédiat.",
        "Le bouton **Désactiver** bloque la connexion sans supprimer l'historique. **Réactiver** rétablit l'accès.",
        "Le propriétaire ne peut être ni rétrogradé ni désactivé ; son rôle est grisé dans la liste.",
    ])

    k.add_heading(doc, "Consulter les constantes et le plan de paie", level=3)
    k.add_para(
        doc,
        "Les onglets **Constantes** et **Plan de paie** sont consultables par le cabinet, "
        "en **lecture seule**. Les boutons de création, de modification et de suppression "
        "sont masqués, et l'API refuse toute écriture : la modification reste réservée "
        "au support payohada.",
    )
    k.add_figure(
        doc,
        IMAGES / "08-admin-constantes.png",
        "Figure 5 — Constantes de paie consultables en lecture seule par le cabinet.",
    )
    k.add_callout(
        doc,
        "info",
        "À savoir",
        "Les constantes (SMIG, plafonds et taux CNPS, CMU, taxes, etc.) sont communes à "
        "la plateforme. Si une valeur doit évoluer, contactez le support payohada.",
    )

    k.add_heading(doc, "3.16 Importer des données en masse", level=2)
    k.add_para(
        doc,
        "Pour une entreprise qui possède déjà des milliers de salariés, la création "
        "manuelle n'est pas envisageable. L'assistant d'import charge les données de "
        "base depuis un fichier **Excel** ou **CSV**, les valide à blanc, puis les "
        "crée ou les met à jour de façon idempotente.",
    )
    k.add_figure(
        doc,
        IMAGES / "09-imports.png",
        "Figure 6 — Assistant d'import des données de base (Excel / CSV).",
    )
    k.add_steps(doc, [
        "Ouvrez le dossier, puis cliquez sur **Importer des données (Excel/CSV)**.",
        "Choisissez le type : **Établissements**, **Salariés** ou **Contrats**.",
        "Téléchargez le **modèle Excel** et remplissez-le sans modifier la ligne d'en-tête.",
        "Déposez le fichier, puis cliquez sur **Analyser le fichier** : aucune donnée n'est écrite à ce stade.",
        "Lisez le rapport : lignes valides, lignes en erreur, colonnes manquantes. Corrigez le fichier ou associez les colonnes, puis relancez l'analyse.",
        "Cliquez sur **Exécuter l'import** (ou **Importer les lignes valides** si des erreurs subsistent).",
        "Consultez l'**historique des imports** pour retrouver le résultat et les compteurs.",
    ])
    k.add_table(
        doc,
        ["Type", "À importer", "Prérequis"],
        [
            ["**Établissements**", "Sites, sièges, filiales : code, raison sociale, adresse, paramètres de base.", "Aucun ; à importer en premier."],
            ["**Salariés**", "Identité, situation familiale, coordonnées, IBAN.", "Le code établissement doit exister."],
            ["**Contrats**", "Classification, dates, rémunération, transport, téléphone.", "L'établissement et le salarié doivent exister."],
        ],
        widths=[3.6, 8.4, 5.0],
        font_size=8.8,
    )
    k.add_callout(
        doc,
        "success",
        "Astuce",
        "Respectez l'ordre **établissements → salariés → contrats**. Un réimport du même "
        "fichier met à jour les enregistrements existants (même code établissement, même "
        "matricule, même numéro de contrat) au lieu de créer des doublons.",
    )
    k.add_callout(
        doc,
        "warning",
        "Attention",
        "L'analyse à blanc ne modifie rien, mais l'exécution est réelle. Vérifiez le "
        "rapport avant de cliquer sur **Exécuter l'import**. Les fichiers sont limités à "
        "25 Mo et supprimés après exécution.",
    )

    k.add_heading(doc, "3.17 Bonnes pratiques et checklist mensuelle", level=2)
    k.add_bullets(doc, [
        "Vérifiez les contrats actifs et les dates de début/fin avant chaque calcul.",
        "Contrôlez les variables transmises par l'entreprise : heures, absences, primes, acomptes.",
        "Calculez d'abord en brouillon, relisez les écarts, puis validez.",
        "Exportez les états de paie et conservez-les avec les bulletins de la période.",
        "Ne réutilisez jamais un compte nominatif : créez un compte par utilisateur.",
    ])
    k.add_table(
        doc,
        ["Avant la clôture", "Vérification"],
        [
            ["Contrats", "Tous les salariés présents ont un contrat actif sur la période."],
            ["Variables", "Heures supplémentaires, absences, primes et acomptes sont saisis."],
            ["Calcul", "Les bulletins sont calculés sans erreur et les totaux sont cohérents."],
            ["Validation", "Les bulletins sont validés et les états sont exportés."],
            ["Archivage", "Bulletins, journal de paie et états CNPS/ITS sont conservés."],
        ],
        widths=[5.0, 12.0],
        font_size=8.8,
    )

    # ══════════════════════════════════════════════════════════════════════
    # Chapitre 4 — Entreprise
    # ══════════════════════════════════════════════════════════════════════
    k.add_heading(doc, "4. Guide Entreprise", level=1, page_break=True)
    k.add_lead(
        doc,
        "L'espace Entreprise permet de préparer la paie du mois : saisir les variables, "
        "transmettre la grille au cabinet, consulter les bulletins et valider les demandes "
        "du personnel.",
    )

    k.add_heading(doc, "Fiche rôle — entreprise cliente", level=2)
    k.add_table(
        doc,
        ["", "Votre périmètre"],
        [
            ["Compte", "client, rattaché à un dossier (une entreprise)."],
            ["Menus", "Tableau de bord · Saisie des Variables · Bulletins de Paie · Personnel · Demandes · Réclamations."],
            ["Vous pouvez", "Saisir et transmettre les variables ; consulter et télécharger les bulletins ; valider ou refuser congés et acomptes ; suivre les réclamations."],
            ["Vous ne pouvez pas", "Calculer ou valider les bulletins (rôle du cabinet) ; modifier les référentiels globaux."],
        ],
        widths=[4.0, 13.0],
        font_size=8.8,
    )

    k.add_heading(doc, "4.1 Le tableau de bord de l'entreprise", level=2)
    k.add_figure(
        doc,
        IMAGES / "04-client.png",
        "Figure 7 — Tableau de bord de l'entreprise pour la période en cours.",
    )
    k.add_para(
        doc,
        "Le tableau de bord affiche la période sélectionnée, l'avancement de la paie en "
        "quatre étapes et les indicateurs clés : effectif, variables saisies, primes "
        "déclarées et bulletins générés.",
    )
    k.add_steps(doc, [
        "Choisissez le **mois** et l'**année** dans le sélecteur de période.",
        "Lisez l'étape en cours : saisie client, transmission, calcul cabinet ou mise à disposition.",
        "Cliquez sur une carte d'action (**Saisir les variables**, **Consulter les bulletins**, **Personnel**) pour ouvrir l'écran correspondant.",
    ])

    k.add_heading(doc, "4.2 Saisir les variables de paie du mois", level=2)
    k.add_figure(
        doc,
        IMAGES / "05-variables.png",
        "Figure 8 — Grille de saisie des variables mensuelles.",
    )
    k.add_para(
        doc,
        "La grille présente un salarié par ligne et les rubriques du mois : salaire de "
        "base, heures supplémentaires, congés et absences, primes et indemnités, statut "
        "du bulletin.",
    )
    k.add_steps(doc, [
        "Ouvrez **Saisie des Variables** et sélectionnez le mois et l'année.",
        "Pour chaque salarié, cliquez sur **+ HS** pour ajouter des heures supplémentaires (code et nombre).",
        "Cliquez sur **+ Absence** pour enregistrer un congé ou une absence (dates, motif, durée).",
        "Cliquez sur **+ Prime** pour ajouter une prime ou une indemnité.",
        "Vérifiez les totaux et les statuts, puis cliquez sur **Transmettre au Cabinet**.",
    ])
    k.add_table(
        doc,
        ["Rubrique", "À saisir", "Exemple"],
        [
            ["Heures supplémentaires", "Code de majoration et nombre d'heures", "HS25 : 10 heures"],
            ["Congés et absences", "Dates, motif, nombre de jours ou d'heures", "Congés payés du 12 au 20"],
            ["Primes et indemnités", "Libellé et montant", "Prime de rendement : 25 000 FCFA"],
            ["Acomptes", "Montant déjà versé au salarié", "Acompte : 50 000 FCFA"],
        ],
        widths=[4.4, 7.4, 5.2],
        font_size=8.8,
    )

    k.add_heading(doc, "Utiliser Excel (maquette et import)", level=3)
    k.add_bullets(doc, [
        "**Maquette Excel** télécharge la grille pré-remplie avec le personnel de l'entreprise.",
        "Complétez-la hors ligne, puis utilisez **Importer Excel** pour la réinjecter.",
        "Vérifiez le message de résultat : les lignes importées et les éventuelles erreurs y sont indiquées.",
        "Après import, contrôlez de nouveau la grille avant de transmettre.",
    ])

    k.add_heading(doc, "Statut de la période et transmission", level=3)
    k.add_table(
        doc,
        ["Statut", "Signification", "Votre action"],
        [
            ["**Saisie en cours**", "La période est modifiable", "Complétez la grille, puis transmettez."],
            ["**Transmis**", "La grille est partie au cabinet", "Attendez le calcul ; signalez toute correction au cabinet."],
            ["**Calculé**", "Les bulletins sont produits", "Consultez les bulletins ; le cabinet peut encore corriger."],
            ["**Validé**", "La paie est définitive", "Téléchargez les bulletins et les états."],
        ],
        widths=[3.8, 6.2, 7.0],
        font_size=8.8,
    )
    k.add_callout(
        doc,
        "warning",
        "Attention",
        "Une fois la grille transmise, évitez de modifier les variables sans prévenir le "
        "cabinet : cela peut créer un décalage entre la saisie et le calcul.",
    )

    k.add_heading(doc, "4.3 Consulter les bulletins", level=2)
    k.add_steps(doc, [
        "Ouvrez **Bulletins de Paie**.",
        "Sélectionnez la période.",
        "Consultez la masse salariale, les cotisations et le net à verser.",
        "Ouvrez un bulletin pour le visualiser, l'imprimer ou le télécharger en PDF.",
    ])
    k.add_para(
        doc,
        "Les bulletins ne sont disponibles qu'après le calcul par le cabinet. Le statut "
        "affiché permet de savoir s'ils sont encore modifiables ou définitifs.",
    )

    k.add_heading(doc, "4.4 Consulter le personnel", level=2)
    k.add_para(
        doc,
        "L'écran **Personnel** liste les salariés de l'entreprise avec leur poste, leur "
        "matricule, leur date d'embauche et leurs contrats en cours. Il s'agit d'une vue "
        "de consultation : la création et la modification des fiches restent du ressort "
        "du cabinet.",
    )

    k.add_heading(doc, "4.5 Valider les demandes du personnel", level=2)
    k.add_para(
        doc,
        "L'entreprise est la seule autorité de décision pour les congés et les acomptes. "
        "Le cabinet ne décide pas à sa place.",
    )
    k.add_steps(doc, [
        "Ouvrez **Demandes** : les congés et acomptes en attente sont regroupés dans une file unique.",
        "Filtrez par statut ou par salarié si nécessaire.",
        "Ouvrez une demande pour voir le détail (dates, motif, solde ou montant).",
        "Validez ou refusez : un refus doit être motivé.",
    ])
    k.add_table(
        doc,
        ["Demande", "Effet d'une validation", "Effet d'un refus"],
        [
            ["**Congé**", "Une absence « Congés payés » est créée et sera prise en compte par la paie.", "Le salarié voit le motif du refus ; aucun congé n'est décompté."],
            ["**Acompte**", "L'avance est retenue sur le bulletin du mois choisi.", "Aucune retenue n'est appliquée."],
        ],
        widths=[3.4, 7.6, 6.0],
        font_size=8.8,
    )

    k.add_heading(doc, "4.6 Suivre les réclamations", level=2)
    k.add_para(
        doc,
        "L'écran **Réclamations** donne une vue en lecture seule des réclamations déposées "
        "par les salariés de l'entreprise et des réponses du cabinet. Le traitement est "
        "réservé au cabinet.",
    )

    k.add_heading(doc, "4.7 Bonnes pratiques", level=2)
    k.add_bullets(doc, [
        "Transmettez la grille avant la date limite convenue avec votre cabinet.",
        "Contrôlez les heures supplémentaires et les absences avant transmission.",
        "Traitez les demandes de congés et d'acomptes rapidement : elles impactent la paie du mois.",
        "Téléchargez et conservez les bulletins après validation.",
    ])
    k.add_heading(doc, "Récapitulatif : qui fait quoi entre l'entreprise et le cabinet", level=2)
    k.add_table(doc, ["Tâche", "Entreprise", "Cabinet"], [
        ["Fixer les éléments variables du mois", "Saisit et transmet", "Contrôle et complète si besoin"],
        ["Calculer les bulletins", "Non", "Oui"],
        ["Valider les bulletins", "Non", "Oui"],
        ["Valider les congés et les acomptes", "Oui (seule autorité)", "Non"],
        ["Mettre les bulletins à disposition", "Consulte et télécharge", "Produit et valide"],
        ["Traiter une réclamation de salarié", "En est informée", "Répond et clôture"],
    ], widths=[5.8, 5.2, 6.0], font_size=8.8)

    # ══════════════════════════════════════════════════════════════════════
    # Chapitre 5 — Salarié
    # ══════════════════════════════════════════════════════════════════════
    k.add_heading(doc, "5. Guide Salarié", level=1, page_break=True)
    k.add_lead(
        doc,
        "L'espace Salarié donne accès aux bulletins de paie, aux congés, aux acomptes et "
        "aux réclamations. Il est strictement personnel.",
    )

    k.add_heading(doc, "Fiche rôle — salarié", level=2)
    k.add_table(
        doc,
        ["", "Votre périmètre"],
        [
            ["Compte", "salarie, rattaché à une fiche salarié."],
            ["Menus", "Mes Bulletins · Mes Congés · Mes Acomptes."],
            ["Vous pouvez", "Consulter et télécharger vos bulletins ; demander des congés ou un acompte ; déposer et suivre une réclamation."],
            ["Vous ne pouvez pas", "Modifier vos bulletins, vos contrats ou vos données de paie."],
        ],
        widths=[4.0, 13.0],
        font_size=8.8,
    )

    k.add_heading(doc, "5.1 Consulter et télécharger ses bulletins", level=2)
    k.add_figure(
        doc,
        IMAGES / "06-salarie.png",
        "Figure 9 — Espace salarié : bulletins et suivi des réclamations.",
    )
    k.add_steps(doc, [
        "Ouvrez **Mes Bulletins**.",
        "Parcourez la liste chronologique des bulletins.",
        "Cliquez sur **Visualiser** pour ouvrir le bulletin, puis utilisez l'impression ou le téléchargement.",
    ])
    k.add_para(
        doc,
        "Chaque ligne indique la période, le salaire brut, le net à payer et le statut. "
        "Un bulletin en brouillon peut encore évoluer ; un bulletin validé est définitif. "
        "En cas de doute sur un montant, déposez une réclamation depuis la ligne concernée.",
    )

    k.add_heading(doc, "5.2 Demander un congé", level=2)
    k.add_steps(doc, [
        "Ouvrez **Mes Congés** : le solde acquis, pris et restant est affiché.",
        "Cliquez sur **Demander un congé**.",
        "Saisissez la date de début, la date de fin et, si besoin, un motif.",
        "Validez : la demande part à l'entreprise, qui accepte ou refuse.",
    ])
    k.add_para(
        doc,
        "Le solde est calculé par le serveur avec les mêmes règles que le bulletin. Une "
        "demande acceptée crée une absence « Congés payés » qui sera prise en compte dans "
        "la paie.",
    )

    k.add_heading(doc, "5.3 Demander un acompte", level=2)
    k.add_steps(doc, [
        "Ouvrez **Mes Acomptes**.",
        "Cliquez sur **Demander un acompte**.",
        "Indiquez le montant, le mois de paie concerné, l'année et un motif éventuel.",
        "Validez : l'entreprise accepte ou refuse.",
    ])
    k.add_callout(
        doc,
        "info",
        "À savoir",
        "Un acompte validé est retenu sur le bulletin du mois choisi. Anticipez-le pour "
        "éviter un net à payer trop faible.",
    )

    k.add_heading(doc, "5.4 Déposer une réclamation", level=2)
    k.add_steps(doc, [
        "Ouvrez **Mes Bulletins** ou l'encart **Suivi de mes réclamations**.",
        "Cliquez sur **Réclamation** sur le bulletin concerné.",
        "Décrivez précisément l'anomalie constatée.",
        "Validez : la réclamation est transmise au cabinet, qui répond.",
    ])
    k.add_para(
        doc,
        "Vous suivez l'état de la réclamation : **À traiter**, **Traitée** ou **Rejetée**, "
        "avec la réponse du cabinet.",
    )

    k.add_heading(doc, "5.5 Modifier son mot de passe", level=2)
    k.add_steps(doc, [
        "Cliquez sur **Modifier mon mot de passe** en haut de l'espace salarié.",
        "Saisissez le mot de passe actuel, puis le nouveau deux fois.",
        "Validez : le nouveau mot de passe est actif immédiatement.",
    ])

    k.add_heading(doc, "5.6 Bonnes pratiques", level=2)
    k.add_bullets(doc, [
        "Conservez vos bulletins : ils constituent des justificatifs de revenus et de droits.",
        "Contrôlez la période, le brut, les cotisations et le net à payer.",
        "Déposez une réclamation rapidement en cas d'écart, en citant le bulletin concerné.",
        "Ne partagez pas votre mot de passe : vous êtes responsable de l'accès à vos données.",
    ])
