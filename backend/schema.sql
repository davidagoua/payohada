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
    salarie_id INTEGER DEFAULT NULL,
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
    siret VARCHAR(255) DEFAULT NULL,
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
    mode_calcul VARCHAR(10) DEFAULT 'brut',
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
    base DOUBLE PRECISION DEFAULT NULL,
    taux DOUBLE PRECISION DEFAULT NULL,
    est_persistant BOOLEAN DEFAULT FALSE,
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
    est_persistant BOOLEAN DEFAULT FALSE,
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

-- Foreign key for utilisateurs to salaries (added at end because salaries is created later)
ALTER TABLE utilisateurs ADD CONSTRAINT fk_utilisateurs_salarie FOREIGN KEY (salarie_id) REFERENCES salaries(id) ON DELETE CASCADE;

-- 28. Table : reclamations
CREATE TABLE reclamations (
    id SERIAL PRIMARY KEY,
    bulletin_id INTEGER NOT NULL REFERENCES bulletins_paies(id) ON DELETE CASCADE,
    salarie_id INTEGER NOT NULL REFERENCES salaries(id) ON DELETE CASCADE,
    sujet VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    statut VARCHAR(50) DEFAULT 'en_attente',
    commentaire_gestionnaire TEXT DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_reclamations_salarie ON reclamations (salarie_id);
CREATE INDEX idx_reclamations_bulletin ON reclamations (bulletin_id);


-- Table 1 : Les secteurs d'activité
CREATE TABLE secteurs (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(255) NOT NULL UNIQUE
);

-- Table 2 : Les postes, catégories et grilles salariales associées
CREATE TABLE postes_salaires (
    id SERIAL PRIMARY KEY,
    secteur_id INT NOT NULL REFERENCES secteurs(id) ON DELETE CASCADE,
    categorie_professionnelle VARCHAR(100) NOT NULL, -- ex: 'EMPLOYES', 'OUVRIERS', 'CADRES', 'CHAUFFEURS', etc.
    echelon_categorie VARCHAR(100) NOT NULL,        -- ex: '1 (SMIG)', 'M1', '2A', '1re classe'
    salaire_mensuel_fcfa INT,                       -- Salaire mensuel (peut être NULL pour certains ouvriers payés uniquement à l'heure)
    taux_horaire_fcfa NUMERIC(6, 2),                -- Taux horaire (facultatif, ex: 346.00)
    details_poste TEXT                              -- Pour préciser les spécificités (ex: "Véhicules Poids lourds de 3 à 5 T")
);

-- Index pour accélérer les recherches par secteur et par catégorie
CREATE INDEX idx_postes_secteur ON postes_salaires(secteur_id);
CREATE INDEX idx_postes_categorie ON postes_salaires(categorie_professionnelle);


-- On s'assure d'abord que la table des secteurs est propre et alimentée
INSERT INTO secteurs (nom) VALUES
('SECTEUR INDUSTRIEL'),
('INDUSTRIE DU BOIS'),
('INDUSTRIE TEXTILE'),
('INDUSTRIE DE TRANSFORMATION DE THON'),
('INDUSTRIE POLYGRAPHIQUE'),
('INDUSTRIE POLYGRAPHIQUE - IMPRIMERIE'),
('INDUSTRIE POLYGRAPHIQUE - BROCHURE - DORURE - RELIURE'),
('INDUSTRIE POLYGRAPHIQUE - PHOTOGRAVURE'),
('INDUSTRIE HOTELIERE'),
('INDUSTRIE TOURISTIQUE'),
('PRODUCTION AGRICOLE'),
('INDUSTRIE DU SUCRE'),
('AUXILIAIRES DU TRANSPORT'),
('ENTREPRISE DE BATIMENT, DES TRAVAUX PUBLICS ET ACTIVITES CONNEXES'),
('COMMERCE - DISTRIBUTION - NEGOCE ET PROFESSIONS LIBERALES'),
('SECTEUR MARITIME - NAVIGATION COTIERE'),
('SECTEUR MARITIME - ARMEMENT AU LONG COURS'),
('SECTEUR MARITIME - ARMEMENT AU CABOTAGE NATIONAL'),
('SECTEUR MARITIME - ARMEMENT AU CABOTAGE INTERNATIONAL'),
('SECTEUR MARITIME - KROOMEN'),
('SECTEUR MARITIME - MARINS PECHEURS'),
('BANQUES'),
('ASSURANCES'),
('ENTREPRISES PETROLIERES'),
('SECURITE PRIVEE'),
('NETTOYAGE - INSALUBRITE'),
('GENS DE MAISON')
ON CONFLICT (nom) DO NOTHING;

-- ============================================================================
-- SEEDING DES POSTES ET SALAIRES
-- ============================================================================

DO $$
DECLARE
    sec_id INT;
BEGIN

    -- ---------------------------------------------------------
    -[span_0](start_span)- 1. SECTEUR INDUSTRIEL[span_0](end_span)
    -- ---------------------------------------------------------
    SELECT id INTO sec_id FROM secteurs WHERE nom = 'SECTEUR INDUSTRIEL';

    -[span_1](start_span)- Employés[span_1](end_span)
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa, taux_horaire_fcfa) VALUES
    (sec_id, 'EMPLOYES', '1 (SMIG)', 75000, 346),
    (sec_id, 'EMPLOYES', '2', 76728, 410),
    (sec_id, 'EMPLOYES', '3', 77266, 446),
    (sec_id, 'EMPLOYES', '4', 82104, 474),
    (sec_id, 'EMPLOYES', '5', 97942, 565),
    (sec_id, 'EMPLOYES', '6', 111003, 640),
    (sec_id, 'EMPLOYES', '7 A', 112166, 647),
    (sec_id, 'EMPLOYES', '7 B', 120472, 695);

    -[span_2](start_span)- Chauffeurs[span_2](end_span)
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa, details_poste) VALUES
    (sec_id, 'CHAUFFEURS', 'Tourisme', 79889, 'Voitures de Tourisme'),
    (sec_id, 'CHAUFFEURS', 'PL 3-5 T', 73480, 'Véhicules Poids lourds de 3 à 5 T'),
    (sec_id, 'CHAUFFEURS', 'PL > 5 T', 83203, 'Véhicules Poids lourds de plus de 5 T'),
    (sec_id, 'CHAUFFEURS', 'Transport en commun', 76710, 'Véhicule de transport en commun');

    -[span_3](start_span)- Ouvriers[span_3](end_span)
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, taux_horaire_fcfa) VALUES
    (sec_id, 'OUVRIERS', '1 (SMIG)', 346),
    (sec_id, 'OUVRIERS', '2', 399),
    (sec_id, 'OUVRIERS', '3 A', 401),
    (sec_id, 'OUVRIERS', '3 B', 413),
    (sec_id, 'OUVRIERS', '4 A', 414),
    (sec_id, 'OUVRIERS', '4 B', 429),
    (sec_id, 'OUVRIERS', '5 A', 436),
    (sec_id, 'OUVRIERS', '5 B', 447),
    (sec_id, 'OUVRIERS', '6 A', 456),
    (sec_id, 'OUVRIERS', '6 B', 509);

    -[span_4](start_span)- Ingénieurs - Cadres assimilés[span_4](end_span)
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa) VALUES
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1A', 153699),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1B', 176935),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2A', 185838),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2B', 210906),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3A', 219239),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3B', 328791);

    -[span_5](start_span)- Agents de maîtrise[span_5](end_span)
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa, taux_horaire_fcfa) VALUES
    (sec_id, 'AGENTS DE MAITRISE', 'MNP', 105213, 607),
    (sec_id, 'AGENTS DE MAITRISE', 'M1', 119345, 689),
    (sec_id, 'AGENTS DE MAITRISE', 'M2', 127712, 737),
    (sec_id, 'AGENTS DE MAITRISE', 'M3', 152531, 880),
    (sec_id, 'AGENTS DE MAITRISE', 'M4', 165946, 957),
    (sec_id, 'AGENTS DE MAITRISE', 'M5', 179778, 1037);


    -- ---------------------------------------------------------
    -[span_6](start_span)- 2. INDUSTRIE DU BOIS[span_6](end_span)
    -- ---------------------------------------------------------
    SELECT id INTO sec_id FROM secteurs WHERE nom = 'INDUSTRIE DU BOIS';

    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa) VALUES
    -[span_7](start_span)- Cadres[span_7](end_span)
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1 A', 152984),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1 B', 176112),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2 A', 184974),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2 B', 209925),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3 A', 218219),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3 B', 327262),
    -[span_8](start_span)- Maîtrise[span_8](end_span)
    (sec_id, 'AGENTS DE MAITRISE', 'MNP', 104723),
    (sec_id, 'AGENTS DE MAITRISE', 'M1', 118790),
    (sec_id, 'AGENTS DE MAITRISE', 'M2', 127118),
    (sec_id, 'AGENTS DE MAITRISE', 'M3', 151822),
    (sec_id, 'AGENTS DE MAITRISE', 'M4', 165174),
    (sec_id, 'AGENTS DE MAITRISE', 'M5', 178941),
    -[span_9](start_span)- Employés[span_9](end_span)
    (sec_id, 'EMPLOYES', '1 (SMIG)', 75000),
    (sec_id, 'EMPLOYES', '2', 74981),
    (sec_id, 'EMPLOYES', '3', 76196),
    (sec_id, 'EMPLOYES', '4', 81721),
    (sec_id, 'EMPLOYES', '5', 97486),
    (sec_id, 'EMPLOYES', '6', 110487),
    (sec_id, 'EMPLOYES', '7 A', 111644),
    (sec_id, 'EMPLOYES', '7 B', 119912);

    -[span_10](start_span)- Chauffeurs[span_10](end_span)
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa, taux_horaire_fcfa, details_poste) VALUES
    (sec_id, 'CHAUFFEURS', 'Tourisme', 69564, 401, 'Voitures de Tourisme'),
    (sec_id, 'CHAUFFEURS', 'PL 3-5 T', 73138, 422, 'Véhicules Poids lourds de 3 à 5 T'),
    (sec_id, 'CHAUFFEURS', 'PL > 5 T', 75798, 437, 'Véhicules Poids lourds de plus de 5 T'),
    (sec_id, 'CHAUFFEURS', 'Transport en commun', 76354, 441, 'Véhicule de transport en commun');

    -[span_11](start_span)- Ouvriers[span_11](end_span)
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, taux_horaire_fcfa) VALUES
    (sec_id, 'OUVRIERS', '1 (SMIG)', 346),
    (sec_id, 'OUVRIERS', '2', 390),
    (sec_id, 'OUVRIERS', '3 A', 391),
    (sec_id, 'OUVRIERS', '3 B', 400),
    (sec_id, 'OUVRIERS', '4 A', 401),
    (sec_id, 'OUVRIERS', '4 B', 422),
    (sec_id, 'OUVRIERS', '5 A', 432),
    (sec_id, 'OUVRIERS', '5 B', 447),
    (sec_id, 'OUVRIERS', '6 A', 459),
    (sec_id, 'OUVRIERS', '6 B', 511);


    -- ---------------------------------------------------------
    -[span_12](start_span)- 3. INDUSTRIE TEXTILE[span_12](end_span)
    -- ---------------------------------------------------------
    SELECT id INTO sec_id FROM secteurs WHERE nom = 'INDUSTRIE TEXTILE';

    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa) VALUES
    -[span_13](start_span)- Cadres[span_13](end_span)
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1 A', 147266),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1 B', 169529),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2 A', 178059),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2 B', 202078),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3 A', 210061),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3 B', 315027),
    -[span_14](start_span)- Maîtrise[span_14](end_span)
    (sec_id, 'AGENTS DE MAITRISE', 'MNP', 101787),
    (sec_id, 'AGENTS DE MAITRISE', 'M1', 115460),
    (sec_id, 'AGENTS DE MAITRISE', 'M2', 123554),
    (sec_id, 'AGENTS DE MAITRISE', 'M3', 147565),
    (sec_id, 'AGENTS DE MAITRISE', 'M4', 160543),
    (sec_id, 'AGENTS DE MAITRISE', 'M5', 173924),
    -[span_15](start_span)- Employés[span_15](end_span)
    (sec_id, 'EMPLOYES', '1 (SMIG)', 75000),
    (sec_id, 'EMPLOYES', '2', 74280),
    (sec_id, 'EMPLOYES', '3', 75483),
    (sec_id, 'EMPLOYES', '4', 80958),
    (sec_id, 'EMPLOYES', '5', 96576),
    (sec_id, 'EMPLOYES', '6', 109455),
    (sec_id, 'EMPLOYES', '7 A', 110601),
    (sec_id, 'EMPLOYES', '7 B', 118791),
    -[span_16](start_span)- Chauffeurs[span_16](end_span)
    (sec_id, 'CHAUFFEURS', 'Tourisme', 68914),
    (sec_id, 'CHAUFFEURS', 'PL 3-5 T', 72454),
    (sec_id, 'CHAUFFEURS', 'PL > 5 T', 75090),
    (sec_id, 'CHAUFFEURS', 'Transport en commun', 75640);

    -[span_17](start_span)- Ouvriers[span_17](end_span)
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, taux_horaire_fcfa) VALUES
    (sec_id, 'OUVRIERS', '1 (SMIG)', 346),
    (sec_id, 'OUVRIERS', '2', 386),
    (sec_id, 'OUVRIERS', '3 A', 387),
    (sec_id, 'OUVRIERS', '3 B', 396),
    (sec_id, 'OUVRIERS', '4 A', 397),
    (sec_id, 'OUVRIERS', '4 B', 418),
    (sec_id, 'OUVRIERS', '5 A', 428),
    (sec_id, 'OUVRIERS', '5 B', 443),
    (sec_id, 'OUVRIERS', '6 A', 455),
    (sec_id, 'OUVRIERS', '6 B', 507);


    -- ---------------------------------------------------------
    -[span_18](start_span)- 4. INDUSTRIE DE TRANSFORMATION DE THON[span_18](end_span)
    -- ---------------------------------------------------------
    SELECT id INTO sec_id FROM secteurs WHERE nom = 'INDUSTRIE DE TRANSFORMATION DE THON';

    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa) VALUES
    -[span_19](start_span)- Cadres[span_19](end_span)
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1 A', 150124),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1 B', 172821),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2 A', 181516),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2 B', 206001),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3 A', 201140),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3 B', 321144);

    -[span_20](start_span)- Maîtrise[span_20](end_span)
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa, taux_horaire_fcfa) VALUES
    (sec_id, 'AGENTS DE MAITRISE', 'MNP', 102765, 593),
    (sec_id, 'AGENTS DE MAITRISE', 'M1', 116570, 673),
    (sec_id, 'AGENTS DE MAITRISE', 'M2', 124742, 720),
    (sec_id, 'AGENTS DE MAITRISE', 'M3', 148984, 860),
    (sec_id, 'AGENTS DE MAITRISE', 'M4', 162087, 935),
    (sec_id, 'AGENTS DE MAITRISE', 'M5', 175596, 1013);

    -[span_21](start_span)- Employés[span_21](end_span)
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa) VALUES
    (sec_id, 'EMPLOYES', '1 (SMIG)', 75000),
    (sec_id, 'EMPLOYES', '2', 73579),
    (sec_id, 'EMPLOYES', '3', 74772),
    (sec_id, 'EMPLOYES', '4', 80194),
    (sec_id, 'EMPLOYES', '5', 95664),
    (sec_id, 'EMPLOYES', '6', 108422),
    (sec_id, 'EMPLOYES', '7 A', 109557),
    (sec_id, 'EMPLOYES', '7 B', 117670);

    -[span_22](start_span)- Chauffeurs[span_22](end_span)
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa, taux_horaire_fcfa, details_poste) VALUES
    (sec_id, 'CHAUFFEURS', 'Tourisme', 68264, 365, 'Voitures de Tourisme'),
    (sec_id, 'CHAUFFEURS', 'PL 3-5 T', 71771, 383, 'Véhicules Poids lourds de 3 à 5 T'),
    (sec_id, 'CHAUFFEURS', 'PL > 5 T', 74382, 397, 'Véhicules Poids lourds de plus de 5 T'),
    (sec_id, 'CHAUFFEURS', 'Transport en commun', 74927, 400, 'Véhicule de transport en commun');

    -[span_23](start_span)- Ouvriers[span_23](end_span)
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, taux_horaire_fcfa) VALUES
    (sec_id, 'OUVRIERS', '1 (SMIG)', 346),
    (sec_id, 'OUVRIERS', '2', 382),
    (sec_id, 'OUVRIERS', '3 A', 383),
    (sec_id, 'OUVRIERS', '3 B', 392),
    (sec_id, 'OUVRIERS', '4 A', 393),
    (sec_id, 'OUVRIERS', '4 B', 414),
    (sec_id, 'OUVRIERS', '5 A', 424),
    (sec_id, 'OUVRIERS', '5 B', 438),
    (sec_id, 'OUVRIERS', '6 A', 450),
    (sec_id, 'OUVRIERS', '6 B', 501);


    -- ---------------------------------------------------------
    -[span_24](start_span)- 5. BANQUES[span_24](end_span)
    -- ---------------------------------------------------------
    SELECT id INTO sec_id FROM secteurs WHERE nom = 'BANQUES';

    -[span_25](start_span)- Employés[span_25](end_span)
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa) VALUES
    (sec_id, 'EMPLOYES', '1re classe', 46364),
    (sec_id, 'EMPLOYES', '2me classe', 61745),
    (sec_id, 'EMPLOYES', '3me classe', 67250),
    (sec_id, 'EMPLOYES', '4me classe', 76662),
    (sec_id, 'EMPLOYES', '5me classe', 95493),
    (sec_id, 'EMPLOYES', '6me classe', 106019),
    (sec_id, 'EMPLOYES', '7me classe', 113146);

    -[span_26](start_span)- Agents de maîtrise[span_26](end_span)
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa) VALUES
    (sec_id, 'AGENTS DE MAITRISE - CADRES ASSIMILES', '1re classe', 113220),
    (sec_id, 'AGENTS DE MAITRISE - CADRES ASSIMILES', '2me classe', 113547),
    (sec_id, 'AGENTS DE MAITRISE - CADRES ASSIMILES', '3me classe', 121172),
    (sec_id, 'AGENTS DE MAITRISE - CADRES ASSIMILES', '4me classe', 123948),
    (sec_id, 'AGENTS DE MAITRISE - CADRES ASSIMILES', '5me classe 1', 1249872), -- Noté "1 249872 F" dans le doc
    (sec_id, 'AGENTS DE MAITRISE - CADRES ASSIMILES', '5me classe 2', 359872),
    (sec_id, 'AGENTS DE MAITRISE - CADRES ASSIMILES', '6me classe', 154898),
    (sec_id, 'AGENTS DE MAITRISE - CADRES ASSIMILES', '7me classe', 176227),
    (sec_id, 'AGENTS DE MAITRISE - CADRES ASSIMILES', '8me classe', 199410);


    -- ---------------------------------------------------------
    -[span_27](start_span)- 6. GENS DE MAISON[span_27](end_span)
    -- ---------------------------------------------------------
    SELECT id INTO sec_id FROM secteurs WHERE nom = 'GENS DE MAISON';

    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa, details_poste) VALUES
    [span_28](start_span)(sec_id, 'GENS DE MAISON', '1re Catégorie', 75000, 'Employé de maison sans spécialité, petit boy, petite bonne, aide-cuisinier[span_28](end_span)'),
    [span_29](start_span)(sec_id, 'GENS DE MAISON', '2me Catégorie', 73600, 'Boy ou Bonne n''assurant qu''une partie des travaux de la maison sans lavage de linge[span_29](end_span)'),
    (sec_id, 'GENS DE MAISON', '3me Catégorie', 73322, 'Boy ou Bonne chargé(e) [span_30](start_span)d''exécuter l''ensemble des travaux courants et justifiant de plus de 2 ans de pratique[span_30](end_span)'),
    [span_31](start_span)(sec_id, 'GENS DE MAISON', '4me Catégorie', 75004, 'Boy cuisinier ou bonne cuisinière assurant l''ensemble des travaux d''intérieur y compris la cuisine[span_31](end_span)'),
    (sec_id, 'GENS DE MAISON', '5me Catégorie', 76965, 'Cuisinier ou Cuisinière qualifié(e) [span_32](start_span)sachant faire la pâtisserie[span_32](end_span)'),
    (sec_id, 'GENS DE MAISON', '6me Catégorie', 79931, 'Cuisinier ou Cuisinière qualifié(e) [span_33](start_span)sachant faire la pâtisserie ou la charcuterie[span_33](end_span)'),
    [span_34](start_span)(sec_id, 'GENS DE MAISON', '7me Catégorie', 83250, 'Maître d''hôtel[span_34](end_span)');

END $$;

-- 8. Alter tables for Secteur and Poste relationships
ALTER TABLE etablissements ADD COLUMN IF NOT EXISTS secteur_id INTEGER REFERENCES secteurs(id) ON DELETE SET NULL;
ALTER TABLE contrats ADD COLUMN IF NOT EXISTS poste_salaire_id INTEGER REFERENCES postes_salaires(id) ON DELETE SET NULL;




