// https://nuxt.com/docs/api/configuration/nuxt-config
import tailwindcss from '@tailwindcss/vite'
import PayohadaTheme from './app/theme/payohada'

const supabaseUrl = process.env.NUXT_PUBLIC_SUPABASE_URL || ''
// Racine de l'API, préfixe `/api/v1` **compris** (voir `frontend/.env`).
// Les appels directs utilisent donc `${apiBase}/editions/...` et jamais
// `${apiBase}/api/v1/...` : ce doublon renvoyait un 404 sur les exports.
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

const apiOrigin = origine(apiBase)
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
  // Origine seule : une source CSP contenant un chemin ne couvre pas ses
  // sous-chemins (`/api/v1` ne couvre pas `/api/v1/dossiers`).
  apiOrigin || apiBase,
  'http://localhost:8000',
  bugsinkOrigin,
  n8nOrigin
].filter(Boolean)

export default defineNuxtConfig({

  modules: [
    '@nuxt/eslint',
    '@primevue/nuxt-module',
    '@nuxt/icon',
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

  vite: {
    plugins: [tailwindcss()]
  },

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  },

  // Icônes Iconify (Lucide, Simple Icons) : `<Icon name="i-lucide-…" />`.
  icon: {
    serverBundle: 'local'
  },

  // Composants PrimeVue, thème aux couleurs de la marque (voir app/theme).
  primevue: {
    options: {
      ripple: false,
      theme: {
        preset: PayohadaTheme,
        options: {
          // L'interface reste en clair : aucune classe `.dark` n'est posée.
          darkModeSelector: '.dark',
          // Les utilitaires Tailwind passent devant les styles PrimeVue.
          cssLayer: {
            name: 'primevue',
            order: 'theme, base, primevue, components, utilities'
          }
        }
      }
    },
    // `useToast` est fourni par `composables/useToast.ts`, qui garde la
    // signature employée dans toute l'application.
    composables: {
      exclude: ['useToast']
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
