/**
 * Référentiels du formulaire de départ d'un salarié.
 *
 * Même liste que `backend/app/services/depart.py`, qui valide les codes et en
 * déduit le motif normalisé des calculs du solde de tout compte.
 */
export interface MotifSortie {
  code: number
  libelle: string
  /** Motif des calculs (licenciement, retraite…) ; `null` : à préciser. */
  calcul: string | null
}

export const MOTIFS_SORTIE: MotifSortie[] = [
  { code: 11, libelle: 'Licenciement suite à liquidation judiciaire ou redressement judiciaire', calcul: 'licenciement' },
  { code: 14, libelle: 'Licenciement pour motif économique', calcul: 'licenciement' },
  { code: 15, libelle: 'Licenciement pour inaptitude', calcul: 'licenciement' },
  { code: 20, libelle: 'Licenciement pour faute grave', calcul: 'licenciement' },
  { code: 25, libelle: 'Licenciement pour faute lourde', calcul: 'licenciement' },
  { code: 26, libelle: 'Licenciement pour cause réelle et sérieuse', calcul: 'licenciement' },
  { code: 31, libelle: 'Fin de contrat à durée déterminée ou fin d\'accueil occasionnel', calcul: 'fin_cdd' },
  { code: 34, libelle: 'Fin de période d\'essai à l\'initiative de l\'employeur', calcul: null },
  { code: 35, libelle: 'Fin de période d\'essai à l\'initiative du salarié', calcul: null },
  { code: 38, libelle: 'Départ à la retraite à l\'initiative du salarié', calcul: 'retraite' },
  { code: 39, libelle: 'Mise à la retraite par l\'employeur', calcul: 'retraite' },
  { code: 43, libelle: 'Rupture conventionnelle', calcul: 'rupture' },
  { code: 59, libelle: 'Démission', calcul: 'demission' },
  { code: 65, libelle: 'Décès du salarié', calcul: 'deces' },
  { code: 99, libelle: 'Autre motif', calcul: null }
]

export const TYPES_PREAVIS = [
  { code: 10, libelle: 'Préavis effectué et payé' },
  { code: 1, libelle: 'Préavis non effectué et payé' },
  { code: 2, libelle: 'Préavis non effectué et non payé' },
  { code: 90, libelle: 'Pas de clause de préavis applicable' }
]

/** « 031 - fin de contrat… » : code sur trois chiffres, comme dans les déclarations. */
export const libelleMotifSortie = (motif: MotifSortie) =>
  `${String(motif.code).padStart(3, '0')} - ${motif.libelle}`

export const motifCalcul = (code: number | null | undefined): string | null =>
  MOTIFS_SORTIE.find(m => m.code === code)?.calcul ?? null
