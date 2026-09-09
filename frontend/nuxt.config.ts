// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({

  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    'nuxt-icons',
    'nuxt-email-renderer',
    'nuxt-security'
  ],
  ssr: false,

  devtools: {
    enabled: true
  },
  app: {
    head: {
      title: 'payohada — Logiciel de Paie SAP-Style',
      link: [
        { rel: 'icon', type: 'image/png', href: '/payohada-icon.png' },
        { rel: 'apple-touch-icon', href: '/payohada-icon.png' }
      ]
    }
  },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      supabaseUrl: process.env.NUXT_PUBLIC_SUPABASE_URL || '',
      supabaseAnonKey: process.env.NUXT_PUBLIC_SUPABASE_ANON_KEY || '',
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
      bugsinkDsn: process.env.NUXT_PUBLIC_BUGSINK_DSN || 'https://0d8e0afc57dc4284ba102e9071a2df74@bugsink-wotq24lgae4gr7gwz7ueyrni.songon.shop/1',
      n8nChatWebhook: process.env.NUXT_PUBLIC_N8N_CHAT_WEBHOOK || 'https://n8n-m4ymolk1iglny3uabdpli4sa.songon.shop/webhook/4edd13ea-6fd0-44c3-b5f8-49bac1c51902/chat'
    }
  },

  routeRules: {
    '/': { prerender: true }
  },

  compatibilityDate: '2025-01-15',
  nitro: {
    preset: 'bun'
  },

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  },

  security: {
    headers: {
      contentSecurityPolicy: {
        'connect-src': [
          '\'self\'',
          'https://api.iconify.design',
          process.env.NUXT_PUBLIC_SUPABASE_URL || 'http://supabase.payohada.cloud',
          (process.env.NUXT_PUBLIC_SUPABASE_URL || 'http://supabase.payohada.cloud').replace(/^http/, 'ws'),
          process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
          'http://localhost:8000',
          'https://bugsink-wotq24lgae4gr7gwz7ueyrni.songon.shop',
          'https://n8n-m4ymolk1iglny3uabdpli4sa.songon.shop'
        ],
        'upgrade-insecure-requests': false
      },
      strictTransportSecurity: false
    }
  }
})
