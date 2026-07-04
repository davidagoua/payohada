import { createClient } from '@supabase/supabase-js'

export const useSupabase = () => {
  const config = useRuntimeConfig()
  const url = config.public.supabaseUrl
  const key = config.public.supabaseAnonKey

  const user = useState<any>('sb-user', () => null)
  const token = useState<string | null>('sb-token', () => null)
  const loading = useState<boolean>('sb-loading', () => false)
  const isMock = useState<boolean>('sb-mock', () => false)
  const initialized = useState<boolean>('sb-initialized', () => false)

  let client: any = null
  if (url && key && typeof window !== 'undefined') {
    client = createClient(url, key)
  }

  const init = async () => {
    if (typeof window === 'undefined') return
    if (!client) {
      isMock.value = true
      const storedUser = localStorage.getItem('mock-user')
      const storedToken = localStorage.getItem('mock-token')
      if (storedUser && storedToken) {
        user.value = JSON.parse(storedUser)
        token.value = storedToken
      }
      initialized.value = true
      return
    }

    loading.value = true
    try {
      const { data: { session } } = await client.auth.getSession()
      if (session) {
        user.value = session.user
        token.value = session.access_token
        isMock.value = false
      } else {
        // Fallback to mock session if stored
        const storedUser = localStorage.getItem('mock-user')
        const storedToken = localStorage.getItem('mock-token')
        if (storedUser && storedToken) {
          user.value = JSON.parse(storedUser)
          token.value = storedToken
          isMock.value = true
        }
      }

      client.auth.onAuthStateChange((event: string, session: any) => {
        if (session) {
          user.value = session.user
          token.value = session.access_token
          isMock.value = false
        } else if (!isMock.value) {
          user.value = null
          token.value = null
        }
      })
    } catch (e) {
      console.error('Supabase init error, switching to mock:', e)
      isMock.value = true
      const storedUser = localStorage.getItem('mock-user')
      const storedToken = localStorage.getItem('mock-token')
      if (storedUser && storedToken) {
        user.value = JSON.parse(storedUser)
        token.value = storedToken
      }
    } finally {
      loading.value = false
      initialized.value = true
    }
  }

  const login = async (email: string, password?: string) => {
    loading.value = true
    try {
      // 1. Essayer de se connecter via notre backend local s'il y a un mot de passe
      if (password) {
        try {
          const apiBase = config.public.apiBase || 'http://localhost:8000'
          const response = await $fetch<any>(`${apiBase}/api/v1/auth/login`, {
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
              salarie_id: response.user.salarie_id
            }
            isMock.value = response.access_token.startsWith("mock-")
            localStorage.setItem('mock-user', JSON.stringify(user.value))
            localStorage.setItem('mock-token', token.value)
            return { error: null }
          }
        } catch (e: any) {
          console.warn("Backend local login failed:", e)
          if (e.status === 401) {
            return { error: "Adresse email ou mot de passe incorrect." }
          }
          // Si 404 (non trouvé), on laisse passer aux fallbacks Supabase / Mock
        }
      }

      // 2. Fallbacks
      if (!client || isMock.value || !password) {
        // Mock Login (sans mot de passe ou en mode pure mock)
        const mockUid = 'mock-uid-' + Math.random().toString(36).substring(2, 11)
        const mockUser = {
          id: mockUid,
          email,
          user_metadata: { first_name: 'Utilisateur', last_name: 'Démo' }
        }
        const mockToken = `mock-${email}-${mockUid}`
        user.value = mockUser
        token.value = mockToken
        isMock.value = true
        localStorage.setItem('mock-user', JSON.stringify(mockUser))
        localStorage.setItem('mock-token', mockToken)
        return { error: null }
      }

      // Supabase production
      const { data, error } = await client.auth.signInWithPassword({ email, password })
      if (error) throw error
      if (data?.session) {
        user.value = data.session.user
        token.value = data.session.access_token
        isMock.value = false
      }
      return { error: null }
    } catch (e: any) {
      return { error: e.message || 'Erreur de connexion Supabase' }
    } finally {
      loading.value = false
    }
  }

  const signup = async (email: string, password?: string, metadata?: any) => {
    loading.value = true
    try {
      if (!client || isMock.value || !password) {
        // Mock Signup
        const mockUid = 'mock-uid-' + Math.random().toString(36).substring(2, 11)
        const mockUser = {
          id: mockUid,
          email,
          user_metadata: metadata || { first_name: 'Utilisateur', last_name: 'Démo' }
        }
        const mockToken = `mock-${email}-${mockUid}`
        user.value = mockUser
        token.value = mockToken
        isMock.value = true
        localStorage.setItem('mock-user', JSON.stringify(mockUser))
        localStorage.setItem('mock-token', mockToken)
        return { error: null }
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
        isMock.value = false
      }
      return { error: null }
    } catch (e: any) {
      return { error: e.message || "Erreur d'inscription Supabase" }
    } finally {
      loading.value = false
    }
  }

  const logout = async () => {
    loading.value = true
    try {
      if (client && !isMock.value) {
        await client.auth.signOut()
      }
    } catch (e) {
      console.error(e)
    } finally {
      user.value = null
      token.value = null
      isMock.value = false
      localStorage.removeItem('mock-user')
      localStorage.removeItem('mock-token')
      loading.value = false
      navigateTo('/login')
    }
  }

  return {
    user,
    token,
    loading,
    isMock,
    initialized,
    init,
    login,
    signup,
    logout
  }
}
