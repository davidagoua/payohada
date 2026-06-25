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
        
        # Add pays to dossiers
        cur.execute("ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS pays VARCHAR(100) DEFAULT 'Côte d''Ivoire';")
        
        # Add columns to contrats
        cur.execute("ALTER TABLE contrats ADD COLUMN IF NOT EXISTS unite_temps VARCHAR(10) DEFAULT 'Heures';")
        cur.execute("ALTER TABLE contrats ADD COLUMN IF NOT EXISTS sursalaire DOUBLE PRECISION DEFAULT 0.0;")
        cur.execute("ALTER TABLE contrats ADD COLUMN IF NOT EXISTS indemnite_transport DOUBLE PRECISION DEFAULT 0.0;")
        cur.execute("ALTER TABLE contrats ADD COLUMN IF NOT EXISTS dotation_telephonique DOUBLE PRECISION DEFAULT 0.0;")
        
        # Widen code column in plan_paie to prevent StringDataRightTruncation
        cur.execute("ALTER TABLE plan_paie ALTER COLUMN code TYPE VARCHAR(20);")
        
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
            
        conn.commit()
        conn.close()
        print("SQLite database updated successfully.")
    except Exception as e:
        print("Error updating SQLite:", e)
