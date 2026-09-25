/* eslint-disable @typescript-eslint/no-explicit-any */
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
          Authorization: `Bearer ${accessToken}`
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

  const init = async () => {
    if (typeof window === 'undefined') return

    // 1. Restaurer depuis le cache local (pour connexions directes backend)
    try {
      const cachedToken = localStorage.getItem('sb-token-cache')
      const cachedUser = localStorage.getItem('sb-user-cache')
      if (cachedToken) {
        token.value = cachedToken
        if (cachedUser) {
          user.value = JSON.parse(cachedUser)
        }
        await fetchAndEnrichProfile(cachedToken)
      }
    } catch (e) {
      console.warn('Erreur restauration session locale:', e)
    }

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
        if (typeof window !== 'undefined') {
          localStorage.setItem('sb-token-cache', session.access_token)
          localStorage.setItem('sb-user-cache', JSON.stringify(session.user))
        }
        await fetchAndEnrichProfile(session.access_token)
      }

      client.auth.onAuthStateChange(async (event: string, session: any) => {
        if (session) {
          user.value = session.user
          token.value = session.access_token
          if (typeof window !== 'undefined') {
            localStorage.setItem('sb-token-cache', session.access_token)
            localStorage.setItem('sb-user-cache', JSON.stringify(session.user))
          }
          await fetchAndEnrichProfile(session.access_token)
        } else if (!token.value) {
          user.value = null
          token.value = null
          if (typeof window !== 'undefined') {
            localStorage.removeItem('sb-token-cache')
            localStorage.removeItem('sb-user-cache')
          }
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
            is_admin: response.user.is_admin,
            cabinet_nom: response.user.cabinet_nom,
            cabinet_telephone: response.user.cabinet_telephone,
            cabinet_ville: response.user.cabinet_ville,
            is_default_password: !!response.user.is_default_password
          }
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
      if (!client) {
        return { error: 'Service d\'authentification non disponible.' }
      }
      const { data, error } = await client.auth.signInWithPassword({ email, password })
      if (error) throw error
      if (data?.session) {
        user.value = data.session.user
        token.value = data.session.access_token
        if (typeof window !== 'undefined') {
          localStorage.setItem('sb-token-cache', data.session.access_token)
          localStorage.setItem('sb-user-cache', JSON.stringify(data.session.user))
        }
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
      if (!client) {
        return { error: 'Service d\'authentification non disponible.' }
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
      return { error: e.message || 'Erreur d\'inscription' }
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
      if (typeof window !== 'undefined') {
        localStorage.removeItem('sb-token-cache')
        localStorage.removeItem('sb-user-cache')
      }
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

      if (client) {
        try {
          await client.auth.updateUser({ password: newPassword })
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
    signupCabinet,
    logout,
    changePassword,
    getDefaultRedirect
  }
}
