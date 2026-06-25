import { createClient } from '@supabase/supabase-js'

export const useSupabase = () => {
  const config = useRuntimeConfig()
  const url = config.public.supabaseUrl
  const key = config.public.supabaseAnonKey

  const user = useState<any>('sb-user', () => null)
  const token = useState<string | null>('sb-token', () => null)
  const loading = useState<boolean>('sb-loading', () => false)
  const isMock = useState<boolean>('sb-mock', () => false)

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
    }
  }

  const login = async (email: string, password?: string) => {
    loading.value = true
    try {
      if (!client || isMock.value || !password) {
        // Mock Login
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
    init,
    login,
    signup,
    logout
  }
}
