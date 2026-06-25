export const useApi = () => {
  const config = useRuntimeConfig()
  const { token, logout } = useSupabase()
  const toast = useToast()

  const apiFetch = async (path: string, options: any = {}) => {
    const apiBase = config.public.apiBase || 'http://localhost:8000'
    const url = `${apiBase}${path}`

    // Cloner et injecter les en-têtes d'authentification
    const headers = { ...options.headers }
    if (token.value) {
      headers['Authorization'] = `Bearer ${token.value}`
    }

    try {
      const response = await $fetch(url, {
        ...options,
        headers
      })
      return response
    } catch (error: any) {
      console.error(`API Error on ${path}:`, error)
      
      const status = error.status || error.response?.status
      const detail = error.data?.detail || error.message || 'Une erreur est survenue'

      if (status === 401) {
        toast.add({
          title: 'Session expirée',
          description: 'Votre session a expiré. Veuillez vous reconnecter.',
          color: 'danger'
        })
        logout()
      } else {
        toast.add({
          title: 'Erreur API',
          description: typeof detail === 'string' ? detail : JSON.stringify(detail),
          color: 'danger'
        })
      }
      throw error
    }
  }

  return {
    fetch: apiFetch,
    get: (path: string, options: any = {}) => apiFetch(path, { ...options, method: 'GET' }),
    post: (path: string, body?: any, options: any = {}) => apiFetch(path, { ...options, method: 'POST', body }),
    put: (path: string, body?: any, options: any = {}) => apiFetch(path, { ...options, method: 'PUT', body }),
    delete: (path: string, options: any = {}) => apiFetch(path, { ...options, method: 'DELETE' })
  }
}
