// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    'nuxt-icons',
    'nuxt-email-renderer',
    'nuxt-security'
  ],

  security: {
    headers: {
      contentSecurityPolicy: {
        'connect-src': [
          "'self'",
          process.env.NUXT_PUBLIC_SUPABASE_URL || 'http://supabase.payohada.cloud',
          (process.env.NUXT_PUBLIC_SUPABASE_URL || 'http://supabase.payohada.cloud').replace(/^http/, 'ws'),
          process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
          'http://localhost:8000'
        ],
        'upgrade-insecure-requests': false
      },
      strictTransportSecurity: false
    }
  },

  devtools: {
    enabled: true
  },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      supabaseUrl: process.env.NUXT_PUBLIC_SUPABASE_URL || '',
      supabaseAnonKey: process.env.NUXT_PUBLIC_SUPABASE_ANON_KEY || '',
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000'
    }
  },

  routeRules: {
    '/': { prerender: true }
  },

  compatibilityDate: '2025-01-15',

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  }
})