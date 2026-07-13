import { defineNuxtPlugin } from '#app'
import * as Sentry from '@sentry/vue'

export default defineNuxtPlugin((nuxtApp) => {
  const config = useRuntimeConfig()
  const dsn = config.public.bugsinkDsn

  if (dsn) {
    Sentry.init({
      app: nuxtApp.vueApp,
      dsn,
      integrations: [],
      tracesSampleRate: 1.0
    })
  }

  return {
    provide: {
      sentry: Sentry
    }
  }
})
