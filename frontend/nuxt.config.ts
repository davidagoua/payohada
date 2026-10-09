// https://nuxt.com/docs/api/configuration/nuxt-config
const supabaseUrl = process.env.NUXT_PUBLIC_SUPABASE_URL || ''
const apiBase = process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000'
const bugsinkDsn = process.env.NUXT_PUBLIC_BUGSINK_DSN || ''
const n8nChatWebhook = process.env.NUXT_PUBLIC_N8N_CHAT_WEBHOOK || ''

/** Extrait l'origine d'une URL sans faire échouer la configuration si elle est malformée. */
const origine = (url: string): string => {
  if (!url) return ''
  try {
    return new URL(url).origin
  } catch {
    return ''
  }
}

const bugsinkOrigin = origine(bugsinkDsn)
const n8nOrigin = origine(n8nChatWebhook)

// Origines autorisées pour les appels sortants. Les services externes
// (journalisation d'erreurs, chatbot) ne sont inclus que s'ils sont
// effectivement configurés : plus aucune URL n'est codée en dur.
const connectSrc = [
  '\'self\'',
  'https://api.iconify.design',
  supabaseUrl,
  supabaseUrl ? supabaseUrl.replace(/^http/, 'ws') : '',
  apiBase,
  'http://localhost:8000',
  bugsinkOrigin,
  n8nOrigin
].filter(Boolean)

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
    enabled: process.env.NODE_ENV !== 'production'
  },
  app: {
    head: {
      title: 'payohada — Logiciel de Paie',
      link: [
        { rel: 'icon', type: 'image/png', href: '/payohada-icon.png' },
        { rel: 'apple-touch-icon', href: '/payohada-icon.png' }
      ]
    }
  },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      supabaseUrl,
      supabaseAnonKey: process.env.NUXT_PUBLIC_SUPABASE_ANON_KEY || '',
      apiBase,
      bugsinkDsn,
      //: Étiquette d'environnement jointe aux événements d'erreur.
      bugsinkEnvironment: process.env.NUXT_PUBLIC_BUGSINK_ENVIRONMENT || 'production',
      n8nChatWebhook
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
        'connect-src': connectSrc,
        'upgrade-insecure-requests': false
      },
      strictTransportSecurity: false
    }
  }
})
