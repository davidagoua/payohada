"""
Modèles de base de données inspirés de l'API OpenPaye.
Architecture : Dossier > Etablissement > Salarié > Contrat > (Bulletins, Absences, HS, Primes...)
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime,
    ForeignKey, Text, Enum, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


# ─────────────────────────────────────────
#  ENUMS
# ─────────────────────────────────────────

class TypeSalaireEnum(str, enum.Enum):
    MENSUEL = "Mensuel"
    HORAIRE = "Horaire"


class TypeCotisationEnum(str, enum.Enum):
    RETRAITE_COMPLEMENTAIRE = "retraite_complementaire"
    PREVOYANCE = "prevoyance"
    MUTUELLE = "mutuelle"
    URSSAF = "urssaf"
    POLE_EMPLOI = "pole_emploi"
    AUTRE = "autre"


class StatutContratEnum(str, enum.Enum):
    ACTIF = "actif"
    SUSPENDU = "suspendu"
    TERMINE = "termine"


# ─────────────────────────────────────────
#  MIXIN TIMESTAMPS
# ─────────────────────────────────────────

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ─────────────────────────────────────────
#  UTILISATEURS (multi-tenant)
# ─────────────────────────────────────────

class Utilisateur(TimestampMixin, Base):
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    nom = Column(String(100), nullable=True)
    prenom = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    supabase_uid = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    # Relations
    dossiers = relationship("Dossier", back_populates="proprietaire")


# ─────────────────────────────────────────
#  DOSSIER (entité cliente / entreprise)
# ─────────────────────────────────────────

class Dossier(TimestampMixin, Base):
    """
    Un dossier représente une entreprise cliente.
    Un gestionnaire de paie peut gérer plusieurs dossiers.
    """
    __tablename__ = "dossiers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    siret = Column(String(14), index=True)
    nom_dossier = Column(String(50), nullable=False)
    adresse_email = Column(String(150))
    telephone = Column(String(15))
    nom_contact = Column(String(100))
    qualite = Column(Integer)         # Code qualité du contact
    annee = Column(String(4))         # Année courante de gestion
    pays = Column(String(100), default="Côte d'Ivoire")

    # Clé étrangère vers le propriétaire/gestionnaire
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False)

    # Relations
    proprietaire = relationship("Utilisateur", back_populates="dossiers")
    etablissements = relationship("Etablissement", back_populates="dossier", cascade="all, delete-orphan")
    net_entreprise = relationship("NetEntreprise", back_populates="dossier", uselist=False)

    __table_args__ = (
        Index("ix_dossiers_siret", "siret"),
    )


# ─────────────────────────────────────────
#  NET ENTREPRISE (déclaration DSN)
# ─────────────────────────────────────────

class NetEntreprise(TimestampMixin, Base):
    __tablename__ = "net_entreprises"

    id = Column(Integer, primary_key=True, index=True)
    dossier_id = Column(Integer, ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False, unique=True)
    parametrage_domaine = Column(Boolean, default=False)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    siret = Column(String(14), nullable=False)
    civilite = Column(String(10))        # M., MME
    email = Column(String(150))
    telephone = Column(String(15))

    # Relations
    dossier = relationship("Dossier", back_populates="net_entreprise")


# ─────────────────────────────────────────
#  ETABLISSEMENT
# ─────────────────────────────────────────

class AdresseEtablissement(Base):
    """Adresse physique d'un établissement (table embarquée via FK)."""
    __tablename__ = "adresses_etablissements"

    id = Column(Integer, primary_key=True, index=True)
    etablissement_id = Column(Integer, ForeignKey("etablissements.id", ondelete="CASCADE"), unique=True)
    adresse_postale = Column(String(200))
    adresse_postale2 = Column(String(200))
    complement_adresse = Column(String(200))
    code_postal = Column(String(10))
    ville = Column(String(100))
    code_insee = Column(String(10))
    code_distribution_etranger = Column(String(20))
    pays = Column(String(100), default="France")

    etablissement = relationship("Etablissement", back_populates="adresse")


class GestionCongesPayes(Base):
    __tablename__ = "gestion_conges_payes"

    id = Column(Integer, primary_key=True, index=True)
    etablissement_id = Column(Integer, ForeignKey("etablissements.id", ondelete="CASCADE"), unique=True)
    mois_cloture_droits_cp = Column(Integer, default=5)   # Mai par défaut
    report_automatique = Column(Boolean, default=True)
    gestion_absences_heures_bulletins = Column(Boolean, default=True)
    decompte_conges_payes = Column(String(50))             # ex: "ouvrables", "ouvres"
    valorisation_conges_payes = Column(String(50))         # ex: "maintien", "1/10"
    bloquer_gestion_cp = Column(Boolean, default=False)
    affilie_caisse_conges_payes = Column(Boolean, default=False)

    etablissement = relationship("Etablissement", back_populates="gestion_conges")


class BanqueEtablissement(Base):
    __tablename__ = "banques_etablissements"

    id = Column(Integer, primary_key=True, index=True)
    etablissement_id = Column(Integer, ForeignKey("etablissements.id", ondelete="CASCADE"), unique=True)
    virement = Column(Boolean, default=False)
    code_bic = Column(String(11))
    iban = Column(String(34))

    etablissement = relationship("Etablissement", back_populates="banque")


class Etablissement(TimestampMixin, Base):
    __tablename__ = "etablissements"

    id = Column(Integer, primary_key=True, index=True)
    dossier_id = Column(Integer, ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(15), nullable=False)
    raison_sociale = Column(String(200), nullable=False)
    etablissement_principal = Column(Boolean, default=False)
    siret = Column(String(14), index=True)
    forme_juridique = Column(Integer)        # Code forme juridique
    civilite = Column(String(10))
    activite = Column(String(200))
    ape = Column(String(5))                  # Code APE (5 caractères)
    libelle_ape = Column(String(200))
    ccn = Column(Integer)                    # Convention collective 1
    ccn2 = Column(Integer)
    ccn3 = Column(Integer)
    ccn4 = Column(Integer)
    ccn5 = Column(Integer)
    avenant = Column(Boolean, default=False)
    numero_cotisant = Column(String(18))
    date_radiation = Column(DateTime(timezone=True))
    code_risque_at = Column(String(20))
    taux_at = Column(Float, default=0.0)
    is_taux_versement_transport = Column(Boolean, default=False)
    taux_versement_transport = Column(Float, default=0.0)

    # Champs CNPS
    cnps_matricule = Column(String(50))
    cnps_code_activite = Column(String(50))
    cnps_code_agence = Column(String(50))
    cnps_code_etablissement = Column(String(50))
    cnps_agence_rattachement = Column(String(150))
    cnps_periodicite_paiement = Column(String(50))
    cmu_periodicite_paiement = Column(String(50))

    # Champs DGI
    dgi_compte_contribuable = Column(String(50))
    dgi_centre_impots = Column(String(150))
    dgi_periodicite_declaration = Column(String(50))
    dgi_regime_fiscal = Column(String(150))

    # Relations
    dossier = relationship("Dossier", back_populates="etablissements")
    adresse = relationship("AdresseEtablissement", back_populates="etablissement", uselist=False, cascade="all, delete-orphan")
    banque = relationship("BanqueEtablissement", back_populates="etablissement", uselist=False, cascade="all, delete-orphan")
    gestion_conges = relationship("GestionCongesPayes", back_populates="etablissement", uselist=False, cascade="all, delete-orphan")
    salaries = relationship("Salarie", back_populates="etablissement")
    caisses_cotisations = relationship("CaisseCotisation", back_populates="etablissement", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("dossier_id", "code", name="uq_etablissement_dossier_code"),
    )


# ─────────────────────────────────────────
#  CAISSE DE COTISATIONS
# ─────────────────────────────────────────

class CaisseCotisation(TimestampMixin, Base):
    __tablename__ = "caisses_cotisations"

    id = Column(Integer, primary_key=True, index=True)
    etablissement_id = Column(Integer, ForeignKey("etablissements.id", ondelete="CASCADE"))
    nom_caisse = Column(String(200))
    code_dsn = Column(String(50))
    adresse_caisse = Column(Text)
    type_cotisation = Column(String(50), nullable=False)
    exclus_de_calcul_dsn = Column(Boolean, default=False)
    numero_affiliation = Column(String(20))
    type_paiement = Column(String(50))
    periodicite_paiement = Column(String(50))
    date_paiement = Column(String(20))
    iban = Column(String(34))
    bic = Column(String(11))

    # Relations
    etablissement = relationship("Etablissement", back_populates="caisses_cotisations")


# ─────────────────────────────────────────
#  SALARIÉ
# ─────────────────────────────────────────

class Salarie(TimestampMixin, Base):
    __tablename__ = "salaries"

    id = Column(Integer, primary_key=True, index=True)
    etablissement_id = Column(Integer, ForeignKey("etablissements.id", ondelete="CASCADE"), nullable=False)
    matricule = Column(String(50), nullable=False, index=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    nom_usage = Column(String(100))
    civilite = Column(String(10))           # M., MME
    date_naissance = Column(DateTime(timezone=True))
    lieu_naissance = Column(String(100))
    departement_naissance = Column(String(5))
    pays_naissance = Column(String(100))
    nationalite = Column(String(100))
    numero_securite_sociale = Column(String(15), index=True)
    adresse = Column(String(200))
    adresse2 = Column(String(200))
    code_postal = Column(String(10))
    ville = Column(String(100))
    pays = Column(String(100), default="France")
    email = Column(String(150))
    telephone = Column(String(15))
    iban = Column(String(34))
    bic = Column(String(11))
    is_active = Column(Boolean, default=True)
    expatrie = Column(Boolean, default=False)

    # Relations
    etablissement = relationship("Etablissement", back_populates="salaries")
    contrats = relationship("Contrat", back_populates="salarie", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("etablissement_id", "matricule", name="uq_salarie_etablissement_matricule"),
    )


# ─────────────────────────────────────────
#  CONTRAT
# ─────────────────────────────────────────

class JoursHebdomadaires(Base):
    __tablename__ = "jours_hebdomadaires"

    id = Column(Integer, primary_key=True, index=True)
    contrat_id = Column(Integer, ForeignKey("contrats.id", ondelete="CASCADE"), unique=True)
    jours_hebdo = Column(Float, default=5.0)
    jour_lundi = Column(Float, default=1.0)
    jour_mardi = Column(Float, default=1.0)
    jour_mercredi = Column(Float, default=1.0)
    jour_jeudi = Column(Float, default=1.0)
    jour_vendredi = Column(Float, default=1.0)
    jour_samedi = Column(Float, default=0.0)
    jour_dimanche = Column(Float, default=0.0)

    contrat = relationship("Contrat", back_populates="jours_hebdomadaires")


class Horaires(Base):
    __tablename__ = "horaires"

    id = Column(Integer, primary_key=True, index=True)
    contrat_id = Column(Integer, ForeignKey("contrats.id", ondelete="CASCADE"), unique=True)
    horaire_travail = Column(Float, default=151.67)   # heures/mois légal
    horaire_hebdo = Column(Float, default=35.0)
    horaire_lundi = Column(Float, default=7.0)
    horaire_mardi = Column(Float, default=7.0)
    horaire_mercredi = Column(Float, default=7.0)
    horaire_jeudi = Column(Float, default=7.0)
    horaire_vendredi = Column(Float, default=7.0)
    horaire_samedi = Column(Float, default=0.0)
    horaire_dimanche = Column(Float, default=0.0)

    contrat = relationship("Contrat", back_populates="horaires")


class DepartSalarie(Base):
    """Informations de sortie/départ d'un salarié."""
    __tablename__ = "departs_salaries"

    id = Column(Integer, primary_key=True, index=True)
    contrat_id = Column(Integer, ForeignKey("contrats.id", ondelete="CASCADE"), unique=True)
    date_sortie = Column(String(20))
    bulletin_post_contrat = Column(Boolean, default=False)
    bulletin_post_contrat_du = Column(String(20))
    bulletin_post_contrat_au = Column(String(20))
    motif_sortie = Column(Integer)          # Code motif de sortie
    date_notification_rupture = Column(String(20))
    date_notification_signature = Column(String(20))
    date_engagement_procedure = Column(String(20))
    maintien_affiliation = Column(Boolean, default=False)
    transaction_en_cours = Column(Boolean, default=False)
    dernier_jour_travaille = Column(String(20))
    statut_particulier = Column(Integer)
    # Préavis 1
    type_paiement_preavis01 = Column(Integer)
    preavis_de01 = Column(String(20))
    preavis_au01 = Column(String(20))
    # Préavis 2
    type_paiement_preavis02 = Column(Integer)
    preavis_de02 = Column(String(20))
    preavis_au02 = Column(String(20))
    # Préavis 3
    type_paiement_preavis03 = Column(Integer)
    preavis_de03 = Column(String(20))
    preavis_au03 = Column(String(20))

    contrat = relationship("Contrat", back_populates="depart_salarie")


class MoisAExclure(Base):
    """Mois à exclure du calcul de paie pour un contrat."""
    __tablename__ = "mois_a_exclure"

    id = Column(Integer, primary_key=True, index=True)
    contrat_id = Column(Integer, ForeignKey("contrats.id", ondelete="CASCADE"), unique=True)
    exclure_janvier = Column(Boolean, default=False)
    exclure_fevrier = Column(Boolean, default=False)
    exclure_mars = Column(Boolean, default=False)
    exclure_avril = Column(Boolean, default=False)
    exclure_mai = Column(Boolean, default=False)
    exclure_juin = Column(Boolean, default=False)
    exclure_juillet = Column(Boolean, default=False)
    exclure_aout = Column(Boolean, default=False)
    exclure_septembre = Column(Boolean, default=False)
    exclure_octobre = Column(Boolean, default=False)
    exclure_novembre = Column(Boolean, default=False)
    exclure_decembre = Column(Boolean, default=False)

    contrat = relationship("Contrat", back_populates="mois_a_exclure")


class Contrat(TimestampMixin, Base):
    __tablename__ = "contrats"

    id = Column(Integer, primary_key=True, index=True)
    dossier_id = Column(Integer, ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False)
    salarie_id = Column(Integer, ForeignKey("salaries.id", ondelete="CASCADE"), nullable=False)
    etablissement_id = Column(Integer, ForeignKey("etablissements.id"), nullable=False)

    # Identifiants métiers
    code_etablissement = Column(String(15), nullable=False)
    matricule_salarie = Column(String(50), nullable=False)
    numero_contrat = Column(String(50), nullable=False)
    ancien_numero_contrat_dsn = Column(String(50))

    # Classification
    emploi_conventionnel = Column(Integer)
    ccn = Column(Integer)
    idcc = Column(Integer)
    emploi = Column(String(200))
    type_contrat_travail = Column(Integer, nullable=False)   # CDI=10, CDD=29, etc.
    type_contrat_temps_partiel = Column(Integer)
    statut_professionnel = Column(Integer, nullable=False)
    regime_retraite = Column(Integer)
    cas_particuliers = Column(Integer)

    # Rémunération
    salaire_mensuel = Column(Float, default=0.0)
    salaire_horaire = Column(Float, default=0.0)
    type_salaire = Column(String(10), default="Mensuel")   # Mensuel | Horaire
    nbr_heures_travail_mensuel_majorees = Column(Float, default=0.0)

    # Dates
    date_debut_contrat = Column(String(20))
    date_fin_previsionnelle_contrat = Column(String(20))
    date_anciennete = Column(String(20))

    # Options
    salarie_temps_partiel = Column(Boolean, default=False)
    forfait_jour = Column(Boolean, default=False)
    ne_pas_calculer_premier_bulletin = Column(Boolean, default=False)
    nbr_jour_annuels_prevus = Column(Float, default=218.0)
    tags = Column(Text)             # Séparé par ","
    statut = Column(String(20), default="actif")
    unite_temps = Column(String(10), default="Heures")
    sursalaire = Column(Float, default=0.0)
    indemnite_transport = Column(Float, default=0.0)
    dotation_telephonique = Column(Float, default=0.0)

    # Relations
    dossier = relationship("Dossier")
    salarie = relationship("Salarie", back_populates="contrats")
    etablissement = relationship("Etablissement")
    jours_hebdomadaires = relationship("JoursHebdomadaires", back_populates="contrat", uselist=False, cascade="all, delete-orphan")
    horaires = relationship("Horaires", back_populates="contrat", uselist=False, cascade="all, delete-orphan")
    depart_salarie = relationship("DepartSalarie", back_populates="contrat", uselist=False, cascade="all, delete-orphan")
    mois_a_exclure = relationship("MoisAExclure", back_populates="contrat", uselist=False, cascade="all, delete-orphan")
    absences = relationship("Absence", back_populates="contrat", cascade="all, delete-orphan")
    heures_supplementaires = relationship("HeureSupplementaire", back_populates="contrat", cascade="all, delete-orphan")
    primes = relationship("Prime", back_populates="contrat", cascade="all, delete-orphan")
    options = relationship("Option", back_populates="contrat", cascade="all, delete-orphan")
    bulletins_paies = relationship("BulletinPaie", back_populates="contrat", cascade="all, delete-orphan")
    variables_reprise = relationship("VariableRepriseDossier", back_populates="contrat", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("dossier_id", "numero_contrat", name="uq_contrat_dossier_numero"),
    )


# ─────────────────────────────────────────
#  ÉLÉMENTS VARIABLES
# ─────────────────────────────────────────

class Absence(TimestampMixin, Base):
    __tablename__ = "absences"

    id = Column(Integer, primary_key=True, index=True)
    contrat_id = Column(Integer, ForeignKey("contrats.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50))              # Code type d'absence (CP, MAL, AT, etc.)
    date_debut = Column(DateTime(timezone=True))
    date_fin = Column(DateTime(timezone=True))
    nbr_heure_by_user = Column(Float, default=0.0)
    nbr_jour_by_user = Column(Float, default=0.0)
    mois = Column(Integer)                  # 1-12
    annee = Column(String(4))

    contrat = relationship("Contrat", back_populates="absences")

    __table_args__ = (
        Index("ix_absences_contrat_periode", "contrat_id", "annee", "mois"),
    )


class HeureSupplementaire(TimestampMixin, Base):
    __tablename__ = "heures_supplementaires"

    id = Column(Integer, primary_key=True, index=True)
    contrat_id = Column(Integer, ForeignKey("contrats.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50))              # Code type HS (HS25, HS50, etc.)
    nombre = Column(Float, nullable=False)
    mois = Column(Integer)                  # 1-12
    annee = Column(String(4))

    contrat = relationship("Contrat", back_populates="heures_supplementaires")

    __table_args__ = (
        Index("ix_hs_contrat_periode", "contrat_id", "annee", "mois"),
    )


class Prime(TimestampMixin, Base):
    __tablename__ = "primes"

    id = Column(Integer, primary_key=True, index=True)
    contrat_id = Column(Integer, ForeignKey("contrats.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50))              # Code prime (PRIME13, PRIMEX, etc.)
    montant = Column(Float, nullable=False)
    mois = Column(Integer)
    annee = Column(String(4))
    libelle = Column(String(200))

    contrat = relationship("Contrat", back_populates="primes")


class Option(TimestampMixin, Base):
    """Options spécifiques du bulletin (avantages en nature, frais pro, etc.)."""
    __tablename__ = "options"

    id = Column(Integer, primary_key=True, index=True)
    contrat_id = Column(Integer, ForeignKey("contrats.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)
    valeur = Column(String(200))
    valeur_numerique = Column(Float)
    mois = Column(Integer)
    annee = Column(String(4))
    libelle = Column(String(200))

    contrat = relationship("Contrat", back_populates="options")


# ─────────────────────────────────────────
#  VARIABLES DE REPRISE DOSSIER
# ─────────────────────────────────────────

class VariableRepriseDossier(TimestampMixin, Base):
    """Cumuls de reprise lors d'une migration de dossier."""
    __tablename__ = "variables_reprise_dossier"

    id = Column(Integer, primary_key=True, index=True)
    contrat_id = Column(Integer, ForeignKey("contrats.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)
    valeur = Column(Float, default=0.0)
    libelle = Column(String(200))
    annee = Column(String(4))

    contrat = relationship("Contrat", back_populates="variables_reprise")


# ─────────────────────────────────────────
#  BULLETIN DE PAIE
# ─────────────────────────────────────────

class BulletinPaie(TimestampMixin, Base):
    __tablename__ = "bulletins_paies"

    id = Column(Integer, primary_key=True, index=True)
    contrat_id = Column(Integer, ForeignKey("contrats.id", ondelete="CASCADE"), nullable=False)
    dossier_id = Column(Integer, ForeignKey("dossiers.id"), nullable=False)
    mois = Column(Integer, nullable=False)   # 1-12
    annee = Column(Integer, nullable=False)
    statut = Column(String(30), default="brouillon")  # brouillon | calcule | valide | envoye
    date_paiement = Column(DateTime(timezone=True))
    salaire_brut = Column(Float, default=0.0)
    cotisations_salariales = Column(Float, default=0.0)
    cotisations_patronales = Column(Float, default=0.0)
    net_a_payer = Column(Float, default=0.0)
    net_imposable = Column(Float, default=0.0)
    commentaire = Column(Text)
    inclure_document_de_sortie = Column(Boolean, default=False)

    # Relations
    contrat = relationship("Contrat", back_populates="bulletins_paies")
    dossier = relationship("Dossier")
    lignes = relationship("LigneBulletinPaie", back_populates="bulletin", cascade="all, delete-orphan")
    variables_bulletin = relationship("VariableBulletin", back_populates="bulletin", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("contrat_id", "mois", "annee", name="uq_bulletin_contrat_periode"),
        Index("ix_bulletin_dossier_periode", "dossier_id", "annee", "mois"),
    )


class LigneBulletinPaie(Base):
    """
    Chaque ligne du bulletin (cotisation, salaire de base, prime...).
    Correspond au BulletinDetail de l'API OpenPaye.
    """
    __tablename__ = "lignes_bulletins_paies"

    id = Column(Integer, primary_key=True, index=True)
    bulletin_id = Column(Integer, ForeignKey("bulletins_paies.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)
    libelle = Column(String(200))
    salaire_base = Column(Float, default=0.0)
    base_s = Column(Float, default=0.0)      # Base salarié
    base_p = Column(Float, default=0.0)      # Base patronal
    taux_s = Column(Float, default=0.0)      # Taux salarié
    taux_p = Column(Float, default=0.0)      # Taux patronal
    montant_pr = Column(Float, default=0.0)  # Montant à percevoir
    montant_cs = Column(Float, default=0.0)  # Montant cotisation salarié
    montant_cp = Column(Float, default=0.0)  # Montant cotisation patronal

    bulletin = relationship("BulletinPaie", back_populates="lignes")

    __table_args__ = (
        UniqueConstraint("bulletin_id", "code", name="uq_ligne_bulletin_code"),
        Index("ix_ligne_bulletin_code", "bulletin_id", "code"),
    )


class VariableBulletin(Base):
    """Variables calculées spécifiques au bulletin."""
    __tablename__ = "variables_bulletins"

    id = Column(Integer, primary_key=True, index=True)
    bulletin_id = Column(Integer, ForeignKey("bulletins_paies.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)
    libelle = Column(String(200))
    valeur = Column(Float, default=0.0)

    bulletin = relationship("BulletinPaie", back_populates="variables_bulletin")


# ─────────────────────────────────────────
#  SOLDE DE TOUT COMPTE
# ─────────────────────────────────────────

class SoldeToutCompte(TimestampMixin, Base):
    __tablename__ = "soldes_tout_compte"

    id = Column(Integer, primary_key=True, index=True)
    contrat_id = Column(Integer, ForeignKey("contrats.id", ondelete="CASCADE"), unique=True, nullable=False)
    date_generation = Column(DateTime(timezone=True), server_default=func.now())
    indemnite_licenciement = Column(Float, default=0.0)
    indemnite_conges_payes = Column(Float, default=0.0)
    indemnite_preavis = Column(Float, default=0.0)
    indemnite_autre = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    statut = Column(String(30), default="genere")   # genere | valide | envoye
    commentaire = Column(Text)

    contrat = relationship("Contrat")


# ─────────────────────────────────────────
#  RÉFÉRENTIEL VARIABLES (codes disponibles)
# ─────────────────────────────────────────

class Variable(Base):
    """Référentiel des codes variables/rubriques disponibles dans le système."""
    __tablename__ = "variables"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    libelle = Column(String(200))
    type = Column(String(50))     # absence, hs, prime, option, reprise
    description = Column(Text)
    is_active = Column(Boolean, default=True)


# ─────────────────────────────────────────
#  DSN (Déclaration Sociale Nominative)
# ─────────────────────────────────────────

class DSN(TimestampMixin, Base):
    __tablename__ = "dsns"

    id = Column(Integer, primary_key=True, index=True)
    dossier_id = Column(Integer, ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False)
    etablissement_id = Column(Integer, ForeignKey("etablissements.id"), nullable=False)
    mois = Column(Integer, nullable=False)
    annee = Column(Integer, nullable=False)
    statut = Column(String(30), default="en_attente")  # en_attente | envoye | accepte | rejete
    contenu_txt = Column(Text)
    date_envoi = Column(DateTime(timezone=True))
    reference_envoi = Column(String(100))

    dossier = relationship("Dossier")
    etablissement = relationship("Etablissement")

    __table_args__ = (
        UniqueConstraint("etablissement_id", "mois", "annee", name="uq_dsn_etablissement_periode"),
    )


# ─────────────────────────────────────────
#  CONSTANTES ET PLAN DE PAIE
# ─────────────────────────────────────────

class Constante(Base):
    __tablename__ = "constantes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), nullable=False, index=True)
    description = Column(String(255), nullable=False)
    montant = Column(Float, nullable=False, default=0.0)
    unite = Column(String(20), nullable=True)
    pays = Column(String(50), nullable=False, default="CI", index=True)
    est_actif = Column(Boolean, default=True)
    date_creation = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    date_modification = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("code", "pays", name="uk_constante_code_pays"),
    )


class PlanPaie(Base):
    __tablename__ = "plan_paie"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(2), nullable=False, index=True)
    code = Column(String(20), nullable=False, index=True)
    libelle = Column(String(255), nullable=False)
    mode_calcul = Column(String(20), nullable=False, default="Sémi-auto")
    sens = Column(String(10), nullable=False, default="Gain")
    masque_si_nul = Column(Boolean, default=False)
    imprimable = Column(Boolean, default=True)
    compte_debit = Column(String(20), nullable=True)
    compte_credit = Column(String(20), nullable=True)
    pays = Column(String(50), nullable=False, default="CI", index=True)
    est_actif = Column(Boolean, default=True)
    date_creation = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    date_modification = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("code", "pays", name="uk_plan_paie_code_pays"),
    )