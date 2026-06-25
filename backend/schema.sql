-- ==============================================================================
-- SCHEMA DE LA BASE DE DONNEES PAYOHADA (POSTGRESQL / SUPABASE)
-- ==============================================================================

-- 1. Table : utilisateurs
CREATE TABLE utilisateurs (
    id SERIAL PRIMARY KEY,
    email VARCHAR(150) NOT NULL UNIQUE,
    nom VARCHAR(100) DEFAULT NULL,
    prenom VARCHAR(100) DEFAULT NULL,
    hashed_password VARCHAR(255) DEFAULT NULL,
    supabase_uid VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_utilisateurs_email ON utilisateurs (email);
CREATE INDEX idx_utilisateurs_supabase_uid ON utilisateurs (supabase_uid);

-- 2. Table : variables (Référentiel)
CREATE TABLE variables (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    libelle VARCHAR(200) DEFAULT NULL,
    type VARCHAR(50) DEFAULT NULL,
    description TEXT DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX idx_variables_code ON variables (code);

-- 3. Table : dossiers (Entreprise Cliente / Tenant)
CREATE TABLE dossiers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    siret VARCHAR(14) DEFAULT NULL,
    nom_dossier VARCHAR(50) NOT NULL,
    adresse_email VARCHAR(150) DEFAULT NULL,
    telephone VARCHAR(15) DEFAULT NULL,
    nom_contact VARCHAR(100) DEFAULT NULL,
    qualite INTEGER DEFAULT NULL,
    annee VARCHAR(4) DEFAULT NULL,
    pays VARCHAR(100) DEFAULT 'Côte d''Ivoire',
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_dossiers_code ON dossiers (code);
CREATE INDEX idx_dossiers_siret ON dossiers (siret);

-- 4. Table : net_entreprises
CREATE TABLE net_entreprises (
    id SERIAL PRIMARY KEY,
    dossier_id INTEGER NOT NULL UNIQUE REFERENCES dossiers(id) ON DELETE CASCADE,
    parametrage_domaine BOOLEAN DEFAULT FALSE,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    siret VARCHAR(14) NOT NULL,
    civilite VARCHAR(10) DEFAULT NULL,
    email VARCHAR(150) DEFAULT NULL,
    telephone VARCHAR(15) DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Table : etablissements
CREATE TABLE etablissements (
    id SERIAL PRIMARY KEY,
    dossier_id INTEGER NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
    code VARCHAR(15) NOT NULL,
    raison_sociale VARCHAR(200) NOT NULL,
    etablissement_principal BOOLEAN DEFAULT FALSE,
    siret VARCHAR(14) DEFAULT NULL,
    forme_juridique INTEGER DEFAULT NULL,
    civilite VARCHAR(10) DEFAULT NULL,
    activite VARCHAR(200) DEFAULT NULL,
    ape VARCHAR(5) DEFAULT NULL,
    libelle_ape VARCHAR(200) DEFAULT NULL,
    ccn INTEGER DEFAULT NULL,
    ccn2 INTEGER DEFAULT NULL,
    ccn3 INTEGER DEFAULT NULL,
    ccn4 INTEGER DEFAULT NULL,
    ccn5 INTEGER DEFAULT NULL,
    avenant BOOLEAN DEFAULT FALSE,
    numero_cotisant VARCHAR(18) DEFAULT NULL,
    date_radiation TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    code_risque_at VARCHAR(20) DEFAULT NULL,
    taux_at DOUBLE PRECISION DEFAULT 0.0,
    is_taux_versement_transport BOOLEAN DEFAULT FALSE,
    taux_versement_transport DOUBLE PRECISION DEFAULT 0.0,
    -- CNPS & DGI Afrique
    cnps_matricule VARCHAR(50) DEFAULT NULL,
    cnps_code_activite VARCHAR(50) DEFAULT NULL,
    cnps_code_agence VARCHAR(50) DEFAULT NULL,
    cnps_code_etablissement VARCHAR(50) DEFAULT NULL,
    cnps_agence_rattachement VARCHAR(150) DEFAULT NULL,
    cnps_periodicite_paiement VARCHAR(50) DEFAULT NULL,
    cmu_periodicite_paiement VARCHAR(50) DEFAULT NULL,
    dgi_compte_contribuable VARCHAR(50) DEFAULT NULL,
    dgi_centre_impots VARCHAR(150) DEFAULT NULL,
    dgi_periodicite_declaration VARCHAR(50) DEFAULT NULL,
    dgi_regime_fiscal VARCHAR(150) DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_etablissement_dossier_code UNIQUE (dossier_id, code)
);
CREATE INDEX idx_etablissements_siret ON etablissements (siret);

-- 6. Table : adresses_etablissements
CREATE TABLE adresses_etablissements (
    id SERIAL PRIMARY KEY,
    etablissement_id INTEGER NOT NULL UNIQUE REFERENCES etablissements(id) ON DELETE CASCADE,
    adresse_postale VARCHAR(200) DEFAULT NULL,
    adresse_postale2 VARCHAR(200) DEFAULT NULL,
    complement_adresse VARCHAR(200) DEFAULT NULL,
    code_postal VARCHAR(10) DEFAULT NULL,
    ville VARCHAR(100) DEFAULT NULL,
    code_insee VARCHAR(10) DEFAULT NULL,
    code_distribution_etranger VARCHAR(20) DEFAULT NULL,
    pays VARCHAR(100) DEFAULT 'France'
);

-- 7. Table : gestion_conges_payes
CREATE TABLE gestion_conges_payes (
    id SERIAL PRIMARY KEY,
    etablissement_id INTEGER NOT NULL UNIQUE REFERENCES etablissements(id) ON DELETE CASCADE,
    mois_cloture_droits_cp INTEGER DEFAULT 5,
    report_automatique BOOLEAN DEFAULT TRUE,
    gestion_absences_heures_bulletins BOOLEAN DEFAULT TRUE,
    decompte_conges_payes VARCHAR(50) DEFAULT NULL,
    valorisation_conges_payes VARCHAR(50) DEFAULT NULL,
    bloquer_gestion_cp BOOLEAN DEFAULT FALSE,
    affilie_caisse_conges_payes BOOLEAN DEFAULT FALSE
);

-- 8. Table : banques_etablissements
CREATE TABLE banques_etablissements (
    id SERIAL PRIMARY KEY,
    etablissement_id INTEGER NOT NULL UNIQUE REFERENCES etablissements(id) ON DELETE CASCADE,
    virement BOOLEAN DEFAULT FALSE,
    code_bic VARCHAR(11) DEFAULT NULL,
    iban VARCHAR(34) DEFAULT NULL
);

-- 9. Table : caisses_cotisations
CREATE TABLE caisses_cotisations (
    id SERIAL PRIMARY KEY,
    etablissement_id INTEGER REFERENCES etablissements(id) ON DELETE CASCADE,
    nom_caisse VARCHAR(200) DEFAULT NULL,
    code_dsn VARCHAR(50) DEFAULT NULL,
    adresse_caisse TEXT DEFAULT NULL,
    type_cotisation VARCHAR(50) NOT NULL,
    exclus_de_calcul_dsn BOOLEAN DEFAULT FALSE,
    numero_affiliation VARCHAR(20) DEFAULT NULL,
    type_paiement VARCHAR(50) DEFAULT NULL,
    periodicite_paiement VARCHAR(50) DEFAULT NULL,
    date_paiement VARCHAR(20) DEFAULT NULL,
    iban VARCHAR(34) DEFAULT NULL,
    bic VARCHAR(11) DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 10. Table : dsns
CREATE TABLE dsns (
    id SERIAL PRIMARY KEY,
    dossier_id INTEGER NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
    etablissement_id INTEGER NOT NULL REFERENCES etablissements(id),
    mois INTEGER NOT NULL,
    annee INTEGER NOT NULL,
    statut VARCHAR(30) DEFAULT 'en_attente',
    contenu_txt TEXT DEFAULT NULL,
    date_envoi TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    reference_envoi VARCHAR(100) DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dsn_etablissement_periode UNIQUE (etablissement_id, mois, annee)
);

-- 11. Table : salaries
CREATE TABLE salaries (
    id SERIAL PRIMARY KEY,
    etablissement_id INTEGER NOT NULL REFERENCES etablissements(id) ON DELETE CASCADE,
    matricule VARCHAR(50) NOT NULL,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    nom_usage VARCHAR(100) DEFAULT NULL,
    civilite VARCHAR(10) DEFAULT NULL,
    date_naissance TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    lieu_naissance VARCHAR(100) DEFAULT NULL,
    departement_naissance VARCHAR(5) DEFAULT NULL,
    pays_naissance VARCHAR(100) DEFAULT NULL,
    nationalite VARCHAR(100) DEFAULT NULL,
    numero_securite_sociale VARCHAR(15) DEFAULT NULL,
    adresse VARCHAR(200) DEFAULT NULL,
    adresse2 VARCHAR(200) DEFAULT NULL,
    code_postal VARCHAR(10) DEFAULT NULL,
    ville VARCHAR(100) DEFAULT NULL,
    pays VARCHAR(100) DEFAULT 'France',
    email VARCHAR(150) DEFAULT NULL,
    telephone VARCHAR(15) DEFAULT NULL,
    iban VARCHAR(34) DEFAULT NULL,
    bic VARCHAR(11) DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    expatrie BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_salarie_etablissement_matricule UNIQUE (etablissement_id, matricule)
);
CREATE INDEX idx_salaries_matricule ON salaries (matricule);
CREATE INDEX idx_salaries_nir ON salaries (numero_securite_sociale);

-- 12. Table : contrats
CREATE TABLE contrats (
    id SERIAL PRIMARY KEY,
    dossier_id INTEGER NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
    salarie_id INTEGER NOT NULL REFERENCES salaries(id) ON DELETE CASCADE,
    etablissement_id INTEGER NOT NULL REFERENCES etablissements(id),
    code_etablissement VARCHAR(15) NOT NULL,
    matricule_salarie VARCHAR(50) NOT NULL,
    numero_contrat VARCHAR(50) NOT NULL,
    ancien_numero_contrat_dsn VARCHAR(50) DEFAULT NULL,
    emploi_conventionnel INTEGER DEFAULT NULL,
    ccn INTEGER DEFAULT NULL,
    idcc INTEGER DEFAULT NULL,
    emploi VARCHAR(200) DEFAULT NULL,
    type_contrat_travail INTEGER NOT NULL,
    type_contrat_temps_partiel INTEGER DEFAULT NULL,
    statut_professionnel INTEGER NOT NULL,
    regime_retraite INTEGER DEFAULT NULL,
    cas_particuliers INTEGER DEFAULT NULL,
    salaire_mensuel DOUBLE PRECISION DEFAULT 0.0,
    salaire_horaire DOUBLE PRECISION DEFAULT 0.0,
    type_salaire VARCHAR(10) DEFAULT 'Mensuel',
    nbr_heures_travail_mensuel_majorees DOUBLE PRECISION DEFAULT 0.0,
    date_debut_contrat VARCHAR(20) DEFAULT NULL,
    date_fin_previsionnelle_contrat VARCHAR(20) DEFAULT NULL,
    date_anciennete VARCHAR(20) DEFAULT NULL,
    salarie_temps_partiel BOOLEAN DEFAULT FALSE,
    forfait_jour BOOLEAN DEFAULT FALSE,
    ne_pas_calculer_premier_bulletin BOOLEAN DEFAULT FALSE,
    nbr_jour_annuels_prevus DOUBLE PRECISION DEFAULT 218.0,
    tags TEXT DEFAULT NULL,
    statut VARCHAR(20) DEFAULT 'actif',
    unite_temps VARCHAR(10) DEFAULT 'Heures',
    sursalaire DOUBLE PRECISION DEFAULT 0.0,
    indemnite_transport DOUBLE PRECISION DEFAULT 0.0,
    dotation_telephonique DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_contrat_dossier_numero UNIQUE (dossier_id, numero_contrat)
);

-- 13. Table : jours_hebdomadaires
CREATE TABLE jours_hebdomadaires (
    id SERIAL PRIMARY KEY,
    contrat_id INTEGER NOT NULL UNIQUE REFERENCES contrats(id) ON DELETE CASCADE,
    jours_hebdo DOUBLE PRECISION DEFAULT 5.0,
    jour_lundi DOUBLE PRECISION DEFAULT 1.0,
    jour_mardi DOUBLE PRECISION DEFAULT 1.0,
    jour_mercredi DOUBLE PRECISION DEFAULT 1.0,
    jour_jeudi DOUBLE PRECISION DEFAULT 1.0,
    jour_vendredi DOUBLE PRECISION DEFAULT 1.0,
    jour_samedi DOUBLE PRECISION DEFAULT 0.0,
    jour_dimanche DOUBLE PRECISION DEFAULT 0.0
);

-- 14. Table : horaires
CREATE TABLE horaires (
    id SERIAL PRIMARY KEY,
    contrat_id INTEGER NOT NULL UNIQUE REFERENCES contrats(id) ON DELETE CASCADE,
    horaire_travail DOUBLE PRECISION DEFAULT 151.67,
    horaire_hebdo DOUBLE PRECISION DEFAULT 35.0,
    horaire_lundi DOUBLE PRECISION DEFAULT 7.0,
    horaire_mardi DOUBLE PRECISION DEFAULT 7.0,
    horaire_mercredi DOUBLE PRECISION DEFAULT 7.0,
    horaire_jeudi DOUBLE PRECISION DEFAULT 7.0,
    horaire_vendredi DOUBLE PRECISION DEFAULT 7.0,
    horaire_samedi DOUBLE PRECISION DEFAULT 0.0,
    horaire_dimanche DOUBLE PRECISION DEFAULT 0.0
);

-- 15. Table : departs_salaries
CREATE TABLE departs_salaries (
    id SERIAL PRIMARY KEY,
    contrat_id INTEGER NOT NULL UNIQUE REFERENCES contrats(id) ON DELETE CASCADE,
    date_sortie VARCHAR(20) DEFAULT NULL,
    bulletin_post_contrat BOOLEAN DEFAULT FALSE,
    bulletin_post_contrat_du VARCHAR(20) DEFAULT NULL,
    bulletin_post_contrat_au VARCHAR(20) DEFAULT NULL,
    motif_sortie INTEGER DEFAULT NULL,
    date_notification_rupture VARCHAR(20) DEFAULT NULL,
    date_notification_signature VARCHAR(20) DEFAULT NULL,
    date_engagement_procedure VARCHAR(20) DEFAULT NULL,
    maintien_affiliation BOOLEAN DEFAULT FALSE,
    transaction_en_cours BOOLEAN DEFAULT FALSE,
    dernier_jour_travaille VARCHAR(20) DEFAULT NULL,
    statut_particulier INTEGER DEFAULT NULL,
    type_paiement_preavis01 INTEGER DEFAULT NULL,
    preavis_de01 VARCHAR(20) DEFAULT NULL,
    preavis_au01 VARCHAR(20) DEFAULT NULL,
    type_paiement_preavis02 INTEGER DEFAULT NULL,
    preavis_de02 VARCHAR(20) DEFAULT NULL,
    preavis_au02 VARCHAR(20) DEFAULT NULL,
    type_paiement_preavis03 INTEGER DEFAULT NULL,
    preavis_de03 VARCHAR(20) DEFAULT NULL,
    preavis_au03 VARCHAR(20) DEFAULT NULL
);

-- 16. Table : mois_a_exclure
CREATE TABLE mois_a_exclure (
    id SERIAL PRIMARY KEY,
    contrat_id INTEGER NOT NULL UNIQUE REFERENCES contrats(id) ON DELETE CASCADE,
    exclure_janvier BOOLEAN DEFAULT FALSE,
    exclure_fevrier BOOLEAN DEFAULT FALSE,
    exclure_mars BOOLEAN DEFAULT FALSE,
    exclure_avril BOOLEAN DEFAULT FALSE,
    exclure_mai BOOLEAN DEFAULT FALSE,
    exclure_juin BOOLEAN DEFAULT FALSE,
    exclure_juillet BOOLEAN DEFAULT FALSE,
    exclure_aout BOOLEAN DEFAULT FALSE,
    exclure_septembre BOOLEAN DEFAULT FALSE,
    exclure_octobre BOOLEAN DEFAULT FALSE,
    exclure_novembre BOOLEAN DEFAULT FALSE,
    exclure_decembre BOOLEAN DEFAULT FALSE
);

-- 17. Table : absences
CREATE TABLE absences (
    id SERIAL PRIMARY KEY,
    contrat_id INTEGER NOT NULL REFERENCES contrats(id) ON DELETE CASCADE,
    code VARCHAR(50) DEFAULT NULL,
    date_debut TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    date_fin TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    nbr_heure_by_user DOUBLE PRECISION DEFAULT 0.0,
    nbr_jour_by_user DOUBLE PRECISION DEFAULT 0.0,
    mois INTEGER DEFAULT NULL,
    annee VARCHAR(4) DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_absences_contrat_periode ON absences (contrat_id, annee, mois);

-- 18. Table : heures_supplementaires
CREATE TABLE heures_supplementaires (
    id SERIAL PRIMARY KEY,
    contrat_id INTEGER NOT NULL REFERENCES contrats(id) ON DELETE CASCADE,
    code VARCHAR(50) DEFAULT NULL,
    nombre DOUBLE PRECISION NOT NULL,
    mois INTEGER DEFAULT NULL,
    annee VARCHAR(4) DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_hs_contrat_periode ON heures_supplementaires (contrat_id, annee, mois);

-- 19. Table : primes
CREATE TABLE primes (
    id SERIAL PRIMARY KEY,
    contrat_id INTEGER NOT NULL REFERENCES contrats(id) ON DELETE CASCADE,
    code VARCHAR(50) DEFAULT NULL,
    montant DOUBLE PRECISION NOT NULL,
    mois INTEGER DEFAULT NULL,
    annee VARCHAR(4) DEFAULT NULL,
    libelle VARCHAR(200) DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 20. Table : options
CREATE TABLE options (
    id SERIAL PRIMARY KEY,
    contrat_id INTEGER NOT NULL REFERENCES contrats(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    valeur VARCHAR(200) DEFAULT NULL,
    valeur_numerique DOUBLE PRECISION DEFAULT NULL,
    mois INTEGER DEFAULT NULL,
    annee VARCHAR(4) DEFAULT NULL,
    libelle VARCHAR(200) DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 21. Table : variables_reprise_dossier
CREATE TABLE variables_reprise_dossier (
    id SERIAL PRIMARY KEY,
    contrat_id INTEGER NOT NULL REFERENCES contrats(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    valeur DOUBLE PRECISION DEFAULT 0.0,
    libelle VARCHAR(200) DEFAULT NULL,
    annee VARCHAR(4) DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 22. Table : bulletins_paies
CREATE TABLE bulletins_paies (
    id SERIAL PRIMARY KEY,
    contrat_id INTEGER NOT NULL REFERENCES contrats(id) ON DELETE CASCADE,
    dossier_id INTEGER NOT NULL REFERENCES dossiers(id),
    mois INTEGER NOT NULL,
    annee INTEGER NOT NULL,
    statut VARCHAR(30) DEFAULT 'brouillon',
    date_paiement TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    salaire_brut DOUBLE PRECISION DEFAULT 0.0,
    cotisations_salariales DOUBLE PRECISION DEFAULT 0.0,
    cotisations_patronales DOUBLE PRECISION DEFAULT 0.0,
    net_a_payer DOUBLE PRECISION DEFAULT 0.0,
    net_imposable DOUBLE PRECISION DEFAULT 0.0,
    commentaire TEXT DEFAULT NULL,
    inclure_document_de_sortie BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_bulletin_contrat_periode UNIQUE (contrat_id, mois, annee)
);
CREATE INDEX idx_bulletin_dossier_periode ON bulletins_paies (dossier_id, annee, mois);

-- 23. Table : lignes_bulletins_paies
CREATE TABLE lignes_bulletins_paies (
    id SERIAL PRIMARY KEY,
    bulletin_id INTEGER NOT NULL REFERENCES bulletins_paies(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    libelle VARCHAR(200) DEFAULT NULL,
    salaire_base DOUBLE PRECISION DEFAULT 0.0,
    base_s DOUBLE PRECISION DEFAULT 0.0,
    base_p DOUBLE PRECISION DEFAULT 0.0,
    taux_s DOUBLE PRECISION DEFAULT 0.0,
    taux_p DOUBLE PRECISION DEFAULT 0.0,
    montant_pr DOUBLE PRECISION DEFAULT 0.0,
    montant_cs DOUBLE PRECISION DEFAULT 0.0,
    montant_cp DOUBLE PRECISION DEFAULT 0.0,
    CONSTRAINT uq_ligne_bulletin_code UNIQUE (bulletin_id, code)
);
CREATE INDEX idx_ligne_bulletin_code ON lignes_bulletins_paies (bulletin_id, code);

-- 24. Table : variables_bulletins
CREATE TABLE variables_bulletins (
    id SERIAL PRIMARY KEY,
    bulletin_id INTEGER NOT NULL REFERENCES bulletins_paies(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    libelle VARCHAR(200) DEFAULT NULL,
    valeur DOUBLE PRECISION DEFAULT 0.0
);

-- 25. Table : soldes_tout_compte
CREATE TABLE soldes_tout_compte (
    id SERIAL PRIMARY KEY,
    contrat_id INTEGER NOT NULL UNIQUE REFERENCES contrats(id) ON DELETE CASCADE,
    date_generation TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    indemnite_licenciement DOUBLE PRECISION DEFAULT 0.0,
    indemnite_conges_payes DOUBLE PRECISION DEFAULT 0.0,
    indemnite_preavis DOUBLE PRECISION DEFAULT 0.0,
    indemnite_autre DOUBLE PRECISION DEFAULT 0.0,
    total DOUBLE PRECISION DEFAULT 0.0,
    statut VARCHAR(30) DEFAULT 'genere',
    commentaire TEXT DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 26. Table : constantes
CREATE TABLE constantes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL,
    description VARCHAR(255) NOT NULL,
    montant DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    unite VARCHAR(20) DEFAULT NULL,
    pays VARCHAR(50) NOT NULL DEFAULT 'CI',
    est_actif BOOLEAN DEFAULT TRUE,
    date_creation TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    date_modification TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_constante_code_pays UNIQUE (code, pays)
);
CREATE INDEX idx_constantes_code ON constantes (code);
CREATE INDEX idx_constantes_pays ON constantes (pays);

COMMENT ON TABLE constantes IS 'Table des constantes de paie par pays';
COMMENT ON COLUMN constantes.id IS 'Identifiant unique de la constante';
COMMENT ON COLUMN constantes.code IS 'Code unique de la constante (ex: SMIG, TAUX_AV)';
COMMENT ON COLUMN constantes.description IS 'Description détaillée de la constante';
COMMENT ON COLUMN constantes.montant IS 'Valeur numérique de la constante';
COMMENT ON COLUMN constantes.unite IS 'Unité de mesure (ex: FCFA, %, heures)';
COMMENT ON COLUMN constantes.pays IS 'Pays de référence (ex: CI pour Côte d''Ivoire)';
COMMENT ON COLUMN constantes.est_actif IS 'Indique si la constante est active ou non';
COMMENT ON COLUMN constantes.date_creation IS 'Date de création de l''enregistrement';
COMMENT ON COLUMN constantes.date_modification IS 'Date de dernière modification';

-- 27. Table : plan_paie
CREATE TABLE plan_paie (
    id SERIAL PRIMARY KEY,
    type VARCHAR(2) NOT NULL,
    code VARCHAR(20) NOT NULL,
    libelle VARCHAR(255) NOT NULL,
    mode_calcul VARCHAR(20) NOT NULL DEFAULT 'Sémi-auto',
    sens VARCHAR(10) NOT NULL DEFAULT 'Gain',
    masque_si_nul BOOLEAN DEFAULT FALSE,
    imprimable BOOLEAN DEFAULT TRUE,
    compte_debit VARCHAR(20) DEFAULT NULL,
    compte_credit VARCHAR(20) DEFAULT NULL,
    pays VARCHAR(50) NOT NULL DEFAULT 'CI',
    est_actif BOOLEAN DEFAULT TRUE,
    date_creation TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    date_modification TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_plan_paie_code_pays UNIQUE (code, pays)
);
CREATE INDEX idx_plan_paie_type ON plan_paie (type);
CREATE INDEX idx_plan_paie_code ON plan_paie (code);
CREATE INDEX idx_plan_paie_pays ON plan_paie (pays);

COMMENT ON TABLE plan_paie IS 'Plan comptable des postes de paie par pays';
COMMENT ON COLUMN plan_paie.id IS 'Identifiant unique du poste de paie';
COMMENT ON COLUMN plan_paie.type IS 'Type de poste (B=Brut, I=Impôt/Cotisation, NS=Non-Salarial, C=Charge patronale, A=Avantage)';
COMMENT ON COLUMN plan_paie.code IS 'Code du poste de paie (ex: 1001, 4011)';
COMMENT ON COLUMN plan_paie.libelle IS 'Libellé du poste de paie (ex: Salaire de base)';
COMMENT ON COLUMN plan_paie.mode_calcul IS 'Mode de calcul (Auto, Sémi-auto, Manuel)';
COMMENT ON COLUMN plan_paie.sens IS 'Sens du poste (Gain, Retenue)';
COMMENT ON COLUMN plan_paie.masque_si_nul IS 'Masquer le poste si le montant est nul';
COMMENT ON COLUMN plan_paie.imprimable IS 'Poste imprimable sur le bulletin de paie';
COMMENT ON COLUMN plan_paie.compte_debit IS 'Compte comptable de débit (ex: 661200)';
COMMENT ON COLUMN plan_paie.compte_credit IS 'Compte comptable de crédit (ex: 447210)';
COMMENT ON COLUMN plan_paie.pays IS 'Pays de référence (ex: CI pour Côte d''Ivoire)';
COMMENT ON COLUMN plan_paie.est_actif IS 'Indique si le poste est actif ou non';
COMMENT ON COLUMN plan_paie.date_creation IS 'Date de création de l''enregistrement';
COMMENT ON COLUMN plan_paie.date_modification IS 'Date de dernière modification';
