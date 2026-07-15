import sqlite3
import os
from pathlib import Path

# Load environment variables manually
env_path = Path(__file__).resolve().parent / ".env"
db_url = None
if env_path.exists():
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                db_url = line.split("DATABASE_URL=")[1].strip()

print("DATABASE_URL:", db_url)

# 1. Update PostgreSQL
if db_url and db_url.startswith("postgresql"):
    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Add expatrie to salaries
        cur.execute("ALTER TABLE salaries ADD COLUMN IF NOT EXISTS expatrie BOOLEAN DEFAULT FALSE;")
        cur.execute("ALTER TABLE salaries ADD COLUMN IF NOT EXISTS situation_matrimoniale VARCHAR(50) DEFAULT NULL;")
        cur.execute("ALTER TABLE salaries ADD COLUMN IF NOT EXISTS enfants_charge INTEGER DEFAULT 0;")
        
        # Add pays to dossiers
        cur.execute("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS pays VARCHAR(100) DEFAULT 'Côte d''Ivoire';")
        
        # Add columns to contrats
        cur.execute("ALTER TABLE contrats ADD COLUMN IF NOT EXISTS unite_temps VARCHAR(10) DEFAULT 'Heures';")
        cur.execute("ALTER TABLE contrats ADD COLUMN IF NOT EXISTS sursalaire DOUBLE PRECISION DEFAULT 0.0;")
        cur.execute("ALTER TABLE contrats ADD COLUMN IF NOT EXISTS indemnite_transport DOUBLE PRECISION DEFAULT 0.0;")
        cur.execute("ALTER TABLE contrats ADD COLUMN IF NOT EXISTS dotation_telephonique DOUBLE PRECISION DEFAULT 0.0;")
        cur.execute("ALTER TABLE contrats ADD COLUMN IF NOT EXISTS mode_calcul VARCHAR(10) DEFAULT 'brut';")
        
        # Add base and taux columns to primes
        cur.execute("ALTER TABLE primes ADD COLUMN IF NOT EXISTS base DOUBLE PRECISION DEFAULT NULL;")
        cur.execute("ALTER TABLE primes ADD COLUMN IF NOT EXISTS taux DOUBLE PRECISION DEFAULT NULL;")
        
        # Add est_persistant column to primes and options
        cur.execute("ALTER TABLE primes ADD COLUMN IF NOT EXISTS est_persistant BOOLEAN DEFAULT FALSE;")
        cur.execute("ALTER TABLE options ADD COLUMN IF NOT EXISTS est_persistant BOOLEAN DEFAULT FALSE;")
        
        # Widen code column in plan_paie to prevent StringDataRightTruncation
        cur.execute("ALTER TABLE plan_paie ALTER COLUMN code TYPE VARCHAR(20);")
        
        # Add salarie_id to utilisateurs
        cur.execute("ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS salarie_id INTEGER REFERENCES salaries(id) ON DELETE CASCADE;")
        
        # Create reclamations table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS reclamations (
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
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_reclamations_salarie ON reclamations (salarie_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_reclamations_bulletin ON reclamations (bulletin_id);")
        
        conn.commit()
        cur.close()
        conn.close()
        print("PostgreSQL database updated successfully.")
    except Exception as e:
        print("Error updating PostgreSQL:", e)
else:
    print("PostgreSQL DATABASE_URL not found or invalid.")
 
# 2. Update SQLite
sqlite_path = Path(__file__).resolve().parent / "paie.db"
if sqlite_path.exists():
    try:
        conn = sqlite_connection = sqlite3.connect(sqlite_path)
        cur = conn.cursor()
        
        # In SQLite, ADD COLUMN does not support IF NOT EXISTS in old versions, so we wrap it
        try:
            cur.execute("ALTER TABLE salaries ADD COLUMN expatrie BOOLEAN DEFAULT 0;")
        except sqlite3.OperationalError:
            print("expatrie column already exists or error in salaries")

        try:
            cur.execute("ALTER TABLE salaries ADD COLUMN situation_matrimoniale VARCHAR(50) DEFAULT NULL;")
        except sqlite3.OperationalError:
            print("situation_matrimoniale column already exists or error in salaries")

        try:
            cur.execute("ALTER TABLE salaries ADD COLUMN enfants_charge INTEGER DEFAULT 0;")
        except sqlite3.OperationalError:
            print("enfants_charge column already exists or error in salaries")

        try:
            cur.execute("ALTER TABLE dossiers ADD COLUMN pays VARCHAR(100) DEFAULT 'Côte d''Ivoire';")
        except sqlite3.OperationalError:
            print("pays column already exists or error in dossiers")
            
        try:
            cur.execute("ALTER TABLE contrats ADD COLUMN unite_temps VARCHAR(10) DEFAULT 'Heures';")
        except sqlite3.OperationalError:
            print("unite_temps column already exists or error in contrats")
            
        try:
            cur.execute("ALTER TABLE contrats ADD COLUMN sursalaire DOUBLE PRECISION DEFAULT 0.0;")
        except sqlite3.OperationalError:
            print("sursalaire column already exists or error in contrats")
            
        try:
            cur.execute("ALTER TABLE contrats ADD COLUMN indemnite_transport DOUBLE PRECISION DEFAULT 0.0;")
        except sqlite3.OperationalError:
            print("indemnite_transport column already exists or error in contrats")
            
        try:
            cur.execute("ALTER TABLE contrats ADD COLUMN dotation_telephonique DOUBLE PRECISION DEFAULT 0.0;")
        except sqlite3.OperationalError:
            print("dotation_telephonique column already exists or error in contrats")

        try:
            cur.execute("ALTER TABLE contrats ADD COLUMN mode_calcul VARCHAR(10) DEFAULT 'brut';")
        except sqlite3.OperationalError:
            print("mode_calcul column already exists or error in contrats")

        try:
            cur.execute("ALTER TABLE primes ADD COLUMN base DOUBLE PRECISION DEFAULT NULL;")
        except sqlite3.OperationalError:
            print("base column already exists or error in primes")

        try:
            cur.execute("ALTER TABLE primes ADD COLUMN taux DOUBLE PRECISION DEFAULT NULL;")
        except sqlite3.OperationalError:
            print("taux column already exists or error in primes")
            
        try:
            cur.execute("ALTER TABLE utilisateurs ADD COLUMN salarie_id INTEGER REFERENCES salaries(id) ON DELETE CASCADE;")
        except sqlite3.OperationalError:
            print("salarie_id column already exists or error in utilisateurs")

        try:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS reclamations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bulletin_id INTEGER NOT NULL REFERENCES bulletins_paies(id) ON DELETE CASCADE,
                salarie_id INTEGER NOT NULL REFERENCES salaries(id) ON DELETE CASCADE,
                sujet VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                statut VARCHAR(50) DEFAULT 'en_attente',
                commentaire_gestionnaire TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_reclamations_salarie ON reclamations (salarie_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_reclamations_bulletin ON reclamations (bulletin_id);")
        except Exception as e:
            print("Error creating reclamations in SQLite:", e)
            
        conn.commit()
        conn.close()
        print("SQLite database updated successfully.")
    except Exception as e:
        print("Error updating SQLite:", e)
