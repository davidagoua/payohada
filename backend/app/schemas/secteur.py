from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal

# ─────────────────────────────────────────
#  SCHÉMAS SECTEUR
# ─────────────────────────────────────────

class SecteurBase(BaseModel):
    nom: str

class SecteurCreate(SecteurBase):
    pass

class SecteurOut(SecteurBase):
    id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
#  SCHÉMAS POSTE SALAIRE
# ─────────────────────────────────────────

class PosteSalaireBase(BaseModel):
    secteur_id: int
    categorie_professionnelle: str
    echelon_categorie: str
    salaire_mensuel_fcfa: Optional[int] = None
    taux_horaire_fcfa: Optional[Decimal] = None
    details_poste: Optional[str] = None

class PosteSalaireCreate(PosteSalaireBase):
    pass

class PosteSalaireOut(PosteSalaireBase):
    id: int

    class Config:
        from_attributes = True
