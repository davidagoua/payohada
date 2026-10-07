"""Script de migration historique (SQLite local / PostgreSQL).

SOURCE DE VÉRITÉ : `backend/schema.sql` (PostgreSQL / Supabase).
Toute modification de la base doit y être ajoutée dans la section
« MIGRATION INCREMENTALE » à la fin du fichier. Ce script ne fait que
rejouer les mêmes changements pour les environnements de développement.
"""
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

def _mask_url(url):
    """Masque les identifiants avant toute journalisation."""
    if not url:
        return "<non défini>"
    import re
    return re.sub(r"://[^@/]*@", "://<identifiants masqués>@", url)


print("DATABASE_URL:", _mask_url(db_url))

# 1. Update PostgreSQL
if db_url and (db_url.startswith("postgresql") or db_url.startswith("postgres")):
    try:
        clean_url = db_url.replace("postgresql+psycopg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")
        if clean_url.startswith("postgres://"):
            clean_url = clean_url.replace("postgres://", "postgresql://", 1)
        try:
            import psycopg2
            conn = psycopg2.connect(clean_url)
        except ImportError:
            import psycopg
            conn = psycopg.connect(clean_url)
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
        
        # Add salarie_id, role, dossier_id to utilisateurs
        cur.execute("ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS salarie_id INTEGER REFERENCES salaries(id) ON DELETE CASCADE;")
        cur.execute("ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'cabinet';")
        cur.execute("ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS dossier_id INTEGER REFERENCES dossiers(id) ON DELETE SET NULL;")
        cur.execute("ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS cabinet_nom VARCHAR(200) DEFAULT NULL;")
        cur.execute("ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS cabinet_telephone VARCHAR(30) DEFAULT NULL;")
        cur.execute("ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS cabinet_ville VARCHAR(100) DEFAULT NULL;")
        cur.execute("ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;")

        # --- Correctifs d'audit (cf. backend/schema.sql, section
        #     « MIGRATION INCREMENTALE : CORRECTIFS D'AUDIT ») ---
        # Défauts d'horaires alignés sur le droit ivoirien / UEMOA (40 h/semaine).
        # SET DEFAULT n'affecte que les nouvelles lignes.
        cur.execute("ALTER TABLE horaires ALTER COLUMN horaire_travail SET DEFAULT 173.33;")
        cur.execute("ALTER TABLE horaires ALTER COLUMN horaire_hebdo SET DEFAULT 40.0;")

        # Majorations d'heures supplémentaires 75 % et 100 % (absentes du référentiel).
        cur.execute("""
        INSERT INTO plan_paie (type, code, libelle, mode_calcul, sens, pays)
        SELECT 'B', 'HS_75', 'Heures supplémentaires majorées à 75%', 'Sémi-auto', 'Gain', 'CI'
        WHERE NOT EXISTS (SELECT 1 FROM plan_paie WHERE code = 'HS_75' AND pays = 'CI');
        """)
        cur.execute("""
        INSERT INTO plan_paie (type, code, libelle, mode_calcul, sens, pays)
        SELECT 'B', 'HS_100', 'Heures supplémentaires majorées à 100%', 'Sémi-auto', 'Gain', 'CI'
        WHERE NOT EXISTS (SELECT 1 FROM plan_paie WHERE code = 'HS_100' AND pays = 'CI');
        """)
        
        # Create periodes_paie table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS periodes_paie (
            id SERIAL PRIMARY KEY,
            dossier_id INTEGER NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
            mois INTEGER NOT NULL,
            annee VARCHAR(4) NOT NULL,
            statut VARCHAR(50) DEFAULT 'saisie_en_cours',
            date_transmission TIMESTAMP WITH TIME ZONE DEFAULT NULL,
            transmis_par_id INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL,
            notes_client TEXT DEFAULT NULL,
            notes_cabinet TEXT DEFAULT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uk_periodes_paie_dossier_periode UNIQUE (dossier_id, annee, mois)
        );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_periodes_paie_dossier ON periodes_paie (dossier_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_periodes_paie_dossier_periode ON periodes_paie (dossier_id, annee, mois);")

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
        cur.execute("ALTER TABLE lignes_bulletins_paies ADD COLUMN IF NOT EXISTS pret_id INTEGER REFERENCES prets_salaries(id) ON DELETE SET NULL;")
        
        # Mettre à jour les rôles des utilisateurs existants
        cur.execute("UPDATE utilisateurs SET role = 'salarie' WHERE salarie_id IS NOT NULL AND (role IS NULL OR role = 'cabinet');")
        cur.execute("UPDATE utilisateurs SET role = 'cabinet' WHERE salarie_id IS NULL AND (role IS NULL);")
        
        # NOTE : la création automatique d'un compte de démonstration sans mot
        # de passe a été supprimée. Un compte est désormais créé via
        # POST /api/v1/dossiers/{id}/comptes-clients (mot de passe aléatoire
        # généré et retourné une seule fois) ou via create_admin.py.

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
            cur.execute("ALTER TABLE utilisateurs ADD COLUMN role VARCHAR(20) DEFAULT 'cabinet';")
        except sqlite3.OperationalError:
            print("role column already exists or error in utilisateurs")

        try:
            cur.execute("ALTER TABLE utilisateurs ADD COLUMN dossier_id INTEGER REFERENCES dossiers(id) ON DELETE SET NULL;")
        except sqlite3.OperationalError:
            print("dossier_id column already exists or error in utilisateurs")

        try:
            cur.execute("ALTER TABLE utilisateurs ADD COLUMN cabinet_nom VARCHAR(200) DEFAULT NULL;")
        except sqlite3.OperationalError:
            print("cabinet_nom column already exists or error in utilisateurs")

        try:
            cur.execute("ALTER TABLE utilisateurs ADD COLUMN cabinet_telephone VARCHAR(30) DEFAULT NULL;")
        except sqlite3.OperationalError:
            print("cabinet_telephone column already exists or error in utilisateurs")

        try:
            cur.execute("ALTER TABLE utilisateurs ADD COLUMN cabinet_ville VARCHAR(100) DEFAULT NULL;")
        except sqlite3.OperationalError:
            print("cabinet_ville column already exists or error in utilisateurs")

        try:
            cur.execute("ALTER TABLE utilisateurs ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0;")
        except sqlite3.OperationalError:
            print("must_change_password column already exists or error in utilisateurs")

        try:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS periodes_paie (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dossier_id INTEGER NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
                mois INTEGER NOT NULL,
                annee VARCHAR(4) NOT NULL,
                statut VARCHAR(50) DEFAULT 'saisie_en_cours',
                date_transmission TIMESTAMP DEFAULT NULL,
                transmis_par_id INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL,
                notes_client TEXT DEFAULT NULL,
                notes_cabinet TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (dossier_id, annee, mois)
            );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_periodes_paie_dossier ON periodes_paie (dossier_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_periodes_paie_dossier_periode ON periodes_paie (dossier_id, annee, mois);")
        except Exception as e:
            print("Error creating periodes_paie in SQLite:", e)

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
            
        try:
            cur.execute("ALTER TABLE lignes_bulletins_paies ADD COLUMN pret_id INTEGER REFERENCES prets_salaries(id) ON DELETE SET NULL;")
        except sqlite3.OperationalError:
            print("pret_id column already exists or error in lignes_bulletins_paies")
            
        conn.commit()
        conn.close()
        print("SQLite database updated successfully.")
    except Exception as e:
        print("Error updating SQLite:", e)
