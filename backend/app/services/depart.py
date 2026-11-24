"""Référentiels du formulaire de départ d'un salarié.

Le motif de sortie suit la codification des déclarations (« 031 — fin de
contrat à durée déterminée… »). Chaque code renvoie, quand c'est possible, au
motif normalisé des calculs du solde de tout compte (`motif_fin_contrat`).
Même liste que `frontend/app/utils/departSalarie.ts`.
"""
from typing import Optional

#: code → (libellé, motif normalisé des calculs ou None si à préciser).
MOTIFS_SORTIE: dict[int, tuple[str, Optional[str]]] = {
    11: ("Licenciement suite à liquidation judiciaire ou redressement judiciaire", "licenciement"),
    14: ("Licenciement pour motif économique", "licenciement"),
    15: ("Licenciement pour inaptitude", "licenciement"),
    20: ("Licenciement pour faute grave", "licenciement"),
    25: ("Licenciement pour faute lourde", "licenciement"),
    26: ("Licenciement pour cause réelle et sérieuse", "licenciement"),
    31: ("Fin de contrat à durée déterminée ou fin d'accueil occasionnel", "fin_cdd"),
    34: ("Fin de période d'essai à l'initiative de l'employeur", None),
    35: ("Fin de période d'essai à l'initiative du salarié", None),
    38: ("Départ à la retraite à l'initiative du salarié", "retraite"),
    39: ("Mise à la retraite par l'employeur", "retraite"),
    43: ("Rupture conventionnelle", "rupture"),
    59: ("Démission", "demission"),
    65: ("Décès du salarié", "deces"),
    99: ("Autre motif", None),
}

#: Types de préavis : code → libellé.
TYPES_PREAVIS: dict[int, str] = {
    10: "Préavis effectué et payé",
    1: "Préavis non effectué et payé",
    2: "Préavis non effectué et non payé",
    90: "Pas de clause de préavis applicable",
}


def motif_calcul(code_motif: Optional[int]) -> Optional[str]:
    """Motif normalisé des calculs correspondant au motif de sortie."""
    if code_motif is None:
        return None
    return MOTIFS_SORTIE.get(int(code_motif), (None, None))[1]
