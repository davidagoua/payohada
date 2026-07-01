-- ==============================================================================
-- SEED DE LA BASE DE DONNEES PAYOHADA (POSTGRESQL / SQLITE)
-- ==============================================================================

-- 1. Seed de la table constantes
INSERT INTO constantes (code, description, montant, unite, pays) VALUES
('SMIG', 'Salaire Minimum Interprofessionnel Garanti', 75000.0, 'FCFA', 'CI'),
('CNPS_PF_PLAFOND', 'Plafond mensuel pour les Prestations Familiales', 75000.0, 'FCFA', 'CI'),
('CNPS_PF_TAUX_P', 'Taux patronal Prestations Familiales', 5.0, '%', 'CI'),
('CNPS_RETRAITE_PLAFOND', 'Plafond mensuel pour la Retraite', 3375000.0, 'FCFA', 'CI'),
('CNPS_RETRAITE_TAUX_S', 'Taux salarial Retraite', 6.3, '%', 'CI'),
('CNPS_RETRAITE_TAUX_P', 'Taux patronal Retraite', 7.7, '%', 'CI'),
('CNPS_AT_PLAFOND', 'Plafond mensuel Accident du Travail', 75000.0, 'FCFA', 'CI'),
('CNPS_MATERNITE_PLAFOND', 'Plafond mensuel Assurance Maternité', 75000.0, 'FCFA', 'CI'),
('CNPS_MATERNITE_TAUX_P', 'Taux patronal Assurance Maternité', 0.75, '%', 'CI'),
('CN_TAUX_P_LOC', 'Taux Contribution Nationale patronale locaux', 1.5, '%', 'CI'),
('CN_TAUX_P_EXP', 'Taux Contribution Nationale patronale expatriés', 8.0, '%', 'CI'),
('TA_TAUX_P', 'Taux Taxe Apprentissage patronale', 0.4, '%', 'CI'),
('TFC_TAUX_P', 'Taux Taxe Formation Continue patronale', 0.6, '%', 'CI'),
('CMU_MONTANT_S', 'Montant CMU part salariale', 500.0, 'FCFA', 'CI'),
('CMU_MONTANT_P', 'Montant CMU part patronale', 500.0, 'FCFA', 'CI'),
('IBS_MONTANT', 'Montant Impôt Brut forfaitaire', 74577.0, 'FCFA', 'CI'),
('RICF_MONTANT', 'Montant Réduction d''impôt charge familiale', -11000.0, 'FCFA', 'CI')
ON CONFLICT (code, pays) DO UPDATE SET
  description = EXCLUDED.description,
  montant = EXCLUDED.montant,
  unite = EXCLUDED.unite,
  date_modification = CURRENT_TIMESTAMP;

-- 2. Seed de la table plan_paie
INSERT INTO plan_paie (code, type, libelle, mode_calcul, sens, pays) VALUES
('BASE', 'B', 'Salaire de base', 'Manuel', 'Gain', 'CI'),
('SURSALAIRE', 'B', 'Sursalaire', 'Manuel', 'Gain', 'CI'),
('ABS', 'B', 'Absence', 'Sémi-auto', 'Retenue', 'CI'),
('HS_15', 'B', 'Heures supplémentaires majorées à 15%', 'Sémi-auto', 'Gain', 'CI'),
('HS_25', 'B', 'Heures supplémentaires majorées à 25%', 'Sémi-auto', 'Gain', 'CI'),
('HS_50', 'B', 'Heures supplémentaires majorées à 50%', 'Sémi-auto', 'Gain', 'CI'),
('IBS', 'I', 'Impôt brut sur salaire', 'Auto', 'Retenue', 'CI'),
('RICF', 'I', 'Réduction d''impôt pour charge familiale', 'Auto', 'Gain', 'CI'),
('CNPS_PF', 'I', 'CNPS - Prestations Familiales', 'Auto', 'Retenue', 'CI'),
('CNPS_RETRAITE', 'I', 'CNPS - Retraite', 'Auto', 'Retenue', 'CI'),
('CNPS_AT', 'I', 'CNPS - Accidents du Travail et Maladies Pro.', 'Auto', 'Retenue', 'CI'),
('CNPS_MATERNITE', 'I', 'CNPS - Assurance Maternité', 'Auto', 'Retenue', 'CI'),
('CMU_S', 'I', 'Cotisation CMU part salariale', 'Auto', 'Retenue', 'CI'),
('CMU_P', 'C', 'Cotisation CMU part patronale', 'Auto', 'Charge', 'CI'),
('CN', 'C', 'Contribution nationale', 'Auto', 'Charge', 'CI'),
('TA', 'C', 'Taxe d''apprentissage', 'Auto', 'Charge', 'CI'),
('TFC', 'C', 'Taxe Formation continue', 'Auto', 'Charge', 'CI'),
('TRANSPORT', 'A', 'Indemnité de transport', 'Sémi-auto', 'Gain', 'CI'),
('TELEPHONE', 'A', 'Dotation téléphonique', 'Sémi-auto', 'Gain', 'CI')
ON CONFLICT (code, pays) DO UPDATE SET
  libelle = EXCLUDED.libelle,
  type = EXCLUDED.type,
  sens = EXCLUDED.sens,
  date_modification = CURRENT_TIMESTAMP;
