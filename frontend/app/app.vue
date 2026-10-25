<script setup>
const { init, initialized } = useSupabase()

onMounted(() => {
  init()
})

const title = 'payohada — Logiciel de Paie'
const description = 'Logiciel moderne de gestion de paie : dossiers entreprises, salariés et contrats.'

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description,
  ogImage: '/payohada-logo.png'
})

useHead({
  // La barre du navigateur mobile reprend l'encre navy de la marque.
  meta: [
    { name: 'theme-color', content: '#01173a' }
  ],
  link: [
    { rel: 'icon', type: 'image/png', href: '/payohada-icon.png' },
    { rel: 'apple-touch-icon', href: '/payohada-icon.png' }
  ]
})
</script>

<template>
  <UApp>
    <div v-if="!initialized" class="min-h-screen bg-navy-950 flex flex-col items-center justify-center space-y-5">
      <img src="/payohada-logo-light.png" alt="payohada" class="h-12 w-auto object-contain animate-pulse mb-1" />
      <UIcon name="i-lucide-loader-2" class="w-6 h-6 animate-spin text-green-500" />
      <span class="text-xs text-slate-300 font-semibold tracking-wider uppercase">Initialisation de la session...</span>
    </div>
    <NuxtLayout v-else>
      <NuxtPage />
    </NuxtLayout>
    <AppChatbot v-if="initialized" />
  </UApp>
</template>
