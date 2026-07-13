import sys
import os

# Add parent directory to path so app can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app.database import SessionLocal
from app.models.models import TaxBracket, FamilyShare, TaxReduction

def seed_its():
    db = SessionLocal()
    try:
        print("Seeding tax_brackets...")
        db.query(TaxBracket).delete()
        brackets = [
            TaxBracket(revenu_min=0.0, revenu_max=75000.0, taux=0.0),
            TaxBracket(revenu_min=75001.0, revenu_max=240000.0, taux=16.0),
            TaxBracket(revenu_min=240001.0, revenu_max=800000.0, taux=21.0),
            TaxBracket(revenu_min=800001.0, revenu_max=2400000.0, taux=24.0),
            TaxBracket(revenu_min=2400001.0, revenu_max=8000000.0, taux=28.0),
            TaxBracket(revenu_min=8000001.0, revenu_max=None, taux=32.0),
        ]
        db.add_all(brackets)

        print("Seeding family_shares...")
        db.query(FamilyShare).delete()
        shares = []
        
        # We populate for situation_matrimoniale: "Célibataire", "Divorcé", "Veuf", "Marié"
        # and enfants_charge from 0 to 15 to cover larger families.
        for status in ["Célibataire", "Divorcé", "Veuf", "Marié"]:
            for kids in range(16):
                if status in ["Célibataire", "Divorcé"]:
                    if kids == 0:
                        parts = 1.0
                    elif kids == 1:
                        parts = 2.0
                    elif kids == 2:
                        parts = 2.5
                    elif kids == 3:
                        parts = 3.0
                    elif kids == 4:
                        parts = 3.5
                    elif kids == 5:
                        parts = 4.0
                    elif kids == 6:
                        parts = 4.5
                    else:
                        parts = 5.0
                elif status == "Marié":
                    if kids == 0:
                        parts = 2.0
                    elif kids == 1:
                        parts = 2.5
                    elif kids == 2:
                        parts = 3.0
                    elif kids == 3:
                        parts = 3.5
                    elif kids == 4:
                        parts = 4.0
                    elif kids == 5:
                        parts = 4.5
                    else:
                        parts = 5.0
                elif status == "Veuf":
                    if kids == 0:
                        parts = 1.0
                    elif kids == 1:
                        parts = 2.5
                    elif kids == 2:
                        parts = 3.0
                    elif kids == 3:
                        parts = 3.5
                    elif kids == 4:
                        parts = 4.0
                    elif kids == 5:
                        parts = 4.5
                    else:
                        parts = 5.0
                        
                shares.append(FamilyShare(situation_matrimoniale=status, enfants_charge=kids, nombre_parts=parts))
        db.add_all(shares)

        print("Seeding tax_reductions...")
        db.query(TaxReduction).delete()
        reductions = [
            TaxReduction(nombre_parts=1.0, reduction_mensuelle=0.0, reduction_annuelle=0.0),
            TaxReduction(nombre_parts=1.5, reduction_mensuelle=5500.0, reduction_annuelle=66000.0),
            TaxReduction(nombre_parts=2.0, reduction_mensuelle=11000.0, reduction_annuelle=132000.0),
            TaxReduction(nombre_parts=2.5, reduction_mensuelle=16500.0, reduction_annuelle=198000.0),
            TaxReduction(nombre_parts=3.0, reduction_mensuelle=22000.0, reduction_annuelle=264000.0),
            TaxReduction(nombre_parts=3.5, reduction_mensuelle=27500.0, reduction_annuelle=330000.0),
            TaxReduction(nombre_parts=4.0, reduction_mensuelle=33000.0, reduction_annuelle=396000.0),
            TaxReduction(nombre_parts=4.5, reduction_mensuelle=38500.0, reduction_annuelle=462000.0),
            TaxReduction(nombre_parts=5.0, reduction_mensuelle=44000.0, reduction_annuelle=528000.0),
        ]
        db.add_all(reductions)

        db.commit()
        print("ITS reference data seeded successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding ITS data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_its()
