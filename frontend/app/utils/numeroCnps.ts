/**
 * Contrôle du N° CNPS saisi, avant enregistrement.
 *
 * L'API retire espaces et séparateurs et refuse tout caractère non numérique ;
 * ici, on prévient aussi d'une longueur inhabituelle (12 chiffres attendus),
 * qui serait signalée à la déclaration.
 */
export const alerteNumeroCnps = (valeur: string | null | undefined): string => {
  const numero = String(valeur || '').replace(/[\s.\-/]/g, '')
  if (!numero) return ''
  if (!/^\d+$/.test(numero)) return 'Le N° CNPS ne contient que des chiffres.'
  if (numero.length !== 12) return `Le N° CNPS compte habituellement 12 chiffres (${numero.length} saisis).`
  return ''
}
