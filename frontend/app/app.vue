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
  ogImage: '/logo.png'
})
</script>

<template>
  <UApp>
    <div v-if="!initialized" class="min-h-screen bg-slate-50 flex flex-col items-center justify-center space-y-4">
      <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
      <span class="text-sm text-slate-500 font-medium">Initialisation de la session...</span>
    </div>
    <NuxtLayout v-else>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
