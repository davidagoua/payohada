<script setup>
const { init } = useSupabase()

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
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
