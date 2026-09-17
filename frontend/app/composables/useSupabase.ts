import { createClient } from '@supabase/supabase-js'

export const useSupabase = () => {
  const config = useRuntimeConfig()
  const url = config.public.supabaseUrl
  const key = config.public.supabaseAnonKey

  const user = useState<any>('sb-user', () => null)
  const token = useState<string | null>('sb-token', () => null)
  const loading = useState<boolean>('sb-loading', () => false)
  const initialized = useState<boolean>('sb-initialized', () => false)

  let client: any = null
  if (url && key && typeof window !== 'undefined') {
    client = createClient(url, key)
  }

  const fetchAndEnrichProfile = async (accessToken: string | null | undefined) => {
    if (!accessToken) return
    try {
      const apiBase = config.public.apiBase || 'http://localhost:8000'
      const profile = await $fetch<any>(`${apiBase}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      })
      if (profile && user.value) {
        user.value = {
          ...user.value,
          id: profile.id,
          salarie_id: profile.salarie_id,
          role: profile.role || (profile.salarie_id ? 'salarie' : 'cabinet'),
          dossier_id: profile.dossier_id,
          nom_dossier: profile.nom_dossier,
          is_admin: profile.is_admin,
          is_active: profile.is_active,
          user_metadata: {
            ...user.value.user_metadata,
            first_name: profile.prenom,
            last_name: profile.nom
          }
        }
      }
    } catch (e) {
      console.error('Error enriching profile:', e)
    }
  }

  const init = async () => {
    if (typeof window === 'undefined') return
    if (!client) {
      initialized.value = true
      return
    }

    loading.value = true
    try {
      const { data: { session } } = await client.auth.getSession()
      if (session) {
        user.value = session.user
        token.value = session.access_token
        await fetchAndEnrichProfile(session.access_token)
      }

      client.auth.onAuthStateChange(async (event: string, session: any) => {
        if (session) {
          user.value = session.user
          token.value = session.access_token
          await fetchAndEnrichProfile(session.access_token)
        } else {
          user.value = null
          token.value = null
        }
      })
    } catch (e) {
      console.error('Supabase init error:', e)
    } finally {
      loading.value = false
      initialized.value = true
    }
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
            is_admin: response.user.is_admin
          }
          return { error: null }
        }
      } catch (e: any) {
        console.warn("Backend local login failed:", e)
        if (e.status === 401) {
          return { error: "Adresse email ou mot de passe incorrect." }
        }
        // Si 404 (non trouvé), on laisse passer à Supabase
      }

      // 2. Supabase production
      if (!client) {
        return { error: "Service d'authentification non disponible." }
      }
      const { data, error } = await client.auth.signInWithPassword({ email, password })
      if (error) throw error
      if (data?.session) {
        user.value = data.session.user
        token.value = data.session.access_token
        await fetchAndEnrichProfile(data.session.access_token)
      }
      return { error: null }
    } catch (e: any) {
      return { error: e.message || 'Erreur de connexion' }
    } finally {
      loading.value = false
    }
  }

  const signup = async (email: string, password: string, metadata?: any) => {
    loading.value = true
    try {
      if (!client) {
        return { error: "Service d'authentification non disponible." }
      }

      const { data, error } = await client.auth.signUp({
        email,
        password,
        options: { data: metadata }
      })
      if (error) throw error
      if (data?.session) {
        user.value = data.session.user
        token.value = data.session.access_token
        await fetchAndEnrichProfile(data.session.access_token)
      }
      return { error: null }
    } catch (e: any) {
      return { error: e.message || "Erreur d'inscription" }
    } finally {
      loading.value = false
    }
  }

  const logout = async () => {
    loading.value = true
    try {
      if (client) {
        await client.auth.signOut()
      }
    } catch (e) {
      console.error(e)
    } finally {
      user.value = null
      token.value = null
      loading.value = false
      navigateTo('/login')
    }
  }

  const getDefaultRedirect = (targetUser?: any) => {
    const u = targetUser || user.value
    if (!u) return '/login'
    if (u.role === 'salarie' || u.salarie_id) {
      return '/salaries/bulletins'
    }
    if (u.role === 'client') {
      return '/client'
    }
    return '/dossiers'
  }

  return {
    user,
    token,
    loading,
    initialized,
    init,
    login,
    signup,
    logout,
    getDefaultRedirect
  }
}
