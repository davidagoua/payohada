/**
 * Mise en forme partagée par les pages de paie (montants, périodes, recherche).
 * Auto-importée par Nuxt depuis `utils/`.
 */

export const MOIS_FR = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
]

/** Montant en francs CFA, sans décimales (« 150 000 FCFA »). */
export const formatXOF = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'XOF',
    maximumFractionDigits: 0
  }).format(value).replace('XOF', 'FCFA')
}

/** Libellé d'une période de paie (« Juin 2025 »). */
export const getPeriodLabel = (mois: number, annee: number | string): string =>
  `${MOIS_FR[mois - 1]} ${annee}`

/** Texte comparable pour la recherche : minuscules, sans accents. */
export const normaliserRecherche = (valeur: unknown): string =>
  String(valeur ?? '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
