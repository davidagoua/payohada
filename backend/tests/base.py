"""Harnais commun des tests PayOHADA.

L'environnement est configuré AVANT l'import de l'application, car le moteur
SQLAlchemy et les paramètres sont instanciés à l'import des modules `app.*`.
"""
import os
import pathlib
import sys

BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

TEST_DB_PATH = pathlib.Path(__file__).resolve().parent / "_test_payohada.sqlite3"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SUPABASE_JWT_SECRET"] = "secret-de-test-uniquement-pour-la-suite"
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_ANON_KEY"] = ""
os.environ["DEBUG"] = "true"
os.environ["BUGSINK_DSN"] = ""
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["LOGIN_MAX_ATTEMPTS"] = "100"
os.environ["LOGIN_WINDOW_SECONDS"] = "60"
os.environ["MAX_UPLOAD_SIZE_BYTES"] = "2048"
os.environ["ALLOWED_UPLOAD_EXTENSIONS"] = ".pdf,.txt"
# Le fichier .env du dépôt ne doit pas influencer les tests.
os.environ["SMTP_HOST"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine, get_db  # noqa: E402
from app.database_seeder import seed_database  # noqa: E402
from app.main import app  # noqa: E402
from app.models import models as M  # noqa: E402
from app.services.rate_limit import reinitialiser_tous_les_limiteurs  # noqa: E402
from app.services.security import create_access_token, get_password_hash  # noqa: E402


def reset_database() -> None:
    """Repart d'une base vierge et rejoue le peuplement des référentiels."""
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    reinitialiser_tous_les_limiteurs()


def _override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


# ─────────────────────────────────────────
#  Fabriques de données
# ─────────────────────────────────────────

DEFAULT_PASSWORD = "MotDePasse!2024"

#: Préfixe de l'API, partagé par les modules de test.
API = "/api/v1"


def make_user(
    db,
    email: str,
    role: str = "cabinet",
    password: str = DEFAULT_PASSWORD,
    dossier_id=None,
    salarie_id=None,
    is_admin: bool = False,
    must_change_password: bool = False,
):
    user = M.Utilisateur(
        email=email,
        nom="Nom",
        prenom="Prenom",
        hashed_password=get_password_hash(password) if password else None,
        supabase_uid=f"uid-{email}",
        is_active=True,
        is_admin=is_admin,
        must_change_password=must_change_password,
        role=role,
        dossier_id=dossier_id,
        salarie_id=salarie_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user) -> dict:
    token = create_access_token({"sub": user.supabase_uid, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


def make_dossier(db, owner, code: str = "DOS001", nom: str = "Entreprise Test"):
    dossier = M.Dossier(code=code, nom_dossier=nom, utilisateur_id=owner.id, pays="Côte d'Ivoire")
    db.add(dossier)
    db.commit()
    db.refresh(dossier)
    return dossier


def make_etablissement(db, dossier, code: str = "ETB1", taux_at: float = 2.0):
    etab = M.Etablissement(
        dossier_id=dossier.id,
        code=code,
        raison_sociale=f"Ets {code}",
        taux_at=taux_at,
    )
    db.add(etab)
    db.commit()
    db.refresh(etab)
    return etab


def make_salarie(db, etab, matricule: str = "M001", **kwargs):
    salarie = M.Salarie(
        etablissement_id=etab.id,
        matricule=matricule,
        nom=kwargs.pop("nom", "Kouassi"),
        prenom=kwargs.pop("prenom", "Aya"),
        situation_matrimoniale=kwargs.pop("situation_matrimoniale", "Marié"),
        enfants_charge=kwargs.pop("enfants_charge", 2),
        email=kwargs.pop("email", None),
        is_active=True,
        **kwargs,
    )
    db.add(salarie)
    db.commit()
    db.refresh(salarie)
    return salarie


def make_contrat(
    db,
    dossier,
    etab,
    salarie,
    numero: str = "C001",
    salaire_mensuel: float = 300000.0,
    horaire_hebdo: float = 40.0,
    horaire_mensuel: float = 173.33,
    type_salaire: str = "Mensuel",
    salaire_horaire: float = 0.0,
    **kwargs,
):
    contrat = M.Contrat(
        dossier_id=dossier.id,
        salarie_id=salarie.id,
        etablissement_id=etab.id,
        code_etablissement=etab.code,
        matricule_salarie=salarie.matricule,
        numero_contrat=numero,
        type_contrat_travail=10,
        statut_professionnel=1,
        salaire_mensuel=salaire_mensuel,
        salaire_horaire=salaire_horaire,
        type_salaire=type_salaire,
        **kwargs,
    )
    db.add(contrat)
    db.commit()
    db.refresh(contrat)
    db.add(M.Horaires(
        contrat_id=contrat.id,
        horaire_travail=horaire_mensuel,
        horaire_hebdo=horaire_hebdo,
    ))
    db.commit()
    db.refresh(contrat)
    return contrat


def make_tenant(db, email_prefix: str = "cabinet"):
    """Crée un cabinet avec un dossier complet (établissement, salarié, contrat)."""
    user = make_user(db, f"{email_prefix}@exemple.ci", role="cabinet")
    dossier = make_dossier(db, user, code=f"D{abs(hash(email_prefix)) % 100000:05d}")
    etab = make_etablissement(db, dossier, code=f"E{abs(hash(email_prefix)) % 10000:04d}")
    salarie = make_salarie(db, etab, matricule=f"M{abs(hash(email_prefix)) % 10000:04d}")
    contrat = make_contrat(db, dossier, etab, salarie, numero=f"C{abs(hash(email_prefix)) % 10000:04d}")
    return {
        "user": user,
        "dossier": dossier,
        "etablissement": etab,
        "salarie": salarie,
        "contrat": contrat,
    }
