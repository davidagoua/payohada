from fastapi import FastAPI
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
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Configuration des CORS pour autoriser l'accès depuis le frontend (ex: Supabase, localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrement des routeurs de l'API
app.include_router(auth.router)
app.include_router(dossiers.router)
app.include_router(etablissements.router)
app.include_router(salaries.router)
app.include_router(contrats.router)
app.include_router(variables.router)
app.include_router(bulletins.router)
app.include_router(constantes.router)
app.include_router(plan_paie.router)


from fastapi.responses import HTMLResponse
import os

@app.get("/", response_class=HTMLResponse)
def read_root():
    """Affiche la landing page de Payohada."""
    path_to_landing = os.path.join(os.path.dirname(__file__), "../frontend/index.html")
    if os.path.exists(path_to_landing):
        with open(path_to_landing, "r", encoding="utf-8") as f:
            html_content = f.read()
            html_content = html_content.replace("{{SUPABASE_URL}}", settings.SUPABASE_URL)
            html_content = html_content.replace("{{SUPABASE_ANON_KEY}}", settings.SUPABASE_ANON_KEY)
            return HTMLResponse(content=html_content, status_code=200)
    return HTMLResponse(content="<h1>Bienvenue sur l'API Payohada</h1>", status_code=200)
