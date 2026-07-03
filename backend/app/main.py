from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, dossiers, etablissements, salaries, contrats, variables, bulletins, constantes, plan_paie
from app.database import Base, engine, SessionLocal
from app.database_seeder import seed_database

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



# Configuration des CORS pour autoriser l'accès depuis le frontend (ex: Supabase, localhost)

api_router = APIRouter(
    prefix="/api/v1",
    tags=["v1"]
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

