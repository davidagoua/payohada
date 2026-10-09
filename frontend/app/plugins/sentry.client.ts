import { defineNuxtPlugin } from '#app'
import * as Sentry from '@sentry/vue'

export default defineNuxtPlugin((nuxtApp) => {
  const config = useRuntimeConfig()
  const dsn = config.public.bugsinkDsn

  if (dsn) {
    Sentry.init({
      app: nuxtApp.vueApp,
      dsn,
      environment: config.public.bugsinkEnvironment || 'production',
      integrations: [],
      // Bugsink ne collecte que les erreurs : il limite les transactions de
      // performance (en-tête x-sentry-rate-limits) et celles-ci consomment le
      // quota au détriment des erreurs. Désactivées.
      tracesSampleRate: 0
    })
  }

  return {
    provide: {
      sentry: Sentry
    }
  }
})
