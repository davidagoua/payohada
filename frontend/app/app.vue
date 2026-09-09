<script setup>
const { init, initialized } = useSupabase()

onMounted(() => {
  init()
})

const title = 'payohada — Logiciel de Paie SAP-Style'
const description = 'Logiciel moderne de gestion de paie, dossiers entreprises, salariés et contrats. Inspiré du style SAP Fiori.'

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description,
  ogImage: '/payohada-logo.png'
})

useHead({
  link: [
    { rel: 'icon', type: 'image/png', href: '/payohada-icon.png' },
    { rel: 'apple-touch-icon', href: '/payohada-icon.png' }
  ]
})
</script>

<template>
  <UApp>
    <div v-if="!initialized" class="min-h-screen bg-slate-50 flex flex-col items-center justify-center space-y-4">
      <img src="/payohada-icon.png" alt="payohada" class="w-12 h-12 object-contain animate-pulse mb-1" />
      <UIcon name="i-lucide-loader-2" class="w-6 h-6 animate-spin text-green-600" />
      <span class="text-xs text-slate-500 font-semibold tracking-wider uppercase">Initialisation de la session...</span>
    </div>
    <NuxtLayout v-else>
      <NuxtPage />
    </NuxtLayout>
    <AppChatbot v-if="initialized" />
  </UApp>
</template>
