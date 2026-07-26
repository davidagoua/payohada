import sys
import os

# Add the current directory to sys.path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, engine
from app.models import models

def main():
    print("Synchornisation du schéma de base de données...")
    print(f"DATABASE_URL en cours d'utilisation.")
    Base.metadata.create_all(bind=engine)
    print("Tables créées/mises à jour avec succès !")

if __name__ == "__main__":
    main()
