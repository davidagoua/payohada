import logging
import os

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.routers import (
    auth, dossiers, etablissements, salaries, contrats, variables, bulletins,
    constantes, plan_paie, reclamations, secteurs, salaries_hr, departements,
    import_export_excel, calculs_ci,
)
from app.database import Base, engine, SessionLocal
from app.database_seeder import seed_database

logger = logging.getLogger("app")

# Initialisation Sentry/Bugsink (uniquement si un DSN est configuré)
if settings.BUGSINK_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration

    sentry_sdk.init(
        dsn=settings.BUGSINK_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.2,
    )

# En mode développement avec SQLite, on initialise automatiquement les tables
if settings.DATABASE_URL.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)

# Peuplement des constantes et du plan de paie au démarrage.
# L'opération est idempotente et n'écrase jamais une valeur administrateur :
# elle peut donc tourner sans risque en production.
db = SessionLocal()
try:
    seed_database(db)
except Exception:  # pragma: no cover - le démarrage ne doit pas échouer
    logger.exception("Échec du peuplement initial des référentiels de paie")
finally:
    db.close()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/api/v1/docs" if settings.DEBUG else None,
    redoc_url="/api/v1/redoc" if settings.DEBUG else None,
)

# CORS : origines explicites uniquement. `allow_origins=["*"]` combiné à
# `allow_credentials=True` est interdit par la spécification CORS et ouvre
# l'API à n'importe quel site.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
)


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    logger.error("Database IntegrityError: %s", str(exc))
    detail = "Cette ressource existe déjà (violation de contrainte d'unicité)."
    err_str = str(exc).lower()
    if "key (code)=" in err_str or "unique constraint" in err_str:
        detail = "Ce code ou identifiant unique est déjà utilisé."
    elif "key (email)=" in err_str:
        detail = "Cette adresse email est déjà utilisée."
    elif "key (matricule)=" in err_str:
        detail = "Ce matricule est déjà utilisé."

    return JSONResponse(status_code=400, content={"detail": detail})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Global unhandled exception:")
    if settings.BUGSINK_DSN:
        import sentry_sdk
        sentry_sdk.capture_exception(exc)
    # Le message du backend ne doit pas aller textuellement au frontend
    return JSONResponse(
        status_code=500,
        content={"detail": "Une erreur interne du serveur est survenue. L'incident a été enregistré."}
    )


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(dossiers.router)
api_router.include_router(etablissements.router)
api_router.include_router(salaries.router)
api_router.include_router(contrats.router)
api_router.include_router(variables.router)
api_router.include_router(variables.dossier_variables_router)
api_router.include_router(bulletins.router)
api_router.include_router(constantes.router)
api_router.include_router(plan_paie.router)
api_router.include_router(reclamations.router)
api_router.include_router(secteurs.router)
api_router.include_router(salaries_hr.router)
api_router.include_router(departements.router)
api_router.include_router(import_export_excel.router)
api_router.include_router(calculs_ci.router)

app.include_router(api_router)

# NOTE : le routeur d'authentification n'est plus monté une seconde fois à la
# racine (« /auth/... ») : cela dupliquait inutilement la surface d'API.

os.makedirs("uploads", exist_ok=True)

# Le dossier `uploads` n'est plus servi en statique : les pièces jointes RH
# sont accessibles via GET /api/v1/salaries/documents/{filename}, qui applique
# le contrôle de portée.

# Documentation statique optionnelle (présente uniquement si le dossier existe)
_frontend_dir = "./frontend"
if os.path.isdir(_frontend_dir):
    app.frontend("/api/documentation", directory=_frontend_dir)
