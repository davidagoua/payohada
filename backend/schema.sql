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
    situation_matrimoniale VARCHAR(50) DEFAULT NULL,
    enfants_charge INTEGER DEFAULT 0,
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
    -- NOTE : `pret_id` est ajouté par la section MIGRATION INCREMENTALE, car il
    -- référence `prets_salaries` qui est créée plus loin dans ce fichier.
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
-- Bloc idempotent : la contrainte peut déjà exister sur une base migrée.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_utilisateurs_salarie'
    ) THEN
        ALTER TABLE utilisateurs
            ADD CONSTRAINT fk_utilisateurs_salarie
            FOREIGN KEY (salarie_id) REFERENCES salaries(id) ON DELETE CASCADE;
    END IF;
END $$;

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
    -- 1. SECTEUR INDUSTRIEL
    -- ---------------------------------------------------------
    SELECT id INTO sec_id FROM secteurs WHERE nom = 'SECTEUR INDUSTRIEL';

    -- Employés
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa, taux_horaire_fcfa) VALUES
    (sec_id, 'EMPLOYES', '1 (SMIG)', 75000, 346),
    (sec_id, 'EMPLOYES', '2', 76728, 410),
    (sec_id, 'EMPLOYES', '3', 77266, 446),
    (sec_id, 'EMPLOYES', '4', 82104, 474),
    (sec_id, 'EMPLOYES', '5', 97942, 565),
    (sec_id, 'EMPLOYES', '6', 111003, 640),
    (sec_id, 'EMPLOYES', '7 A', 112166, 647),
    (sec_id, 'EMPLOYES', '7 B', 120472, 695);

    -- Chauffeurs
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa, details_poste) VALUES
    (sec_id, 'CHAUFFEURS', 'Tourisme', 79889, 'Voitures de Tourisme'),
    (sec_id, 'CHAUFFEURS', 'PL 3-5 T', 73480, 'Véhicules Poids lourds de 3 à 5 T'),
    (sec_id, 'CHAUFFEURS', 'PL > 5 T', 83203, 'Véhicules Poids lourds de plus de 5 T'),
    (sec_id, 'CHAUFFEURS', 'Transport en commun', 76710, 'Véhicule de transport en commun');

    -- Ouvriers
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

    -- Ingénieurs - Cadres assimilés
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa) VALUES
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1A', 153699),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1B', 176935),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2A', 185838),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2B', 210906),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3A', 219239),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3B', 328791);

    -- Agents de maîtrise
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa, taux_horaire_fcfa) VALUES
    (sec_id, 'AGENTS DE MAITRISE', 'MNP', 105213, 607),
    (sec_id, 'AGENTS DE MAITRISE', 'M1', 119345, 689),
    (sec_id, 'AGENTS DE MAITRISE', 'M2', 127712, 737),
    (sec_id, 'AGENTS DE MAITRISE', 'M3', 152531, 880),
    (sec_id, 'AGENTS DE MAITRISE', 'M4', 165946, 957),
    (sec_id, 'AGENTS DE MAITRISE', 'M5', 179778, 1037);


    -- ---------------------------------------------------------
    -- 2. INDUSTRIE DU BOIS
    -- ---------------------------------------------------------
    SELECT id INTO sec_id FROM secteurs WHERE nom = 'INDUSTRIE DU BOIS';

    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa) VALUES
    -- Cadres
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1 A', 152984),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1 B', 176112),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2 A', 184974),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2 B', 209925),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3 A', 218219),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3 B', 327262),
    -- Maîtrise
    (sec_id, 'AGENTS DE MAITRISE', 'MNP', 104723),
    (sec_id, 'AGENTS DE MAITRISE', 'M1', 118790),
    (sec_id, 'AGENTS DE MAITRISE', 'M2', 127118),
    (sec_id, 'AGENTS DE MAITRISE', 'M3', 151822),
    (sec_id, 'AGENTS DE MAITRISE', 'M4', 165174),
    (sec_id, 'AGENTS DE MAITRISE', 'M5', 178941),
    -- Employés
    (sec_id, 'EMPLOYES', '1 (SMIG)', 75000),
    (sec_id, 'EMPLOYES', '2', 74981),
    (sec_id, 'EMPLOYES', '3', 76196),
    (sec_id, 'EMPLOYES', '4', 81721),
    (sec_id, 'EMPLOYES', '5', 97486),
    (sec_id, 'EMPLOYES', '6', 110487),
    (sec_id, 'EMPLOYES', '7 A', 111644),
    (sec_id, 'EMPLOYES', '7 B', 119912);

    -- Chauffeurs
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa, taux_horaire_fcfa, details_poste) VALUES
    (sec_id, 'CHAUFFEURS', 'Tourisme', 69564, 401, 'Voitures de Tourisme'),
    (sec_id, 'CHAUFFEURS', 'PL 3-5 T', 73138, 422, 'Véhicules Poids lourds de 3 à 5 T'),
    (sec_id, 'CHAUFFEURS', 'PL > 5 T', 75798, 437, 'Véhicules Poids lourds de plus de 5 T'),
    (sec_id, 'CHAUFFEURS', 'Transport en commun', 76354, 441, 'Véhicule de transport en commun');

    -- Ouvriers
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
    -- 3. INDUSTRIE TEXTILE
    -- ---------------------------------------------------------
    SELECT id INTO sec_id FROM secteurs WHERE nom = 'INDUSTRIE TEXTILE';

    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa) VALUES
    -- Cadres
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1 A', 147266),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1 B', 169529),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2 A', 178059),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2 B', 202078),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3 A', 210061),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3 B', 315027),
    -- Maîtrise
    (sec_id, 'AGENTS DE MAITRISE', 'MNP', 101787),
    (sec_id, 'AGENTS DE MAITRISE', 'M1', 115460),
    (sec_id, 'AGENTS DE MAITRISE', 'M2', 123554),
    (sec_id, 'AGENTS DE MAITRISE', 'M3', 147565),
    (sec_id, 'AGENTS DE MAITRISE', 'M4', 160543),
    (sec_id, 'AGENTS DE MAITRISE', 'M5', 173924),
    -- Employés
    (sec_id, 'EMPLOYES', '1 (SMIG)', 75000),
    (sec_id, 'EMPLOYES', '2', 74280),
    (sec_id, 'EMPLOYES', '3', 75483),
    (sec_id, 'EMPLOYES', '4', 80958),
    (sec_id, 'EMPLOYES', '5', 96576),
    (sec_id, 'EMPLOYES', '6', 109455),
    (sec_id, 'EMPLOYES', '7 A', 110601),
    (sec_id, 'EMPLOYES', '7 B', 118791),
    -- Chauffeurs
    (sec_id, 'CHAUFFEURS', 'Tourisme', 68914),
    (sec_id, 'CHAUFFEURS', 'PL 3-5 T', 72454),
    (sec_id, 'CHAUFFEURS', 'PL > 5 T', 75090),
    (sec_id, 'CHAUFFEURS', 'Transport en commun', 75640);

    -- Ouvriers
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
    -- 4. INDUSTRIE DE TRANSFORMATION DE THON
    -- ---------------------------------------------------------
    SELECT id INTO sec_id FROM secteurs WHERE nom = 'INDUSTRIE DE TRANSFORMATION DE THON';

    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa) VALUES
    -- Cadres
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1 A', 150124),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '1 B', 172821),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2 A', 181516),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '2 B', 206001),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3 A', 201140),
    (sec_id, 'INGENIEURS - CADRES ASSIMILES', '3 B', 321144);

    -- Maîtrise
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa, taux_horaire_fcfa) VALUES
    (sec_id, 'AGENTS DE MAITRISE', 'MNP', 102765, 593),
    (sec_id, 'AGENTS DE MAITRISE', 'M1', 116570, 673),
    (sec_id, 'AGENTS DE MAITRISE', 'M2', 124742, 720),
    (sec_id, 'AGENTS DE MAITRISE', 'M3', 148984, 860),
    (sec_id, 'AGENTS DE MAITRISE', 'M4', 162087, 935),
    (sec_id, 'AGENTS DE MAITRISE', 'M5', 175596, 1013);

    -- Employés
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa) VALUES
    (sec_id, 'EMPLOYES', '1 (SMIG)', 75000),
    (sec_id, 'EMPLOYES', '2', 73579),
    (sec_id, 'EMPLOYES', '3', 74772),
    (sec_id, 'EMPLOYES', '4', 80194),
    (sec_id, 'EMPLOYES', '5', 95664),
    (sec_id, 'EMPLOYES', '6', 108422),
    (sec_id, 'EMPLOYES', '7 A', 109557),
    (sec_id, 'EMPLOYES', '7 B', 117670);

    -- Chauffeurs
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa, taux_horaire_fcfa, details_poste) VALUES
    (sec_id, 'CHAUFFEURS', 'Tourisme', 68264, 365, 'Voitures de Tourisme'),
    (sec_id, 'CHAUFFEURS', 'PL 3-5 T', 71771, 383, 'Véhicules Poids lourds de 3 à 5 T'),
    (sec_id, 'CHAUFFEURS', 'PL > 5 T', 74382, 397, 'Véhicules Poids lourds de plus de 5 T'),
    (sec_id, 'CHAUFFEURS', 'Transport en commun', 74927, 400, 'Véhicule de transport en commun');

    -- Ouvriers
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
    -- 5. BANQUES
    -- ---------------------------------------------------------
    SELECT id INTO sec_id FROM secteurs WHERE nom = 'BANQUES';

    -- Employés
    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa) VALUES
    (sec_id, 'EMPLOYES', '1re classe', 46364),
    (sec_id, 'EMPLOYES', '2me classe', 61745),
    (sec_id, 'EMPLOYES', '3me classe', 67250),
    (sec_id, 'EMPLOYES', '4me classe', 76662),
    (sec_id, 'EMPLOYES', '5me classe', 95493),
    (sec_id, 'EMPLOYES', '6me classe', 106019),
    (sec_id, 'EMPLOYES', '7me classe', 113146);

    -- Agents de maîtrise
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
    -- 6. GENS DE MAISON
    -- ---------------------------------------------------------
    SELECT id INTO sec_id FROM secteurs WHERE nom = 'GENS DE MAISON';

    INSERT INTO postes_salaires (secteur_id, categorie_professionnelle, echelon_categorie, salaire_mensuel_fcfa, details_poste) VALUES
    (sec_id, 'GENS DE MAISON', '1re Catégorie', 75000, 'Employé de maison sans spécialité, petit boy, petite bonne, aide-cuisinier'),
    (sec_id, 'GENS DE MAISON', '2me Catégorie', 73600, 'Boy ou Bonne n''assurant qu''une partie des travaux de la maison sans lavage de linge'),
    (sec_id, 'GENS DE MAISON', '3me Catégorie', 73322, 'Boy ou Bonne chargé(e) d''exécuter l''ensemble des travaux courants et justifiant de plus de 2 ans de pratique'),
    (sec_id, 'GENS DE MAISON', '4me Catégorie', 75004, 'Boy cuisinier ou bonne cuisinière assurant l''ensemble des travaux d''intérieur y compris la cuisine'),
    (sec_id, 'GENS DE MAISON', '5me Catégorie', 76965, 'Cuisinier ou Cuisinière qualifié(e) sachant faire la pâtisserie'),
    (sec_id, 'GENS DE MAISON', '6me Catégorie', 79931, 'Cuisinier ou Cuisinière qualifié(e) sachant faire la pâtisserie ou la charcuterie'),
    (sec_id, 'GENS DE MAISON', '7me Catégorie', 83250, 'Maître d''hôtel');

END $$;

-- 8. Alter tables for Secteur and Poste relationships
ALTER TABLE etablissements ADD COLUMN IF NOT EXISTS secteur_id INTEGER REFERENCES secteurs(id) ON DELETE SET NULL;
ALTER TABLE contrats ADD COLUMN IF NOT EXISTS poste_salaire_id INTEGER REFERENCES postes_salaires(id) ON DELETE SET NULL;


ALTER TABLE etablissements
    -- 1. Identification supplémentaire
    ADD COLUMN sigle VARCHAR(50) DEFAULT NULL,
    ADD COLUMN numero_rccm VARCHAR(100) DEFAULT NULL,
    ADD COLUMN date_creation DATE DEFAULT NULL,

    -- 2. Adresse physique détaillée
    ADD COLUMN adresse_pays VARCHAR(100) DEFAULT 'COTE D''IVOIRE',
    ADD COLUMN adresse_commune VARCHAR(100) DEFAULT NULL,
    ADD COLUMN adresse_quartier VARCHAR(100) DEFAULT NULL,
    ADD COLUMN adresse_rue VARCHAR(150) DEFAULT NULL,
    ADD COLUMN adresse_ilot VARCHAR(50) DEFAULT NULL,
    ADD COLUMN adresse_lot VARCHAR(50) DEFAULT NULL,
    ADD COLUMN adresse_localisation TEXT DEFAULT NULL,

    -- 3. Contacts
    ADD COLUMN adresse_postale VARCHAR(255) DEFAULT NULL,
    ADD COLUMN telephone VARCHAR(100) DEFAULT NULL,
    ADD COLUMN fax VARCHAR(50) DEFAULT NULL,
    ADD COLUMN email VARCHAR(150) DEFAULT NULL,
    ADD COLUMN site_web VARCHAR(255) DEFAULT NULL,

    -- 4. Edition de paie
    ADD COLUMN adresse_bulletin_paie TEXT DEFAULT NULL,

    -- 5. Paramètres de paie & RH
    ADD COLUMN mode_decompte_anciennete VARCHAR(100) DEFAULT 'Date anniversaire de la date d''entrée',
    ADD COLUMN conges_periode_reference_mois INTEGER DEFAULT 12,
    ADD COLUMN conges_mode_gestion_solde VARCHAR(50) DEFAULT 'Jours calendaires',

    -- 6. Configuration de la génération des matricules salariés
    ADD COLUMN matricule_generation_auto BOOLEAN DEFAULT TRUE,
    ADD COLUMN matricule_prefixe VARCHAR(20) DEFAULT NULL,
    ADD COLUMN matricule_suffixe VARCHAR(20) DEFAULT NULL,
    ADD COLUMN matricule_numero_sequentiel VARCHAR(20) DEFAULT '001';


-- ==============================================================================
-- NOUVELLES TABLES POUR L'ONGLET RH (INFORMATION SALARIÉ)
-- ==============================================================================

-- 29. Table : entretiens_evaluations
CREATE TABLE entretiens_evaluations (
    id SERIAL PRIMARY KEY,
    salarie_id INTEGER NOT NULL REFERENCES salaries(id) ON DELETE CASCADE,
    date_entretien DATE NOT NULL,
    nom_evaluateur VARCHAR(100) NOT NULL,
    note_globale DOUBLE PRECISION DEFAULT NULL,
    commentaires TEXT DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_entretiens_evaluations_salarie ON entretiens_evaluations (salarie_id);

-- 30. Table : visites_medicales
CREATE TABLE visites_medicales (
    id SERIAL PRIMARY KEY,
    salarie_id INTEGER NOT NULL REFERENCES salaries(id) ON DELETE CASCADE,
    date_visite DATE NOT NULL,
    type_visite VARCHAR(50) NOT NULL,
    aptitude VARCHAR(50) NOT NULL,
    prochaine_visite DATE DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_visites_medicales_salarie ON visites_medicales (salarie_id);

-- 31. Table : suivi_formations
CREATE TABLE suivi_formations (
    id SERIAL PRIMARY KEY,
    salarie_id INTEGER NOT NULL REFERENCES salaries(id) ON DELETE CASCADE,
    intitule_formation VARCHAR(200) NOT NULL,
    organisme VARCHAR(200) NOT NULL,
    date_debut DATE NOT NULL,
    date_fin DATE NOT NULL,
    statut_formation VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_suivi_formations_salarie ON suivi_formations (salarie_id);

-- 32. Table : salaries_absences
CREATE TABLE salaries_absences (
    id SERIAL PRIMARY KEY,
    salarie_id INTEGER NOT NULL REFERENCES salaries(id) ON DELETE CASCADE,
    type_absence VARCHAR(100) NOT NULL,
    date_debut_absence DATE NOT NULL,
    date_fin_absence DATE NOT NULL,
    justificatif_fourni BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_salaries_absences_salarie ON salaries_absences (salarie_id);

-- 33. Table : prets_salaries
CREATE TABLE prets_salaries (
    id SERIAL PRIMARY KEY,
    salarie_id INTEGER NOT NULL REFERENCES salaries(id) ON DELETE CASCADE,
    montant_pret DOUBLE PRECISION NOT NULL,
    date_deblocage DATE NOT NULL,
    montant_mensualite DOUBLE PRECISION NOT NULL,
    reste_a_rembourser DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_prets_salaries_salarie ON prets_salaries (salarie_id);

-- 34. Table : salaries_contrats_info
CREATE TABLE salaries_contrats_info (
    id SERIAL PRIMARY KEY,
    salarie_id INTEGER NOT NULL REFERENCES salaries(id) ON DELETE CASCADE,
    type_contrat VARCHAR(50) NOT NULL,
    date_embauche DATE NOT NULL,
    date_fin_contrat DATE DEFAULT NULL,
    fin_periode_essai DATE DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_salaries_contrats_info_salarie ON salaries_contrats_info (salarie_id);

-- 35. Table : salaries_services
CREATE TABLE salaries_services (
    id SERIAL PRIMARY KEY,
    salarie_id INTEGER NOT NULL REFERENCES salaries(id) ON DELETE CASCADE,
    departement VARCHAR(100) NOT NULL,
    poste_occupe VARCHAR(100) NOT NULL,
    manager VARCHAR(100) NOT NULL,
    dotation_materiel TEXT DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_salaries_services_salarie ON salaries_services (salarie_id);

-- 36. Table : archivages_documents
CREATE TABLE archivages_documents (
    id SERIAL PRIMARY KEY,
    salarie_id INTEGER NOT NULL REFERENCES salaries(id) ON DELETE CASCADE,
    type_document VARCHAR(100) NOT NULL,
    fichier_joint VARCHAR(255) DEFAULT NULL,
    date_ajout DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_archivages_documents_salarie ON archivages_documents (salarie_id);

-- 37. Table : departements
CREATE TABLE departements (
    id SERIAL PRIMARY KEY,
    dossier_id INTEGER NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
    nom VARCHAR(100) NOT NULL,
    code VARCHAR(50) DEFAULT NULL,
    description TEXT DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_departements_dossier ON departements (dossier_id);

-- ==============================================================================
-- MIGRATION INCREMENTALE : ARCHITECTURE 3 PLATEFORMES (CABINET / CLIENT / SALARIÉ)
-- ==============================================================================

-- 1. Extension de la table utilisateurs pour le multi-rôle et l'affectation entreprise
ALTER TABLE utilisateurs 
    ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'cabinet' NOT NULL,
    ADD COLUMN IF NOT EXISTS dossier_id INTEGER DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS cabinet_nom VARCHAR(200) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS cabinet_telephone VARCHAR(30) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS cabinet_ville VARCHAR(100) DEFAULT NULL;

-- Clé étrangère vers le dossier d'entreprise client (bloc idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_utilisateurs_dossier'
    ) THEN
        ALTER TABLE utilisateurs
            ADD CONSTRAINT fk_utilisateurs_dossier
            FOREIGN KEY (dossier_id) REFERENCES dossiers(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Index pour optimiser les filtres par rôle et dossier
CREATE INDEX IF NOT EXISTS idx_utilisateurs_role ON utilisateurs (role);
CREATE INDEX IF NOT EXISTS idx_utilisateurs_dossier ON utilisateurs (dossier_id);

-- 2. Table : periodes_paie (Suivi des variables et transmission mensuelle par dossier)
CREATE TABLE IF NOT EXISTS periodes_paie (
    id SERIAL PRIMARY KEY,
    dossier_id INTEGER NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
    mois INTEGER NOT NULL,
    annee VARCHAR(4) NOT NULL,
    statut VARCHAR(50) DEFAULT 'saisie_en_cours',
    date_transmission TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    transmis_par_id INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL,
    notes_client TEXT DEFAULT NULL,
    notes_cabinet TEXT DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_periodes_paie_dossier_periode UNIQUE (dossier_id, annee, mois)
);
CREATE INDEX IF NOT EXISTS idx_periodes_paie_dossier ON periodes_paie (dossier_id);
CREATE INDEX IF NOT EXISTS idx_periodes_paie_dossier_periode ON periodes_paie (dossier_id, annee, mois);

-- ==============================================================================
-- MIGRATION INCREMENTALE : CORRECTIFS D'AUDIT SÉCURITÉ & INTÉGRITÉ
-- ==============================================================================
-- Cette section est IDEMPOTENTE : elle peut être rejouée sans risque sur la
-- base PostgreSQL / Supabase existante. Elle doit être appliquée AVANT de
-- déployer le code correspondant.
-- ==============================================================================

-- 0. Lignes de bulletin : rattachement d'une retenue à un prêt salarié.
--    Colonne déplacée ici car elle référence `prets_salaries`, créée plus haut
--    dans la section « NOUVELLES TABLES POUR L'ONGLET RH ». Corrige l'échec
--    « relation "prets_salaries" does not exist » lors d'une installation neuve.
ALTER TABLE lignes_bulletins_paies
    ADD COLUMN IF NOT EXISTS pret_id INTEGER REFERENCES prets_salaries(id) ON DELETE SET NULL;

-- 1. Utilisateurs : obligation de remplacer le mot de passe provisoire.
--    Remplace la backdoor « Payohada@123 » et supprime la notion de mot de
--    passe partagé : un compte dont hashed_password IS NULL ne peut plus se
--    connecter et doit être recréé (API ou backend/create_admin.py).
ALTER TABLE utilisateurs
    ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN utilisateurs.must_change_password
    IS 'Le mot de passe provisoire doit être remplacé à la première connexion';

-- 2. Horaires : défauts alignés sur le droit du travail ivoirien / UEMOA
--    (40 heures par semaine, soit 173,33 heures par mois).
--    ⚠️ SET DEFAULT n'affecte QUE les nouvelles lignes. Les contrats existants
--    conservent leur valeur enregistrée (35 h / 151,67 h) : leur reprise est une
--    décision de gestion, à traiter contrat par contrat.
ALTER TABLE horaires ALTER COLUMN horaire_travail SET DEFAULT 173.33;
ALTER TABLE horaires ALTER COLUMN horaire_hebdo SET DEFAULT 40.0;

COMMENT ON COLUMN horaires.horaire_travail IS 'Heures mensuelles légales (173.33 pour 40 h/semaine)';
COMMENT ON COLUMN horaires.horaire_hebdo IS 'Heures hebdomadaires légales (40 h en Côte d''Ivoire)';

-- 3. Plan de paie : ajout des majorations d'heures supplémentaires 75 % et 100 %.
--    Elles étaient proposées dans l'interface de saisie mais absentes du
--    référentiel : le moteur les payait donc au taux de base.
INSERT INTO plan_paie (type, code, libelle, mode_calcul, sens, pays)
SELECT 'B', 'HS_75', 'Heures supplémentaires majorées à 75%', 'Sémi-auto', 'Gain', 'CI'
WHERE NOT EXISTS (
    SELECT 1 FROM plan_paie WHERE code = 'HS_75' AND pays = 'CI'
);

INSERT INTO plan_paie (type, code, libelle, mode_calcul, sens, pays)
SELECT 'B', 'HS_100', 'Heures supplémentaires majorées à 100%', 'Sémi-auto', 'Gain', 'CI'
WHERE NOT EXISTS (
    SELECT 1 FROM plan_paie WHERE code = 'HS_100' AND pays = 'CI'
);

-- 4. Constantes CNPS : plafonds Prestations Familiales / Accident du Travail /
--    Maternité portés de 75 000 à 70 000 FCFA par mois.
--
--    ⚠️ CORRECTION SOUMISE À VALIDATION MÉTIER ⚠️
--    Cette mise à jour MODIFIE le montant des cotisations patronales calculées.
--    Le plafond usuel en Côte d'Ivoire est de 70 000 FCFA/mois, mais il doit
--    être confirmé contre les textes officiels (CGI / CNPS) en vigueur avant
--    d'être appliqué. Décommenter la requête ci-dessous après validation :
--
-- UPDATE constantes
--    SET montant = 70000.00,
--        date_modification = CURRENT_TIMESTAMP
--  WHERE code IN ('CNPS_PF_PLAFOND', 'CNPS_AT_PLAFOND', 'CNPS_MATERNITE_PLAFOND')
--    AND pays = 'CI'
--    AND montant = 75000.00;

-- 5. Nettoyage facultatif : la constante IBS_MONTANT n'est plus lue par le
--    moteur de calcul (le barème ITS progressif la remplace). Elle est laissée
--    en place pour ne rien supprimer sans validation :
-- DELETE FROM constantes WHERE code = 'IBS_MONTANT' AND pays = 'CI';


-- 7. Réinitialisation de mot de passe : jetons à usage unique.
--    Seul le condensat SHA-256 du jeton est stocké (une fuite de la base ne
--    permet pas de réinitialiser un mot de passe). Le jeton en clair n'existe
--    que dans l'email envoyé à l'utilisateur.
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    requested_ip VARCHAR(45) DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_utilisateur
    ON password_reset_tokens (utilisateur_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_hash
    ON password_reset_tokens (token_hash);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires
    ON password_reset_tokens (expires_at);

COMMENT ON TABLE password_reset_tokens
    IS 'Jetons de réinitialisation de mot de passe (usage unique, hachés, périssables)';
COMMENT ON COLUMN password_reset_tokens.token_hash
    IS 'Condensat SHA-256 du jeton ; le jeton en clair n''est jamais stocké';
COMMENT ON COLUMN password_reset_tokens.used_at
    IS 'Renseigné lors de la consommation : un jeton ne sert qu''une fois';


-- 8. Calculateurs réglementaires : indemnités de rupture, gratification,
--    congés payés et avantages en nature.
--    Sources : décret n° 2017-210 (licenciement, retraite, décès),
--    art. 15.8 du Code du travail (fin de CDD), art. 53 de la Convention
--    collective interprofessionnelle (gratification), art. 25.1/25.2 et 71-72
--    (congés payés), note de service DGI du 08/07/2024 (avantages en nature).

-- 8.1 Salaire minimum conventionnel de la catégorie, base de la gratification
--     annuelle et des frais funéraires. 0 = utiliser la grille du poste.
ALTER TABLE contrats
    ADD COLUMN IF NOT EXISTS smhc_mensuel DOUBLE PRECISION DEFAULT 0.0;

COMMENT ON COLUMN contrats.smhc_mensuel
    IS 'Salaire minimum conventionnel mensuel de la catégorie (gratification, frais funéraires)';

-- 8.2 Motif de fin de contrat normalisé et conditions de retraite
ALTER TABLE departs_salaries
    ADD COLUMN IF NOT EXISTS motif_fin_contrat VARCHAR(40) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS sous_motif_fin_cdd VARCHAR(40) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS conditions_retraite_remplies BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN departs_salaries.motif_fin_contrat
    IS 'licenciement | retraite | deces | fin_cdd | demission | rupture';
COMMENT ON COLUMN departs_salaries.sous_motif_fin_cdd
    IS 'terme_normal_sans_cdi | refus_cdi_equivalent | rupture_initiative_salarie | faute_lourde | cdi_conclu';
COMMENT ON COLUMN departs_salaries.conditions_retraite_remplies
    IS 'Ouvre le droit à l''indemnité de décès sans condition d''ancienneté';

-- 8.3 Nouvelles composantes du solde de tout compte
ALTER TABLE soldes_tout_compte
    ADD COLUMN IF NOT EXISTS indemnite_fin_cdd DOUBLE PRECISION DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS indemnite_deces DOUBLE PRECISION DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS frais_funeraires DOUBLE PRECISION DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS gratification DOUBLE PRECISION DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS detail_calcul TEXT DEFAULT NULL;

COMMENT ON COLUMN soldes_tout_compte.indemnite_fin_cdd
    IS 'Indemnité de fin de CDD : 3 % du brut du contrat (art. 15.8)';
COMMENT ON COLUMN soldes_tout_compte.indemnite_deces
    IS 'Indemnité de décès versée aux ayants droit (décret n° 2017-210)';
COMMENT ON COLUMN soldes_tout_compte.frais_funeraires
    IS 'Participation aux frais funéraires : 3, 4 ou 6 × le SMHC mensuel';
COMMENT ON COLUMN soldes_tout_compte.gratification
    IS 'Gratification annuelle / prime de fin d''année (art. 53)';
COMMENT ON COLUMN soldes_tout_compte.detail_calcul
    IS 'Détail JSON du calcul : traçabilité des montants et des paramètres';

-- 8.4 Avantages en nature (barème DGI du 08/07/2024)
CREATE TABLE IF NOT EXISTS avantages_en_nature (
    id SERIAL PRIMARY KEY,
    contrat_id INTEGER NOT NULL REFERENCES contrats(id) ON DELETE CASCADE,
    mois INTEGER NOT NULL,
    annee VARCHAR(4) NOT NULL,

    -- Logement et charges
    logement_fourni BOOLEAN DEFAULT FALSE,
    mobilier_fourni BOOLEAN DEFAULT FALSE,
    electricite_prise_en_charge BOOLEAN DEFAULT FALSE,
    eau_prise_en_charge BOOLEAN DEFAULT FALSE,
    nombre_pieces INTEGER DEFAULT 1,

    -- Équipements et domesticité
    nombre_climatiseurs DOUBLE PRECISION DEFAULT 0,
    piscine BOOLEAN DEFAULT FALSE,
    nombre_gardiens DOUBLE PRECISION DEFAULT 0,
    nombre_employes_maison DOUBLE PRECISION DEFAULT 0,
    nombre_cuisiniers DOUBLE PRECISION DEFAULT 0,

    -- Repas et autres
    cout_mensuel_repas DOUBLE PRECISION DEFAULT 0,
    exoneration_repas_applicable BOOLEAN DEFAULT FALSE,
    autres_avantages_cout_reel DOUBLE PRECISION DEFAULT 0,

    -- Participations
    participation_salarie_hors_vehicule DOUBLE PRECISION DEFAULT 0,

    -- Véhicule
    vehicule_type VARCHAR(40) DEFAULT NULL,
    vehicule_carburant DOUBLE PRECISION DEFAULT 0,
    vehicule_entretien DOUBLE PRECISION DEFAULT 0,
    vehicule_assurance DOUBLE PRECISION DEFAULT 0,
    vehicule_vignette DOUBLE PRECISION DEFAULT 0,
    vehicule_autres DOUBLE PRECISION DEFAULT 0,
    vehicule_nombre_beneficiaires INTEGER DEFAULT 1,
    vehicule_forfait_mensuel DOUBLE PRECISION DEFAULT 0,
    vehicule_valeur_reelle DOUBLE PRECISION DEFAULT 0,
    vehicule_participation DOUBLE PRECISION DEFAULT 0,
    vehicule_valeur_reelle_cnps DOUBLE PRECISION DEFAULT 0,

    -- Assiette sociale (valeur réelle), distincte de l'assiette fiscale
    valeur_reelle_hors_vehicule_cnps DOUBLE PRECISION DEFAULT NULL,

    est_persistant BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_avantage_nature_contrat_periode UNIQUE (contrat_id, mois, annee)
);

CREATE INDEX IF NOT EXISTS ix_avantage_nature_contrat_periode
    ON avantages_en_nature (contrat_id, annee, mois);

COMMENT ON TABLE avantages_en_nature
    IS 'Avantages en nature par salarié et par mois (barème DGI du 08/07/2024)';
COMMENT ON COLUMN avantages_en_nature.vehicule_type
    IS 'fonction_service | transport_collectif_couts_reels | transport_collectif_forfait | autre_taxable';
COMMENT ON COLUMN avantages_en_nature.valeur_reelle_hors_vehicule_cnps
    IS 'Valeur réelle pour l''assiette CNPS, distincte de l''évaluation fiscale';

-- 6. Contrôles post-migration (à exécuter manuellement) :
--    -- Aucun compte sans mot de passe (sinon connexion impossible) :
--    SELECT id, email, role FROM utilisateurs WHERE hashed_password IS NULL;
--    -- La colonne et ses valeurs par défaut :
--    SELECT column_name, data_type, column_default, is_nullable
--      FROM information_schema.columns
--     WHERE table_name = 'utilisateurs' AND column_name = 'must_change_password';
--    -- Les majorations d'heures supplémentaires :
--    SELECT code, libelle FROM plan_paie WHERE code LIKE 'HS%' ORDER BY code;
