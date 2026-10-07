/**
 * Décision de navigation par rôle — logique PURE, sans dépendance à Nuxt.
 *
 * Isolée ici pour deux raisons :
 *  1. elle est testable directement (`scripts/test-auth-navigation.mjs`) ;
 *  2. elle centralise la règle qui, appliquée naïvement, provoquait une boucle
 *     de redirection infinie : rediriger vers la route courante.
 */

export interface UtilisateurAuth {
  role?: string | null
  salarie_id?: number | null
  is_admin?: boolean | null
}

export type Decision =
  | { action: 'laisser' }
  | { action: 'rediriger'; destination: string }

/** Routes accessibles sans session. */
export const ROUTES_PUBLIQUES = ['/', '/login']

/** Préfixes réservés à chaque espace, avec les rôles autorisés. */
export const ESPACES = [
  { prefixe: '/admin', roles: [] as string[], adminSeulement: true },
  { prefixe: '/dossiers', roles: ['cabinet'], adminSeulement: false },
  { prefixe: '/simulation', roles: ['cabinet'], adminSeulement: false },
  { prefixe: '/bulletins', roles: ['cabinet'], adminSeulement: false },
  { prefixe: '/client', roles: ['client'], adminSeulement: false },
  { prefixe: '/salaries', roles: ['salarie'], adminSeulement: false }
]

/** Espace d'accueil d'un utilisateur selon son rôle. */
export function destinationParDefaut(utilisateur: UtilisateurAuth): string {
  if (utilisateur.role === 'salarie' || utilisateur.salarie_id) {
    return '/salaries/bulletins'
  }
  if (utilisateur.role === 'client') {
    return '/client'
  }
  return '/dossiers'
}

/**
 * Décide de l'action à mener pour une navigation donnée.
 *
 * Invariant garanti : `destination` n'est jamais égale à `chemin`, ce qui
 * empêche toute boucle de redirection.
 */
export function deciderRedirection(params: {
  chemin: string
  aJeton: boolean
  utilisateur: UtilisateurAuth | null | undefined
}): Decision {
  const { chemin, aJeton, utilisateur } = params

  const rediriger = (destination: string): Decision =>
    destination && destination !== chemin
      ? { action: 'rediriger', destination }
      : { action: 'laisser' }

  if (ROUTES_PUBLIQUES.includes(chemin)) {
    // Un utilisateur connecté n'a rien à faire sur l'écran de connexion — mais
    // seulement si son profil est connu : avec un jeton sans profil, la
    // destination calculée serait '/login' et l'on bouclait indéfiniment.
    if (chemin === '/login' && aJeton && utilisateur) {
      return rediriger(destinationParDefaut(utilisateur))
    }
    return { action: 'laisser' }
  }

  if (!aJeton) {
    return rediriger(`/login?redirect=${encodeURIComponent(chemin)}`)
  }

  if (!utilisateur) {
    // Jeton présent mais profil indisponible : on laisse la page s'afficher,
    // l'API tranchera. Rediriger ici relancerait une boucle.
    return { action: 'laisser' }
  }

  const estAdmin = !!utilisateur.is_admin
  const role = utilisateur.role || (utilisateur.salarie_id ? 'salarie' : 'cabinet')

  for (const espace of ESPACES) {
    if (!chemin.startsWith(espace.prefixe)) continue

    if (espace.adminSeulement) {
      return estAdmin ? { action: 'laisser' } : rediriger(destinationParDefaut(utilisateur))
    }

    if (!estAdmin && !espace.roles.includes(role)) {
      return rediriger(destinationParDefaut(utilisateur))
    }
    return { action: 'laisser' }
  }

  // Route hors espaces connus : on laisse passer.
  return { action: 'laisser' }
}
