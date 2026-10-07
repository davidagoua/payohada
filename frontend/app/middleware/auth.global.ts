/**
 * Garde d'accès globale côté client.
 *
 * La décision est déléguée à `~/utils/authNavigation`, une fonction pure
 * couverte par des tests (`node scripts/test-auth-navigation.mjs`).
 *
 * Rappel important : ce contrôle est un confort d'usage et une première barrière
 * d'interface. La véritable autorisation est appliquée par l'API
 * (rôles + portée dossier/salarié). Ne jamais considérer ce middleware comme
 * une protection suffisante.
 */
import { deciderRedirection } from '~/utils/authNavigation'

// ─────────────────────────────────────────────────────────────
//  Protection anti-boucle (ceinture et bretelles)
// ─────────────────────────────────────────────────────────────
// `deciderRedirection` ne propose jamais la route courante, mais une boucle
// reste possible entre plusieurs règles. On compte donc les redirections sur
// une fenêtre glissante et on coupe si elles s'emballent : c'est ce qui a
// évité au navigateur (et à la machine) de saturer.
const FENETRE_MS = 2000
const MAX_REDIRECTIONS = 5
let redirections: number[] = []

function redirectionAutorisee(): boolean {
  const maintenant = Date.now()
  redirections = redirections.filter((t) => maintenant - t < FENETRE_MS)
  if (redirections.length >= MAX_REDIRECTIONS) {
    console.error(
      '[auth] Boucle de redirection détectée : navigation laissée en l\'état ' +
      'pour éviter de saturer le navigateur.'
    )
    return false
  }
  redirections.push(maintenant)
  return true
}

export default defineNuxtRouteMiddleware(async (to) => {
  const { token, user, initialized, ensureInitialized } = useSupabase()

  // La session doit être restaurée avant de décider quoi que ce soit.
  if (!initialized.value) {
    await ensureInitialized()
  }

  const decision = deciderRedirection({
    chemin: to.path,
    aJeton: !!token.value,
    utilisateur: user.value
  })

  if (decision.action === 'rediriger' && redirectionAutorisee()) {
    return navigateTo(decision.destination)
  }
})
