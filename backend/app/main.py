from fastapi import FastAPI, APIRouter, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, dossiers, etablissements, salaries, contrats, variables, bulletins, constantes, plan_paie, reclamations, secteurs, salaries_hr, departements, import_export_excel
from app.database import Base, engine, SessionLocal
from app.database_seeder import seed_database
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sqlalchemy.exc import IntegrityError
import logging


logger = logging.getLogger("app")

# Initialisation Sentry/Bugsink
if settings.BUGSINK_DSN:
    sentry_sdk.init(
        dsn=settings.BUGSINK_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=1.0,
    )

# En mode développement avec SQLite, on initialise automatiquement les tables
if settings.DATABASE_URL.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)

# Peuplement des constantes et plan de paie au démarrage
db = SessionLocal()
try:
    seed_database(db)
finally:
    db.close()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/api/v1/docs" if settings.DEBUG else None,
    redoc_url="/api/v1/redoc" if settings.DEBUG else None,
)



@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    logger.error(f"Database IntegrityError: {str(exc)}")
    detail = "Cette ressource existe déjà (violation de contrainte d'unicité)."
    err_str = str(exc).lower()
    if "key (code)=" in err_str or "unique constraint" in err_str:
        detail = "Ce code ou identifiant unique est déjà utilisé."
    elif "key (email)=" in err_str:
        detail = "Cette adresse email est déjà utilisée."
    elif "key (matricule)=" in err_str:
        detail = "Ce matricule est déjà utilisé."
    
    return JSONResponse(
        status_code=400,
        content={"detail": detail}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Global unhandled exception:")
    if settings.BUGSINK_DSN:
        sentry_sdk.capture_exception(exc)
    # Le message du backend ne doit pas aller textuellement au frontend pour les erreurs serveur inattendues
    return JSONResponse(
        status_code=500,
        content={"detail": "Une erreur interne du serveur est survenue. L'incident a été enregistré."}
    )



# Configuration des CORS pour autoriser l'accès depuis le frontend (ex: Supabase, localhost)

api_router = APIRouter(
    prefix="/api/v1",

)

api_router.include_router(auth.router)
api_router.include_router(dossiers.router)
api_router.include_router(etablissements.router)
api_router.include_router(salaries.router)
api_router.include_router(contrats.router)
api_router.include_router(variables.router)
api_router.include_router(bulletins.router)
api_router.include_router(constantes.router)
api_router.include_router(plan_paie.router)
api_router.include_router(reclamations.router)
api_router.include_router(secteurs.router)
api_router.include_router(salaries_hr.router)
api_router.include_router(departements.router)
api_router.include_router(import_export_excel.router)

import os
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



from fastapi.responses import HTMLResponse
import os



app.frontend("/api/documentation", directory="./frontend")

