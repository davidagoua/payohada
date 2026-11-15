import { useToast as usePrimeToast } from 'primevue/usetoast'

type Couleur = 'success' | 'danger' | 'error' | 'warning' | 'info' | 'primary' | 'neutral'

export interface Notification {
  title?: string
  description?: string
  color?: Couleur | string
  /** Durée d'affichage en millisecondes (5 s par défaut). */
  duration?: number
  /** Conservé pour compatibilité : PrimeVue choisit l'icône selon la gravité. */
  icon?: string
}

const GRAVITE: Record<string, 'success' | 'info' | 'warn' | 'error' | 'secondary'> = {
  success: 'success',
  primary: 'success',
  danger: 'error',
  error: 'error',
  warning: 'warn',
  info: 'info',
  neutral: 'secondary'
}

/**
 * Notifications de l'application, affichées par le `<Toast>` de PrimeVue
 * (voir `app.vue`). La signature `toast.add({ title, description, color })`
 * reste celle employée partout dans le code.
 */
export const useToast = () => {
  const toast = usePrimeToast()

  return {
    add: ({ title, description, color = 'info', duration = 5000 }: Notification) => {
      toast.add({
        severity: GRAVITE[color] ?? 'info',
        summary: title,
        detail: description,
        life: duration
      })
    },
    clear: () => toast.removeAllGroups()
  }
}
