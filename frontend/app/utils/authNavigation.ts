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

/** Routes accessibles sans session (dont le parcours « mot de passe oublié »). */
export const ROUTES_PUBLIQUES = ['/', '/login', '/forgot-password', '/reset-password']

/** Préfixes réservés à chaque espace, avec les rôles autorisés. */
//: Rôles qui tiennent la paie des sociétés (le « cabinet » historique et le
//: gestionnaire de paie affecté à des dossiers).
export const ROLES_PAIE = ['cabinet', 'gestionnaire_paie']

/** Réclamations : accessibles à tout le personnel (cabinet et gestionnaires). */
export const ROUTE_ADMIN_RECLAMATIONS = '/admin/reclamations'

export const ESPACES = [
  { prefixe: '/dossiers', roles: ROLES_PAIE, adminSeulement: false },
  { prefixe: '/simulation', roles: ROLES_PAIE, adminSeulement: false },
  { prefixe: '/bulletins', roles: ROLES_PAIE, adminSeulement: false },
  { prefixe: '/client', roles: ['client'], adminSeulement: false },
  { prefixe: '/salaries', roles: ['salarie'], adminSeulement: false }
]

/**
 * Routes ouvertes à l'administrateur plateforme. Il pilote le SaaS (cabinets,
 * référentiels, indicateurs) et n'accède à aucun espace de paie des cabinets.
 */
export const ROUTES_PLATEFORME = ['/admin', '/admin/cabinets', '/admin/constantes', '/admin/plan-paie', '/simulation']

/** Espace d'accueil d'un utilisateur selon son rôle. */
export function destinationParDefaut(utilisateur: UtilisateurAuth): string {
  if (utilisateur.is_admin) {
    return '/admin'
  }
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

  if (estAdmin) {
    const autorisee = ROUTES_PLATEFORME.some(
      route => chemin === route || (route !== '/admin' && chemin.startsWith(`${route}/`))
    )
    return autorisee ? { action: 'laisser' } : rediriger(destinationParDefaut(utilisateur))
  }

  // Espace /admin (hors plateforme) :
  //  - réclamations : tout le personnel ;
  //  - constantes, plan de paie et administration des membres : cabinet (les
  //    référentiels globaux y sont en lecture seule ; l'écriture reste réservée
  //    à la plateforme).
  if (chemin === ROUTE_ADMIN_RECLAMATIONS || chemin.startsWith(`${ROUTE_ADMIN_RECLAMATIONS}/`)) {
    return ROLES_PAIE.includes(role)
      ? { action: 'laisser' }
      : rediriger(destinationParDefaut(utilisateur))
  }
  if (chemin === '/admin' || chemin.startsWith('/admin/')) {
    return role === 'cabinet' && !chemin.startsWith('/admin/cabinets')
      ? { action: 'laisser' }
      : rediriger(destinationParDefaut(utilisateur))
  }

  for (const espace of ESPACES) {
    if (!chemin.startsWith(espace.prefixe)) continue

    if (espace.adminSeulement) {
      return rediriger(destinationParDefaut(utilisateur))
    }

    if (!espace.roles.includes(role)) {
      return rediriger(destinationParDefaut(utilisateur))
    }
    return { action: 'laisser' }
  }

  // Route hors espaces connus : on laisse passer.
  return { action: 'laisser' }
}
