"""Import de données de base (Excel / CSV) : modèles, validation, exécution.

Le flux est volontairement en deux temps :

1. **analyse à blanc** : le fichier est lu, les colonnes sont rapprochées des
   champs attendus, chaque ligne est validée sans rien écrire en base ;
2. **exécution** : seules les lignes valides sont créées ou mises à jour, de
   façon idempotente (clés métier : code établissement, matricule, numéro de
   contrat).

Les erreurs sont conservées dans le rapport JSON du job, ce qui sert à la fois
de rapport de rapprochement et de journal d'audit.
"""
from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.models.models import (
    Contrat,
    Dossier,
    Etablissement,
    Horaires,
    JoursHebdomadaires,
    Salarie,
)

MAX_IMPORT_BYTES = 25 * 1024 * 1024
EXTENSIONS_AUTORISEES = {".xlsx", ".xlsm", ".csv"}
DOSSIER_IMPORTS = Path("uploads") / "imports"

NAVY = "01173A"
GREEN = "177B36"


# ─────────────────────────────────────────
#  Définition des modèles d'import
# ─────────────────────────────────────────

@dataclass(frozen=True)
class Champ:
    cle: str
    libelle: str
    obligatoire: bool = False
    exemple: str = ""
    aliases: tuple[str, ...] = ()
    aide: str = ""


def _aliases(libelle: str, *extra: str) -> tuple[str, ...]:
    return (libelle, libelle.replace(" *", ""), *extra)


CHAMPS: dict[str, tuple[Champ, ...]] = {
    "etablissements": (
        Champ("code", "Code établissement", True, "ETB01", _aliases("Code établissement", "code etablissement", "code etb", "code")),
        Champ("raison_sociale", "Raison sociale", True, "ETS NORD CI", _aliases("Raison sociale", "nom etablissement", "nom")),
        Champ("sigle", "Sigle", False, "NORD", _aliases("Sigle", "abreviation")),
        Champ("numero_rccm", "N° RCCM", False, "CI-ABJ-2024-B-12345", _aliases("N° RCCM", "rccm", "numero rccm")),
        Champ("activite", "Activité", False, "Commerce de détail", _aliases("Activité", "secteur", "secteur activite")),
        Champ("adresse_commune", "Commune", False, "Cocody", _aliases("Commune", "ville")),
        Champ("adresse_pays", "Pays", False, "Côte d'Ivoire", _aliases("Pays", "adresse pays")),
        Champ("telephone", "Téléphone", False, "+225 27 00 00 00 00", _aliases("Téléphone", "tel", "telephone")),
        Champ("email", "Email", False, "contact@ets.ci", _aliases("Email", "e-mail", "adresse email")),
        Champ("taux_at", "Taux AT (%)", False, "2", _aliases("Taux AT (%)", "taux at", "taux accident travail")),
        Champ("cnps_matricule", "Matricule CNPS", False, "123456789", _aliases("Matricule CNPS", "cnps")),
        Champ("dgi_compte_contribuable", "Compte contribuable DGI", False, "CI-1234567", _aliases("Compte contribuable DGI", "compte contribuable", "dgi")),
        Champ("date_creation", "Date de création", False, "2020-01-15", _aliases("Date de création", "date creation")),
    ),
    "salaries": (
        Champ("etablissement_code", "Code établissement", True, "ETB01", _aliases("Code établissement", "code etablissement", "code etb", "etablissement")),
        Champ("matricule", "Matricule", True, "M0001", _aliases("Matricule", "matricule salarie")),
        Champ("nom", "Nom", True, "Kouadio", _aliases("Nom", "nom de famille")),
        Champ("prenom", "Prénom", True, "Jean", _aliases("Prénom", "prenom")),
        Champ("civilite", "Civilité", False, "M.", _aliases("Civilité", "civilite"), "M. ou MME"),
        Champ("date_naissance", "Date de naissance", False, "1990-05-12", _aliases("Date de naissance", "date naissance", "naissance")),
        Champ("lieu_naissance", "Lieu de naissance", False, "Abidjan", _aliases("Lieu de naissance", "lieu naissance")),
        Champ("numero_securite_sociale", "N° sécurité sociale", False, "CI0000000000001", _aliases("N° sécurité sociale", "numero securite sociale", "nir", "nss")),
        Champ("situation_matrimoniale", "Situation matrimoniale", False, "Marié(e)", _aliases("Situation matrimoniale", "situation familiale", "situation")),
        Champ("enfants_charge", "Enfants à charge", False, "2", _aliases("Enfants à charge", "enfants charge", "enfants")),
        Champ("email", "Email personnel", False, "jean@exemple.ci", _aliases("Email personnel", "email", "e-mail")),
        Champ("telephone", "Téléphone", False, "+225 07 00 00 00 00", _aliases("Téléphone", "tel", "telephone")),
        Champ("adresse", "Adresse", False, "Rue des Jardins", _aliases("Adresse", "adresse postale")),
        Champ("ville", "Ville", False, "Abidjan", _aliases("Ville",)),
        Champ("pays", "Pays", False, "Côte d'Ivoire", _aliases("Pays",)),
        Champ("iban", "IBAN", False, "CI0000000000000000000000", _aliases("IBAN", "iban versement")),
        Champ("bic", "BIC", False, "XXXXXXXX", _aliases("BIC", "bic banque")),
        Champ("expatrie", "Expatrié (oui/non)", False, "non", _aliases("Expatrié (oui/non)", "expatrie", "expatrie oui non")),
        Champ("is_active", "Actif (oui/non)", False, "oui", _aliases("Actif (oui/non)", "actif", "is active")),
    ),
    "contrats": (
        Champ("etablissement_code", "Code établissement", True, "ETB01", _aliases("Code établissement", "code etablissement", "code etb", "etablissement")),
        Champ("matricule", "Matricule salarié", True, "M0001", _aliases("Matricule salarié", "matricule", "matricule salarie")),
        Champ("numero_contrat", "N° contrat", True, "C0001", _aliases("N° contrat", "numero contrat", "contrat")),
        Champ("type_contrat_travail", "Type de contrat", True, "10", _aliases("Type de contrat", "type contrat", "type contrat travail"), "10 = CDI, 29 = CDD, 18 = apprentissage, 28 = professionnalisation"),
        Champ("statut_professionnel", "Statut professionnel", True, "1", _aliases("Statut professionnel", "statut"), "1 = cadre, 2 = non-cadre, 3 = ouvrier/employé"),
        Champ("date_debut_contrat", "Date de début", True, "2024-01-15", _aliases("Date de début", "date debut", "debut contrat")),
        Champ("date_fin_previsionnelle_contrat", "Date de fin (CDD)", False, "2025-01-14", _aliases("Date de fin (CDD)", "date fin", "fin contrat", "date fin previsionnelle")),
        Champ("date_anciennete", "Date d'ancienneté", False, "2024-01-15", _aliases("Date d'ancienneté", "date anciennete")),
        Champ("salaire_mensuel", "Salaire mensuel brut", False, "350000", _aliases("Salaire mensuel brut", "salaire mensuel", "salaire brut", "salaire")),
        Champ("salaire_horaire", "Salaire horaire", False, "0", _aliases("Salaire horaire", "taux horaire")),
        Champ("type_salaire", "Type de salaire", False, "Mensuel", _aliases("Type de salaire", "type salaire"), "Mensuel ou Horaire"),
        Champ("unite_temps", "Unité de temps", False, "Heures", _aliases("Unité de temps", "unite temps"), "Heures ou Jours"),
        Champ("sursalaire", "Sursalaire", False, "0", _aliases("Sursalaire",)),
        Champ("indemnite_transport", "Indemnité de transport", False, "30000", _aliases("Indemnité de transport", "indemnite transport")),
        Champ("dotation_telephonique", "Dotation téléphonique", False, "10000", _aliases("Dotation téléphonique", "dotation telephone")),
        Champ("ccn", "CCN (IDCC)", False, "0", _aliases("CCN (IDCC)", "ccn", "idcc")),
        Champ("emploi", "Poste / emploi", False, "Comptable", _aliases("Poste / emploi", "poste", "emploi")),
    ),
}

TYPES_LIBELLES = {
    "etablissements": "Établissements",
    "salaries": "Salariés",
    "contrats": "Contrats",
}

TYPES_DESCRIPTIONS = {
    "etablissements": "Sites, sièges et filiales de l'entreprise (code, raison sociale, adresse, paramètres de base).",
    "salaries": "Fiches du personnel : identité, situation familiale, coordonnées, IBAN. L'établissement doit exister.",
    "contrats": "Contrats de travail : classification, dates, rémunération. Le salarié et l'établissement doivent exister.",
}


# ─────────────────────────────────────────
#  Utilitaires de lecture et de conversion
# ─────────────────────────────────────────

def _normaliser_entete(value: Any) -> str:
    texte = str(value or "").strip().lower()
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = re.sub(r"[^a-z0-9]+", " ", texte)
    return re.sub(r"\s+", " ", texte).strip()


def _texte(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    texte = str(value).strip()
    return texte or None


def _date(value: Any) -> Optional[date]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    texte = str(value).strip()
    for format_ in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(texte, format_).date()
        except ValueError:
            continue
    raise ValueError("date invalide (attendu AAAA-MM-JJ ou JJ/MM/AAAA)")


def _decimal(value: Any) -> Optional[float]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    texte = str(value).strip().replace(" ", "").replace("\u00a0", "").replace(",", ".")
    try:
        return float(texte)
    except ValueError:
        raise ValueError("valeur numérique invalide")


def _entier(value: Any) -> Optional[int]:
    decimal = _decimal(value)
    return None if decimal is None else int(round(decimal))


def _booleen(value: Any) -> Optional[bool]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        return value
    texte = _normaliser_entete(value)
    if texte in ("oui", "vrai", "true", "1", "x"):
        return True
    if texte in ("non", "faux", "false", "0"):
        return False
    raise ValueError("valeur booléenne invalide (oui/non)")


def _email(value: Any) -> Optional[str]:
    texte = _texte(value)
    if texte is None:
        return None
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", texte):
        raise ValueError("adresse email invalide")
    return texte


def _iban(value: Any) -> Optional[str]:
    texte = _texte(value)
    if texte is None:
        return None
    compact = re.sub(r"\s+", "", texte).upper()
    if not re.match(r"^[A-Z]{2}[0-9A-Z]{13,32}$", compact):
        raise ValueError("IBAN invalide")
    return compact


def _civilite(value: Any) -> Optional[str]:
    texte = _normaliser_entete(value)
    if not texte:
        return None
    if texte in ("m", "m.", "monsieur", "mr"):
        return "M."
    if texte in ("mme", "mme.", "madame", "mlle", "mademoiselle"):
        return "MME"
    raise ValueError("civilité invalide (M. ou MME)")


def _situation(value: Any) -> Optional[str]:
    texte = _normaliser_entete(value)
    if not texte:
        return None
    # « Marié(e) », « Divorcé(e) », « Veuf(ve) » : la parenthèse devient un
    # espace après normalisation ; on retire la terminaison correspondante.
    for suffixe in (" ve", " e"):
        if texte.endswith(suffixe):
            texte = texte[: -len(suffixe)].strip()
            break
    correspondances = {
        "celibataire": "Célibataire",
        "marie": "Marié(e)",
        "mariee": "Marié(e)",
        "divorce": "Divorcé(e)",
        "divorcee": "Divorcé(e)",
        "veuf": "Veuf(ve)",
        "veuve": "Veuf(ve)",
    }
    if texte in correspondances:
        return correspondances[texte]
    raise ValueError("situation matrimoniale invalide")


def _type_contrat(value: Any) -> Optional[int]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    texte = _normaliser_entete(value)
    correspondances = {
        "10": 10, "cdi": 10,
        "29": 29, "cdd": 29,
        "18": 18, "apprentissage": 18, "contrat apprentissage": 18,
        "28": 28, "professionnalisation": 28,
    }
    if texte in correspondances:
        return correspondances[texte]
    raise ValueError("type de contrat invalide (10, 29, 18 ou 28)")


def _statut_professionnel(value: Any) -> Optional[int]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    texte = _normaliser_entete(value)
    correspondances = {
        "1": 1, "cadre": 1,
        "2": 2, "non cadre": 2,
        "3": 3, "ouvrier": 3, "employe": 3, "ouvrier employe": 3,
    }
    if texte in correspondances:
        return correspondances[texte]
    raise ValueError("statut professionnel invalide (1, 2 ou 3)")


def _type_salaire(value: Any) -> Optional[str]:
    texte = _normaliser_entete(value)
    if not texte:
        return None
    if texte in ("mensuel", "mensuelle"):
        return "Mensuel"
    if texte in ("horaire", "hourly"):
        return "Horaire"
    raise ValueError("type de salaire invalide (Mensuel ou Horaire)")


def _unite_temps(value: Any) -> Optional[str]:
    texte = _normaliser_entete(value)
    if not texte:
        return None
    if texte in ("heures", "heure", "h"):
        return "Heures"
    if texte in ("jours", "jour", "j"):
        return "Jours"
    raise ValueError("unité de temps invalide (Heures ou Jours)")


PARSEURS = {
    "date": _date,
    "decimal": _decimal,
    "entier": _entier,
    "booleen": _booleen,
    "email": _email,
    "iban": _iban,
    "civilite": _civilite,
    "situation": _situation,
    "type_contrat": _type_contrat,
    "statut_professionnel": _statut_professionnel,
    "type_salaire": _type_salaire,
    "unite_temps": _unite_temps,
}

#: Type de parseur à appliquer, champ par champ.
PARSEURS_CHAMPS = {
    "etablissements": {
        "taux_at": "decimal",
        "date_creation": "date",
        "email": "email",
    },
    "salaries": {
        "date_naissance": "date",
        "enfants_charge": "entier",
        "email": "email",
        "iban": "iban",
        "expatrie": "booleen",
        "is_active": "booleen",
        "civilite": "civilite",
        "situation_matrimoniale": "situation",
    },
    "contrats": {
        "type_contrat_travail": "type_contrat",
        "statut_professionnel": "statut_professionnel",
        "date_debut_contrat": "date",
        "date_fin_previsionnelle_contrat": "date",
        "date_anciennete": "date",
        "salaire_mensuel": "decimal",
        "salaire_horaire": "decimal",
        "sursalaire": "decimal",
        "indemnite_transport": "decimal",
        "dotation_telephonique": "decimal",
        "ccn": "entier",
        "type_salaire": "type_salaire",
        "unite_temps": "unite_temps",
    },
}


# ─────────────────────────────────────────
#  Lecture du fichier
# ─────────────────────────────────────────

def extension_fichier(nom_fichier: str) -> str:
    return Path(nom_fichier or "").suffix.lower()


def verifier_fichier(nom_fichier: str, taille: int) -> str:
    extension = extension_fichier(nom_fichier)
    if extension not in EXTENSIONS_AUTORISEES:
        raise ValueError("Format non pris en charge : utilisez un fichier .xlsx, .xlsm ou .csv.")
    if taille <= 0:
        raise ValueError("Le fichier est vide.")
    if taille > MAX_IMPORT_BYTES:
        raise ValueError("Fichier trop volumineux (25 Mo maximum).")
    return extension


def _lire_xlsx(contenu: bytes) -> tuple[list[str], list[list[Any]]]:
    try:
        classeur = load_workbook(io.BytesIO(contenu), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Fichier Excel illisible ou corrompu.") from exc
    feuille = classeur["Données"] if "Données" in classeur.sheetnames else classeur.active
    lignes = []
    for ligne in feuille.iter_rows(values_only=True):
        valeurs = list(ligne)
        if all(v is None or (isinstance(v, str) and not v.strip()) for v in valeurs):
            continue
        lignes.append(valeurs)
    classeur.close()
    if not lignes:
        raise ValueError("Le fichier ne contient aucune ligne.")
    entetes = [str(v).strip() if v is not None else "" for v in lignes[0]]
    return entetes, lignes[1:]


def _lire_csv(contenu: bytes) -> tuple[list[str], list[list[Any]]]:
    try:
        texte = contenu.decode("utf-8-sig")
    except UnicodeDecodeError:
        texte = contenu.decode("latin-1")
    if not texte.strip():
        raise ValueError("Le fichier ne contient aucune ligne.")
    echantillon = texte[:4096]
    try:
        dialecte = csv.Sniffer().sniff(echantillon, delimiters=";,\t")
        separateur = dialecte.delimiter
    except csv.Error:
        separateur = ";"
    lignes = list(csv.reader(io.StringIO(texte), delimiter=separateur))
    lignes = [ligne for ligne in lignes if any((cellule or "").strip() for cellule in ligne)]
    if not lignes:
        raise ValueError("Le fichier ne contient aucune ligne.")
    entetes = [(cellule or "").strip() for cellule in lignes[0]]
    return entetes, [list(ligne) for ligne in lignes[1:]]


def lire_fichier(nom_fichier: str, contenu: bytes) -> tuple[list[str], list[list[Any]]]:
    extension = extension_fichier(nom_fichier)
    if extension == ".csv":
        return _lire_csv(contenu)
    return _lire_xlsx(contenu)


# ─────────────────────────────────────────
#  Construction du mapping
# ─────────────────────────────────────────

def _mapping_automatique(type_import: str, entetes: list[str]) -> dict[str, int]:
    normalisees = [_normaliser_entete(entete) for entete in entetes]
    mapping: dict[str, int] = {}
    for champ in CHAMPS[type_import]:
        candidats = {_normaliser_entete(champ.cle), _normaliser_entete(champ.libelle)}
        candidats.update(_normaliser_entete(alias) for alias in champ.aliases)
        for index, entete in enumerate(normalisees):
            if entete and entete in candidats:
                mapping[champ.cle] = index
                break
    return mapping


def construire_mapping(type_import: str, entetes: list[str], mapping_override: Optional[dict[str, str]] = None) -> tuple[dict[str, int], list[str]]:
    mapping = _mapping_automatique(type_import, entetes)
    if mapping_override:
        index_par_entete = {_normaliser_entete(entete): index for index, entete in enumerate(entetes)}
        for cle, source in mapping_override.items():
            if cle not in {champ.cle for champ in CHAMPS[type_import]}:
                continue
            index = index_par_entete.get(_normaliser_entete(source))
            if index is not None:
                mapping[cle] = index
    manquants = [champ.libelle for champ in CHAMPS[type_import] if champ.obligatoire and champ.cle not in mapping]
    return mapping, manquants


def _valeur_ligne(ligne: list[Any], mapping: dict[str, int], cle: str) -> Any:
    index = mapping.get(cle)
    if index is None or index >= len(ligne):
        return None
    return ligne[index]


# ─────────────────────────────────────────
#  Validation
# ─────────────────────────────────────────

def _erreur(ligne: int, champ: str, message: str, valeur: Any = None) -> dict:
    return {
        "ligne": ligne,
        "champ": champ,
        "message": message,
        "valeur": None if valeur is None else str(valeur)[:200],
    }


def _normaliser_ligne(type_import: str, ligne: list[Any], mapping: dict[str, int], numero: int,
                      erreurs: list[dict]) -> dict:
    donnees: dict[str, Any] = {"_ligne": numero}
    for champ in CHAMPS[type_import]:
        brut = _valeur_ligne(ligne, mapping, champ.cle)
        if champ.obligatoire and (brut is None or (isinstance(brut, str) and not brut.strip())):
            erreurs.append(_erreur(numero, champ.libelle, "Champ obligatoire manquant.", brut))
            continue
        if brut is None or (isinstance(brut, str) and not brut.strip()):
            continue
        parseur = PARSEURS_CHAMPS.get(type_import, {}).get(champ.cle)
        try:
            valeur = PARSEURS[parseur](brut) if parseur else _texte(brut)
        except ValueError as exc:
            erreurs.append(_erreur(numero, champ.libelle, str(exc), brut))
            continue
        if valeur is not None:
            donnees[champ.cle] = valeur
    return donnees


def _valider_etablissements(db: Session, dossier: Dossier, lignes: list[dict], mapping: dict[str, int]) -> tuple[list[dict], list[dict]]:
    erreurs: list[dict] = []
    valides: list[dict] = []
    codes_vus: set[str] = set()
    for index, ligne in enumerate(lignes, start=2):
        avant = len(erreurs)
        donnees = _normaliser_ligne("etablissements", ligne, mapping, index, erreurs)
        if len(erreurs) > avant or not donnees.get("code"):
            continue
        code = str(donnees["code"]).strip()
        if code in codes_vus:
            erreurs.append(_erreur(index, "Code établissement", "Code en double dans le fichier.", code))
            continue
        codes_vus.add(code)
        if "taux_at" in donnees and donnees["taux_at"] is not None and donnees["taux_at"] < 0:
            erreurs.append(_erreur(index, "Taux AT (%)", "Le taux ne peut pas être négatif.", donnees["taux_at"]))
            continue
        valides.append(donnees)
    return valides, erreurs


def _valider_salaries(db: Session, dossier: Dossier, lignes: list[dict], mapping: dict[str, int]) -> tuple[list[dict], list[dict]]:
    erreurs: list[dict] = []
    valides: list[dict] = []
    etabs = {
        etab.code: etab
        for etab in db.query(Etablissement).filter(Etablissement.dossier_id == dossier.id).all()
    }
    cles_vues: set[tuple[str, str]] = set()
    for index, ligne in enumerate(lignes, start=2):
        avant = len(erreurs)
        donnees = _normaliser_ligne("salaries", ligne, mapping, index, erreurs)
        if len(erreurs) > avant:
            continue
        code_etab = str(donnees.get("etablissement_code") or "").strip()
        matricule = str(donnees.get("matricule") or "").strip()
        if not code_etab or not matricule:
            continue
        if code_etab not in etabs:
            erreurs.append(_erreur(index, "Code établissement", "Établissement introuvable dans ce dossier.", code_etab))
            continue
        cle = (code_etab, matricule)
        if cle in cles_vues:
            erreurs.append(_erreur(index, "Matricule", "Matricule en double dans le fichier pour cet établissement.", matricule))
            continue
        cles_vues.add(cle)
        if donnees.get("enfants_charge") is not None and donnees["enfants_charge"] < 0:
            erreurs.append(_erreur(index, "Enfants à charge", "Le nombre d'enfants ne peut pas être négatif.", donnees["enfants_charge"]))
            continue
        valides.append(donnees)
    return valides, erreurs


def _valider_contrats(db: Session, dossier: Dossier, lignes: list[dict], mapping: dict[str, int]) -> tuple[list[dict], list[dict]]:
    erreurs: list[dict] = []
    valides: list[dict] = []
    etabs = {
        etab.code: etab
        for etab in db.query(Etablissement).filter(Etablissement.dossier_id == dossier.id).all()
    }
    salaries = {
        (salarie.etablissement.code, salarie.matricule): salarie
        for salarie in db.query(Salarie).join(Etablissement).filter(Etablissement.dossier_id == dossier.id).all()
    }
    numeros_vus: set[str] = set()
    for index, ligne in enumerate(lignes, start=2):
        avant = len(erreurs)
        donnees = _normaliser_ligne("contrats", ligne, mapping, index, erreurs)
        if len(erreurs) > avant:
            continue
        code_etab = str(donnees.get("etablissement_code") or "").strip()
        matricule = str(donnees.get("matricule") or "").strip()
        numero = str(donnees.get("numero_contrat") or "").strip()
        if not code_etab or not matricule or not numero:
            continue
        if code_etab not in etabs:
            erreurs.append(_erreur(index, "Code établissement", "Établissement introuvable dans ce dossier.", code_etab))
            continue
        if (code_etab, matricule) not in salaries:
            erreurs.append(_erreur(index, "Matricule salarié", "Salarié introuvable : importez d'abord les salariés.", matricule))
            continue
        if numero in numeros_vus:
            erreurs.append(_erreur(index, "N° contrat", "Numéro de contrat en double dans le fichier.", numero))
            continue
        numeros_vus.add(numero)
        debut = donnees.get("date_debut_contrat")
        fin = donnees.get("date_fin_previsionnelle_contrat")
        if debut and fin and fin < debut:
            erreurs.append(_erreur(index, "Date de fin (CDD)", "La date de fin précède la date de début.", fin.isoformat()))
            continue
        mensuel = donnees.get("salaire_mensuel") or 0
        horaire = donnees.get("salaire_horaire") or 0
        if mensuel < 0 or horaire < 0:
            erreurs.append(_erreur(index, "Salaire", "Le salaire ne peut pas être négatif.", mensuel or horaire))
            continue
        if mensuel <= 0 and horaire <= 0:
            erreurs.append(_erreur(index, "Salaire mensuel brut", "Renseignez un salaire mensuel ou horaire supérieur à 0.", None))
            continue
        valides.append(donnees)
    return valides, erreurs


VALIDATEURS = {
    "etablissements": _valider_etablissements,
    "salaries": _valider_salaries,
    "contrats": _valider_contrats,
}


# ─────────────────────────────────────────
#  Analyse
# ─────────────────────────────────────────

@dataclass
class Analyse:
    entetes: list[str] = field(default_factory=list)
    mapping: dict[str, str] = field(default_factory=dict)
    champs_manquants: list[str] = field(default_factory=list)
    total_lignes: int = 0
    valides: list[dict] = field(default_factory=list)
    erreurs: list[dict] = field(default_factory=list)
    apercu: list[dict] = field(default_factory=list)

    @property
    def lignes_erreurs(self) -> int:
        return len({erreur["ligne"] for erreur in self.erreurs})

    @property
    def statut(self) -> str:
        if self.champs_manquants:
            return "mapping_requis"
        return "pret"


def analyser_contenu(
    db: Session,
    dossier: Dossier,
    type_import: str,
    nom_fichier: str,
    contenu: bytes,
    mapping_override: Optional[dict[str, str]] = None,
) -> Analyse:
    if type_import not in CHAMPS:
        raise ValueError("Type d'import inconnu.")
    entetes, lignes = lire_fichier(nom_fichier, contenu)
    mapping_index, manquants = construire_mapping(type_import, entetes, mapping_override)
    mapping_public = {cle: entetes[index] for cle, index in mapping_index.items()}
    analyse = Analyse(entetes=entetes, mapping=mapping_public, total_lignes=len(lignes))
    if manquants:
        analyse.champs_manquants = manquants
        return analyse

    valides, erreurs = VALIDATEURS[type_import](db, dossier, lignes, mapping_index)
    analyse.total_lignes = len(lignes)
    analyse.valides = valides
    analyse.erreurs = erreurs
    analyse.apercu = [
        {
            cle: (valeur.isoformat() if isinstance(valeur, date) else valeur)
            for cle, valeur in ligne.items()
            if cle != "_ligne"
        }
        for ligne in valides[:8]
    ]
    return analyse


# ─────────────────────────────────────────
#  Exécution (upserts idempotents)
# ─────────────────────────────────────────

def _champs_modifiables(type_import: str, donnees: dict) -> dict:
    autorises = {
        "etablissements": (
            "raison_sociale", "sigle", "numero_rccm", "activite", "adresse_commune",
            "adresse_pays", "telephone", "email", "taux_at", "cnps_matricule",
            "dgi_compte_contribuable", "date_creation",
        ),
        "salaries": (
            "nom", "prenom", "civilite", "date_naissance", "lieu_naissance",
            "numero_securite_sociale", "situation_matrimoniale", "enfants_charge",
            "email", "telephone", "adresse", "ville", "pays", "iban", "bic",
            "expatrie", "is_active",
        ),
        "contrats": (
            "type_contrat_travail", "statut_professionnel", "date_debut_contrat",
            "date_fin_previsionnelle_contrat", "date_anciennete", "salaire_mensuel",
            "salaire_horaire", "type_salaire", "unite_temps", "sursalaire",
            "indemnite_transport", "dotation_telephonique", "ccn", "emploi", "statut",
        ),
    }[type_import]
    resultat = {cle: valeur for cle, valeur in donnees.items() if cle in autorises}
    if "date_naissance" in resultat and isinstance(resultat["date_naissance"], date):
        resultat["date_naissance"] = datetime.combine(resultat["date_naissance"], datetime.min.time())
    # Les dates de contrat sont stockées en texte ISO dans le modèle.
    for cle in ("date_debut_contrat", "date_fin_previsionnelle_contrat", "date_anciennete"):
        if isinstance(resultat.get(cle), date):
            resultat[cle] = resultat[cle].isoformat()
    return resultat


def _appliquer_etablissement(db: Session, dossier: Dossier, donnees: dict) -> bool:
    code = str(donnees["code"]).strip()
    etab = (
        db.query(Etablissement)
        .filter(Etablissement.dossier_id == dossier.id, Etablissement.code == code)
        .first()
    )
    cree = etab is None
    if etab is None:
        etab = Etablissement(
            dossier_id=dossier.id,
            code=code,
            raison_sociale=str(donnees.get("raison_sociale") or code),
        )
        db.add(etab)
        db.flush()
    for cle, valeur in _champs_modifiables("etablissements", donnees).items():
        setattr(etab, cle, valeur)
    return cree


def _appliquer_salarie(db: Session, dossier: Dossier, donnees: dict) -> bool:
    etab = (
        db.query(Etablissement)
        .filter(Etablissement.dossier_id == dossier.id, Etablissement.code == str(donnees["etablissement_code"]).strip())
        .first()
    )
    if etab is None:
        raise ValueError("Établissement introuvable.")
    matricule = str(donnees["matricule"]).strip()
    salarie = (
        db.query(Salarie)
        .filter(Salarie.etablissement_id == etab.id, Salarie.matricule == matricule)
        .first()
    )
    cree = salarie is None
    if salarie is None:
        salarie = Salarie(
            etablissement_id=etab.id,
            matricule=matricule,
            nom=str(donnees.get("nom") or ""),
            prenom=str(donnees.get("prenom") or ""),
            is_active=True,
        )
        db.add(salarie)
        db.flush()
    for cle, valeur in _champs_modifiables("salaries", donnees).items():
        setattr(salarie, cle, valeur)
    return cree


def _appliquer_contrat(db: Session, dossier: Dossier, donnees: dict) -> bool:
    code_etab = str(donnees["etablissement_code"]).strip()
    matricule = str(donnees["matricule"]).strip()
    numero = str(donnees["numero_contrat"]).strip()
    etab = (
        db.query(Etablissement)
        .filter(Etablissement.dossier_id == dossier.id, Etablissement.code == code_etab)
        .first()
    )
    if etab is None:
        raise ValueError("Établissement introuvable.")
    salarie = (
        db.query(Salarie)
        .filter(Salarie.etablissement_id == etab.id, Salarie.matricule == matricule)
        .first()
    )
    if salarie is None:
        raise ValueError("Salarié introuvable.")
    contrat = (
        db.query(Contrat)
        .filter(Contrat.dossier_id == dossier.id, Contrat.numero_contrat == numero)
        .first()
    )
    cree = contrat is None
    if contrat is None:
        contrat = Contrat(
            dossier_id=dossier.id,
            salarie_id=salarie.id,
            etablissement_id=etab.id,
            code_etablissement=etab.code,
            matricule_salarie=salarie.matricule,
            numero_contrat=numero,
            type_contrat_travail=int(donnees.get("type_contrat_travail") or 10),
            statut_professionnel=int(donnees.get("statut_professionnel") or 2),
            salaire_mensuel=float(donnees.get("salaire_mensuel") or 0),
            type_salaire=str(donnees.get("type_salaire") or "Mensuel"),
            statut="actif",
        )
        db.add(contrat)
        db.flush()
    for cle, valeur in _champs_modifiables("contrats", donnees).items():
        setattr(contrat, cle, valeur)
    contrat.salarie_id = salarie.id
    contrat.etablissement_id = etab.id
    contrat.code_etablissement = etab.code
    contrat.matricule_salarie = salarie.matricule

    if db.query(Horaires).filter(Horaires.contrat_id == contrat.id).first() is None:
        db.add(Horaires(contrat_id=contrat.id))
    if db.query(JoursHebdomadaires).filter(JoursHebdomadaires.contrat_id == contrat.id).first() is None:
        db.add(JoursHebdomadaires(contrat_id=contrat.id))
    return cree


APPLIQUER = {
    "etablissements": _appliquer_etablissement,
    "salaries": _appliquer_salarie,
    "contrats": _appliquer_contrat,
}


@dataclass
class Execution:
    crees: int = 0
    mis_a_jour: int = 0
    ignores: int = 0
    erreurs: list[dict] = field(default_factory=list)


def executer_analyse(db: Session, job, analyse: Analyse, ignorer_erreurs: bool = False) -> Execution:
    if analyse.champs_manquants:
        raise ValueError("Le mapping des colonnes est incomplet.")
    if analyse.erreurs and not ignorer_erreurs:
        raise ValueError(
            "Le fichier contient des erreurs : corrigez-le ou choisissez d'importer uniquement les lignes valides."
        )
    execution = Execution()
    for donnees in analyse.valides:
        ligne = int(donnees.get("_ligne") or 0)
        try:
            with db.begin_nested():
                cree = APPLIQUER[job.type_import](db, job.dossier, donnees)
            if cree:
                execution.crees += 1
            else:
                execution.mis_a_jour += 1
        except Exception as exc:  # noqa: BLE001
            execution.erreurs.append(
                _erreur(ligne, None, f"Import impossible : {exc}")
            )
            execution.ignores += 1
    db.commit()
    return execution


# ─────────────────────────────────────────
#  Modèles Excel
# ─────────────────────────────────────────

def _style_entete(cellule) -> None:
    cellule.font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
    cellule.fill = PatternFill("solid", fgColor=NAVY)
    cellule.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cellule.border = Border(bottom=Side(style="thin", color=GREEN))


def generer_modele(type_import: str) -> bytes:
    if type_import not in CHAMPS:
        raise ValueError("Type d'import inconnu.")
    classeur = Workbook()
    feuille = classeur.active
    feuille.title = "Données"
    champs = CHAMPS[type_import]
    for index, champ in enumerate(champs, start=1):
        cellule = feuille.cell(row=1, column=index, value=f"{champ.libelle} *" if champ.obligatoire else champ.libelle)
        _style_entete(cellule)
        feuille.column_dimensions[get_column_letter(index)].width = max(14, min(32, len(champ.libelle) + 4))
    feuille.row_dimensions[1].height = 32
    feuille.freeze_panes = "A2"
    feuille.auto_filter.ref = f"A1:{get_column_letter(len(champs))}1"

    aide = classeur.create_sheet("Instructions")
    aide.column_dimensions["A"].width = 26
    aide.column_dimensions["B"].width = 70
    aide.column_dimensions["C"].width = 30
    titre = aide.cell(row=1, column=1, value=f"Modèle d'import — {TYPES_LIBELLES[type_import]}")
    titre.font = Font(bold=True, size=14, color=NAVY)
    aide.cell(row=2, column=1, value=TYPES_DESCRIPTIONS[type_import]).font = Font(italic=True, color="475569")
    aide.cell(row=4, column=1, value="Colonne").font = Font(bold=True)
    aide.cell(row=4, column=2, value="Obligatoire / aide").font = Font(bold=True)
    aide.cell(row=4, column=3, value="Exemple").font = Font(bold=True)
    for index, champ in enumerate(champs, start=5):
        aide.cell(row=index, column=1, value=champ.libelle)
        aide.cell(row=index, column=2, value=("Obligatoire. " if champ.obligatoire else "") + (champ.aide or "Facultatif."))
        aide.cell(row=index, column=3, value=champ.exemple)
    aide.cell(row=len(champs) + 7, column=1, value="Rappels").font = Font(bold=True, color=GREEN)
    aide.cell(row=len(champs) + 8, column=1, value="• Une ligne = un enregistrement. Ne modifiez pas la ligne d'en-tête.")
    aide.cell(row=len(champs) + 9, column=1, value="• Les dates s'écrivent AAAA-MM-JJ (ou JJ/MM/AAAA).")
    aide.cell(row=len(champs) + 10, column=1, value="• Les montants sont en FCFA, sans espace ni devise.")
    aide.cell(row=len(champs) + 11, column=1, value="• Importez d'abord les établissements, puis les salariés, puis les contrats.")
    aide.cell(row=len(champs) + 12, column=1, value="• L'analyse à blanc ne modifie rien : corrigez le fichier avant d'exécuter.")

    flux = io.BytesIO()
    classeur.save(flux)
    return flux.getvalue()


# ─────────────────────────────────────────
#  Stockage du fichier
# ─────────────────────────────────────────

def enregistrer_fichier(nom_fichier: str, contenu: bytes) -> str:
    try:
        DOSSIER_IMPORTS.mkdir(parents=True, exist_ok=True)
        nom_securise = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(nom_fichier).name)[:120] or "import"
        chemin = DOSSIER_IMPORTS / f"{uuid.uuid4().hex}_{nom_securise}"
        chemin.write_bytes(contenu)
        return str(chemin)
    except OSError as exc:
        raise RuntimeError(
            "Impossible d'enregistrer le fichier sur le serveur. "
            "Vérifiez les droits d'écriture du dossier d'imports (uploads/imports) "
            "ou montez un volume dédié."
        ) from exc


def lire_fichier_job(chemin: Optional[str]) -> bytes:
    if not chemin:
        raise ValueError("Fichier d'import introuvable.")
    path = Path(chemin)
    if not path.exists() or not path.is_file():
        raise ValueError("Fichier d'import introuvable.")
    return path.read_bytes()


def supprimer_fichier(chemin: Optional[str]) -> None:
    if not chemin:
        return
    try:
        Path(chemin).unlink(missing_ok=True)
    except OSError:
        pass


def rapport_json(job) -> dict:
    try:
        return json.loads(job.rapport or "{}")
    except (TypeError, ValueError):
        return {}
