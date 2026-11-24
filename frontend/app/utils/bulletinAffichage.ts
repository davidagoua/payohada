/**
 * Choix d'affichage du bulletin imprimé : informations de l'employeur dans
 * l'en-tête et zone des signatures.
 *
 * Même liste que `INFOS_EMPLOYEUR` dans `backend/app/services/bulletin_saari.py`,
 * qui produit le PDF : les deux rendus doivent rester identiques.
 */
export interface InfoEmployeur {
  cle: string
  libelle: string
  parDefaut: boolean
}

export const INFOS_EMPLOYEUR: InfoEmployeur[] = [
  { cle: 'logo', libelle: 'Logo', parDefaut: true },
  { cle: 'raison_sociale', libelle: 'Raison sociale', parDefaut: true },
  { cle: 'sigle', libelle: 'Sigle', parDefaut: false },
  { cle: 'adresse', libelle: 'Adresse', parDefaut: true },
  { cle: 'activite', libelle: 'Activité', parDefaut: true },
  { cle: 'numero_rccm', libelle: 'N° RCCM', parDefaut: false },
  { cle: 'telephone', libelle: 'Téléphone', parDefaut: false },
  { cle: 'email', libelle: 'Email', parDefaut: false },
  { cle: 'site_web', libelle: 'Site web', parDefaut: false }
]

export interface AffichageBulletin {
  infos_employeur: string[]
  signatures: boolean
}

export function affichageParDefaut(): AffichageBulletin {
  return {
    infos_employeur: INFOS_EMPLOYEUR.filter(i => i.parDefaut).map(i => i.cle),
    signatures: true
  }
}

/** Relit un choix mémorisé en écartant les clés inconnues. */
export function normaliserAffichage(valeur: unknown): AffichageBulletin {
  const defaut = affichageParDefaut()
  if (!valeur || typeof valeur !== 'object') return defaut
  const v = valeur as Partial<AffichageBulletin>
  const connues = new Set(INFOS_EMPLOYEUR.map(i => i.cle))
  return {
    infos_employeur: Array.isArray(v.infos_employeur)
      ? v.infos_employeur.filter(c => connues.has(c))
      : defaut.infos_employeur,
    signatures: typeof v.signatures === 'boolean' ? v.signatures : defaut.signatures
  }
}
