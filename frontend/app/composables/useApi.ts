import * as Sentry from '@sentry/vue'

export const extractFieldErrors = (error: any): Record<string, string> => {
  const errors: Record<string, string> = {}
  if (error && error.data && error.data.detail) {
    const detail = error.data.detail
    if (Array.isArray(detail)) {
      for (const err of detail) {
        if (err.loc && Array.isArray(err.loc)) {
          const field = err.loc[err.loc.length - 1]
          let msg = err.msg || ''
          
          // Map to user friendly French messages
          if (err.type === 'value_error.missing' || msg.includes('field required')) {
            msg = 'Ce champ est obligatoire.'
          } else if (err.type === 'value_error.email' || msg.includes('value is not a valid email address')) {
            msg = 'Adresse email invalide.'
          } else if (err.type === 'value_error.number.not_ge') {
            msg = 'Cette valeur doit être supérieure ou égale au minimum requis.'
          } else if (msg.includes('less than')) {
            msg = 'Cette valeur dépasse la limite autorisée.'
          }
          
          errors[field] = msg
        }
      }
    }
  }
  return errors
}

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

      // Send unexpected internal / network errors to Bugsink
      if (!status || status >= 500) {
        Sentry.captureException(error, {
          extra: {
            path,
            status,
            detail
          }
        })
      }

      if (status === 401) {
        toast.add({
          title: 'Session expirée',
          description: 'Votre session a expiré. Veuillez vous reconnecter.',
          color: 'danger'
        })
        logout()
      } else if (status === 422) {
        toast.add({
          title: 'Erreur de validation',
          description: 'Certains champs du formulaire contiennent des erreurs.',
          color: 'warning'
        })
      } else if (status === 403) {
        toast.add({
          title: 'Accès refusé',
          description: "Vous n'avez pas l'autorisation d'effectuer cette action.",
          color: 'danger'
        })
      } else if (status === 404) {
        toast.add({
          title: 'Introuvable',
          description: "La ressource demandée est introuvable.",
          color: 'danger'
        })
      } else if (status === 400) {
        const displayMsg = typeof detail === 'string' ? detail : "Une erreur est survenue lors de l'envoi de la requête."
        toast.add({
          title: 'Requête incorrecte',
          description: displayMsg,
          color: 'warning'
        })
      } else {
        toast.add({
          title: 'Erreur Serveur',
          description: "Une erreur de communication avec le serveur est survenue. L'incident a été signalé.",
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
    delete: (path: string, options: any = {}) => apiFetch(path, { ...options, method: 'DELETE' }),
    extractFieldErrors
  }
}
