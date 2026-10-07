/**
 * Garde d'accès globale côté client.
 *
 * Rappel important : ce contrôle est un confort d'usage et une première barrière
 * d'interface. La véritable autorisation est appliquée par l'API
 * (rôles + portée dossier/salarié). Ne jamais considérer ce middleware comme
 * une protection suffisante.
 */
const ROUTES_PUBLIQUES = ['/', '/login']

/** Préfixes réservés à chaque espace, avec les rôles autorisés. */
const ESPACES = [
  { prefixe: '/admin', roles: [], adminSeulement: true },
  { prefixe: '/dossiers', roles: ['cabinet'] },
  { prefixe: '/simulation', roles: ['cabinet'] },
  { prefixe: '/bulletins', roles: ['cabinet'] },
  { prefixe: '/client', roles: ['client'] },
  { prefixe: '/salaries', roles: ['salarie'] }
]

export default defineNuxtRouteMiddleware(async (to) => {
  const { token, user, initialized, ensureInitialized, getDefaultRedirect } = useSupabase()

  if (ROUTES_PUBLIQUES.includes(to.path)) {
    // Un utilisateur déjà connecté n'a rien à faire sur l'écran de connexion.
    if (to.path === '/login' && token.value) {
      return navigateTo(getDefaultRedirect())
    }
    return
  }

  if (!initialized.value) {
    await ensureInitialized()
  }

  if (!token.value) {
    return navigateTo(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
  }

  const u = user.value
  if (!u) {
    // Jeton présent mais profil indisponible : on laisse l'API trancher.
    return
  }

  const estAdmin = !!u.is_admin
  const role = u.role || (u.salarie_id ? 'salarie' : 'cabinet')

  for (const espace of ESPACES) {
    if (!to.path.startsWith(espace.prefixe)) continue

    if (espace.adminSeulement) {
      if (!estAdmin) {
        return navigateTo(getDefaultRedirect())
      }
      return
    }

    if (!estAdmin && !espace.roles.includes(role)) {
      return navigateTo(getDefaultRedirect())
    }
    return
  }
})
