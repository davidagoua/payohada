/* eslint-disable @typescript-eslint/no-explicit-any */
import { createClient } from '@supabase/supabase-js'
import { destinationParDefaut } from '~/utils/authNavigation'

/**
 * Client Supabase — SINGLETON au niveau du module.
 *
 * Un `createClient()` par appel de `useSupabase()` créait autant de clients que
 * de composants (15 dans l'application) et surtout un nouveau client à CHAQUE
 * navigation via le middleware. Or chaque client possède son propre minuteur
 * d'auto-rafraîchissement et écoute `localStorage` : plusieurs clients
 * partageant la même session se réveillent mutuellement, se rafraîchissent en
 * boucle et déclenchent une tempête d'événements d'authentification — d'où un
 * flot ininterrompu d'appels à `/auth/me` et une consommation CPU qui faisait
 * tomber la machine.
 */
let clientSingleton: any = null

/** Promesse d'initialisation unique : `init()` ne s'exécute qu'une seule fois. */
let initialisation: Promise<void> | null = null

/** Dernier enrichissement de profil, pour éviter les appels redondants. */
let dernierEnrichissement = { jeton: null as string | null, date: 0 }

/** Intervalle minimal entre deux appels identiques à `/auth/me`. */
const ENRICHISSEMENT_MIN_INTERVALLE_MS = 5000

export const useSupabase = () => {
  const config = useRuntimeConfig()
  const url = config.public.supabaseUrl
  const key = config.public.supabaseAnonKey

  const user = useState<any>('sb-user', () => null)
  const token = useState<string | null>('sb-token', () => null)
  const loading = useState<boolean>('sb-loading', () => false)
  const initialized = useState<boolean>('sb-initialized', () => false)

  /** Retourne le client unique, en le créant au premier usage réel. */
  const obtenirClient = () => {
    if (clientSingleton) return clientSingleton
    if (typeof window === 'undefined' || !url || !key) return null
    clientSingleton = createClient(url, key, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        // Pas de session dans l'URL : évite les allers-retours d'OAuth non utilisés.
        detectSessionInUrl: false
      }
    })
    return clientSingleton
  }

  /**
   * Complète le profil local avec les données de l'API (`/auth/me`).
   *
   * Les appels sont dédupliqués : le même jeton n'est pas ré-enrichi moins de
   * `ENRICHISSEMENT_MIN_INTERVALLE_MS` après le précédent. C'est le garde-fou
   * qui empêche une rafale d'événements d'authentification de se transformer en
   * boucle d'appels réseau.
   */
  const fetchAndEnrichProfile = async (
    accessToken: string | null | undefined,
    options: { force?: boolean } = {}
  ) => {
    if (!accessToken) return

    const maintenant = Date.now()
    if (
      !options.force &&
      dernierEnrichissement.jeton === accessToken &&
      maintenant - dernierEnrichissement.date < ENRICHISSEMENT_MIN_INTERVALLE_MS
    ) {
      return
    }
    dernierEnrichissement = { jeton: accessToken, date: maintenant }

    try {
      const apiBase = config.public.apiBase || 'http://localhost:8000'
      const profile = await $fetch<any>(`${apiBase}/auth/me`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      })
      if (profile && user.value) {
        user.value = {
          ...user.value,
          id: profile.id,
          salarie_id: profile.salarie_id,
          role: profile.role || (profile.salarie_id ? 'salarie' : 'cabinet'),
          dossier_id: profile.dossier_id,
          nom_dossier: profile.nom_dossier,
          cabinet_nom: profile.cabinet_nom,
          cabinet_telephone: profile.cabinet_telephone,
          cabinet_ville: profile.cabinet_ville,
          is_admin: profile.is_admin,
          is_active: profile.is_active,
          is_default_password: !!profile.is_default_password,
          user_metadata: {
            ...user.value.user_metadata,
            first_name: profile.prenom,
            last_name: profile.nom
          }
        }
        if (typeof window !== 'undefined') {
          localStorage.setItem('sb-user-cache', JSON.stringify(user.value))
        }
      }
    } catch (e) {
      console.error('Error enriching profile:', e)
    }
  }

  /** Applique une session à l'état local et au cache. */
  const appliquerSession = (session: any) => {
    user.value = session.user
    token.value = session.access_token
    if (typeof window !== 'undefined') {
      localStorage.setItem('sb-token-cache', session.access_token)
      localStorage.setItem('sb-user-cache', JSON.stringify(session.user))
    }
  }

  /** Efface la session locale (sans redirection). */
  const effacerSession = () => {
    user.value = null
    token.value = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem('sb-token-cache')
      localStorage.removeItem('sb-user-cache')
    }
  }

  const executerInit = async () => {
    if (typeof window === 'undefined') {
      initialized.value = true
      return
    }

    // 1. Restaurer depuis le cache local (connexions directes au backend)
    try {
      const cachedToken = localStorage.getItem('sb-token-cache')
      const cachedUser = localStorage.getItem('sb-user-cache')
      if (cachedToken) {
        token.value = cachedToken
        if (cachedUser) {
          user.value = JSON.parse(cachedUser)
        } else {
          // Jeton sans profil : état incohérent qui provoquait auparavant une
          // boucle de redirection. On repart proprement d'une session vide.
          effacerSession()
        }
        if (token.value) {
          await fetchAndEnrichProfile(cachedToken)
        }
      }
    } catch (e) {
      console.warn('Erreur restauration session locale:', e)
      effacerSession()
    }

    const supabase = obtenirClient()
    if (!supabase) {
      initialized.value = true
      return
    }

    loading.value = true
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (session) {
        appliquerSession(session)
        await fetchAndEnrichProfile(session.access_token)
      }

      // Écouteur enregistré UNE SEULE FOIS (init() est unique).
      supabase.auth.onAuthStateChange(async (event: string, nouvelleSession: any) => {
        if (event === 'INITIAL_SESSION' || event === 'TOKEN_REFRESHED') {
          // Le profil ne change pas lors d'un simple rafraîchissement de jeton :
          // inutile de rappeler l'API.
          if (nouvelleSession) {
            token.value = nouvelleSession.access_token
          }
          return
        }

        if (nouvelleSession) {
          appliquerSession(nouvelleSession)
          await fetchAndEnrichProfile(nouvelleSession.access_token)
        } else if (!token.value) {
          effacerSession()
        }
      })
    } catch (e) {
      console.error('Supabase init error:', e)
    } finally {
      loading.value = false
      initialized.value = true
    }
  }

  /** Initialise la session. Idempotent : les appels concurrents partagent la même promesse. */
  const init = async () => {
    if (!initialisation) {
      initialisation = executerInit().catch((e) => {
        console.error('Échec de l\'initialisation de la session:', e)
        initialized.value = true
      })
    }
    return initialisation
  }

  /** Initialise la session si nécessaire (utilisé par le middleware de route). */
  const ensureInitialized = async () => {
    if (initialized.value) return
    await init()
  }

  const login = async (email: string, password: string) => {
    loading.value = true
    try {
      // 1. Essayer de se connecter via notre backend local
      try {
        const apiBase = config.public.apiBase || 'http://localhost:8000'
        const response = await $fetch<any>(`${apiBase}/auth/login`, {
          method: 'POST',
          body: { email, password }
        })

        if (response && response.access_token) {
          token.value = response.access_token
          user.value = {
            id: response.user.id,
            email: response.user.email,
            user_metadata: {
              first_name: response.user.prenom,
              last_name: response.user.nom
            },
            role: response.user.role || (response.user.salarie_id ? 'salarie' : 'cabinet'),
            dossier_id: response.user.dossier_id,
            nom_dossier: response.user.nom_dossier,
            salarie_id: response.user.salarie_id,
            is_admin: response.user.is_admin,
            cabinet_nom: response.user.cabinet_nom,
            cabinet_telephone: response.user.cabinet_telephone,
            cabinet_ville: response.user.cabinet_ville,
            is_default_password: !!response.user.is_default_password
          }
          dernierEnrichissement = { jeton: response.access_token, date: Date.now() }
          if (typeof window !== 'undefined') {
            localStorage.setItem('sb-token-cache', response.access_token)
            localStorage.setItem('sb-user-cache', JSON.stringify(user.value))
          }
          return { error: null }
        }
      } catch (e: any) {
        console.warn('Backend local login failed:', e)
        if (e.status === 401) {
          return { error: 'Adresse email ou mot de passe incorrect.' }
        }
        // Si 404 (non trouvé), on laisse passer à Supabase
      }

      // 2. Supabase production
      const supabase = obtenirClient()
      if (!supabase) {
        return { error: 'Service d\'authentification non disponible.' }
      }
      const { data, error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) throw error
      if (data?.session) {
        appliquerSession(data.session)
        await fetchAndEnrichProfile(data.session.access_token)
      }
      return { error: null }
    } catch (e: any) {
      return { error: e.message || 'Erreur de connexion' }
    } finally {
      loading.value = false
    }
  }

  const signupCabinet = async (formData: {
    prenom: string
    nom: string
    email: string
    password: string
    cabinet_nom: string
    cabinet_telephone?: string
    cabinet_ville?: string
  }) => {
    loading.value = true
    try {
      const apiBase = config.public.apiBase || 'http://localhost:8000'
      const response = await $fetch<any>(`${apiBase}/auth/signup-cabinet`, {
        method: 'POST',
        body: formData
      })

      if (response && response.access_token) {
        token.value = response.access_token
        user.value = {
          id: response.user.id,
          email: response.user.email,
          user_metadata: {
            first_name: response.user.prenom,
            last_name: response.user.nom
          },
          role: 'cabinet',
          dossier_id: null,
          nom_dossier: null,
          salarie_id: null,
          is_admin: response.user.is_admin || false,
          cabinet_nom: response.user.cabinet_nom,
          cabinet_telephone: response.user.cabinet_telephone,
          cabinet_ville: response.user.cabinet_ville
        }
        dernierEnrichissement = { jeton: response.access_token, date: Date.now() }
        if (typeof window !== 'undefined') {
          localStorage.setItem('sb-token-cache', response.access_token)
          localStorage.setItem('sb-user-cache', JSON.stringify(user.value))
        }
        return { error: null }
      }
      return { error: 'Une réponse inattendue a été reçue du serveur.' }
    } catch (e: any) {
      console.error('Erreur signup cabinet:', e)
      const detail = e.data?.detail || e.message || 'Erreur lors de la création du compte cabinet.'
      return { error: detail }
    } finally {
      loading.value = false
    }
  }

  const signup = async (email: string, password: string, metadata?: any) => {
    loading.value = true
    try {
      const supabase = obtenirClient()
      if (!supabase) {
        return { error: 'Service d\'authentification non disponible.' }
      }

      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: { data: metadata }
      })
      if (error) throw error
      if (data?.session) {
        appliquerSession(data.session)
        await fetchAndEnrichProfile(data.session.access_token)
      }
      return { error: null }
    } catch (e: any) {
      return { error: e.message || 'Erreur d\'inscription' }
    } finally {
      loading.value = false
    }
  }

  const logout = async () => {
    loading.value = true
    try {
      const supabase = obtenirClient()
      if (supabase) {
        await supabase.auth.signOut()
      }
    } catch (e) {
      console.error(e)
    } finally {
      effacerSession()
      // Un nouveau jeton devra être enrichi sans attendre la fenêtre anti-rebond.
      dernierEnrichissement = { jeton: null, date: 0 }
      loading.value = false
      navigateTo('/login')
    }
  }

  const changePassword = async (oldPassword: string, newPassword: string) => {
    loading.value = true
    try {
      const apiBase = config.public.apiBase || 'http://localhost:8000'
      const headers: Record<string, string> = {}
      if (token.value) {
        headers.Authorization = `Bearer ${token.value}`
      }
      const response = await $fetch<any>(`${apiBase}/auth/change-password`, {
        method: 'POST',
        headers,
        body: {
          old_password: oldPassword,
          new_password: newPassword
        }
      })

      const supabase = obtenirClient()
      if (supabase) {
        try {
          await supabase.auth.updateUser({ password: newPassword })
        } catch (err) {
          console.warn('Supabase updateUser password notice:', err)
        }
      }

      if (user.value) {
        user.value = {
          ...user.value,
          is_default_password: false
        }
        if (typeof window !== 'undefined') {
          localStorage.setItem('sb-user-cache', JSON.stringify(user.value))
        }
      }

      return { error: null, message: response?.message || 'Mot de passe mis à jour avec succès.' }
    } catch (e: any) {
      const detail = e.data?.detail || e.message || 'Erreur lors de la modification du mot de passe.'
      return { error: detail }
    } finally {
      loading.value = false
    }
  }

  const getDefaultRedirect = (targetUser?: any) => {
    const u = targetUser || user.value
    if (!u) return '/login'
    return destinationParDefaut(u)
  }

  return {
    user,
    token,
    loading,
    initialized,
    init,
    ensureInitialized,
    login,
    signup,
    signupCabinet,
    logout,
    changePassword,
    getDefaultRedirect
  }
}
