/**
 * Résout l'URL de base de l'API.
 *
 * En développement, l'API tourne sur le port 8000. En production statique
 * (Caddy), l'API est proxyfiée sur le même domaine sous `/api/v1`. Si une
 * build a été produite avec une valeur `localhost` (ce qui arrive quand le
 * frontend est compilé localement puis déployé), on bascule automatiquement
 * sur l'origine courante pour éviter des appels vers le poste de l'utilisateur.
 */
export function resoudreApiBase(configuree?: string | null): string {
  const valeur = (configuree || '').trim()
  const defaut = import.meta.dev ? 'http://localhost:8000/api/v1' : '/api/v1'
  if (!import.meta.dev && typeof window !== 'undefined') {
    const hoteLocal = ['localhost', '127.0.0.1', '[::1]', '::1'].includes(window.location.hostname)
    const pointeVersLocal = !valeur || valeur.includes('localhost') || valeur.includes('127.0.0.1')
    if (!hoteLocal && pointeVersLocal) return `${window.location.origin}/api/v1`
  }
  return valeur || defaut
}
