<script setup>
const route = useRoute()
const router = useRouter()
const { get } = useApi()

const dossierId = route.params.dossierId
const etabId = route.params.etabId

const ids = route.query.ids ? String(route.query.ids).split(',') : []

const etablissement = ref(null)
const bulletinsData = ref([])
const loading = ref(true)

const loadAllData = async () => {
  if (ids.length === 0) {
    loading.value = false
    return
  }
  try {
    etablissement.value = await get(`/etablissements/${etabId}`)
    const promises = ids.map(async (bId) => {
      try {
        const b = await get(`/bulletins/${bId}`)
        const contrat = await get(`/contrats/${b.contrat_id}`)
        const salarie = await get(`/salaries/${contrat.salarie_id}`)
        return { bulletin: b, contrat, salarie }
      } catch (e) {
        console.error(`Error loading bulletin #${bId}:`, e)
        return null
      }
    })
    const results = await Promise.all(promises)
    bulletinsData.value = results.filter(Boolean)
  } catch (e) {
    console.error("Error loading print data:", e)
  } finally {
    loading.value = false
  }
}

// Helpers
const formatXOF = (value) => {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'XOF',
    maximumFractionDigits: 0
  }).format(value).replace('XOF', 'FCFA')
}

const formatPercent = (value) => {
  if (!value) return '-'
  return `${value.toFixed(2)} %`
}

const triggerPrint = () => {
  window.print()
}

const telechargementEnCours = ref(false)

/**
 * Télécharge l'ensemble des bulletins sélectionnés en un seul PDF, au format
 * Sage Saari, un bulletin par page. Le document est produit par le serveur :
 * c'est exactement celui qui est joint aux emails.
 */
const telechargerPdfLot = async () => {
  const identifiants = bulletinsData.value.map(item => item.bulletin.id)
  if (!identifiants.length) return

  telechargementEnCours.value = true
  try {
    const config = useRuntimeConfig()
    const { token } = useSupabase()
    const apiBase = config.public.apiBase || 'http://localhost:8000'
    const reponse = await fetch(`${apiBase}/api/v1/bulletins/pdf-lot`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token.value}`
      },
      body: JSON.stringify({ bulletin_ids: identifiants })
    })
    if (!reponse.ok) throw new Error(`HTTP ${reponse.status}`)

    const blob = await reponse.blob()
    const lien = document.createElement('a')
    lien.href = URL.createObjectURL(blob)
    lien.download = `bulletins_paie_${identifiants.length}_documents.pdf`
    lien.click()
    URL.revokeObjectURL(lien.href)
    useToast().add({
      title: 'PDF groupé téléchargé',
      description: `${identifiants.length} bulletin(s), un par page, au format Sage Saari.`,
      color: 'success'
    })
  } catch (e) {
    console.error('Erreur de téléchargement du lot :', e)
    useToast().add({
      title: 'Téléchargement impossible',
      description: 'La génération du PDF groupé a échoué.',
      color: 'danger'
    })
  } finally {
    telechargementEnCours.value = false
  }
}

onMounted(() => {
  loadAllData()
})
</script>

<template>
  <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4 no-print">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Préparation de l'impression...</span>
  </div>

  <div v-else-if="bulletinsData.length === 0" class="max-w-md mx-auto py-20 text-center space-y-4 no-print bg-white p-8 border-2 border-slate-200 shadow-flat">
    <div class="w-12 h-12 bg-slate-100 text-slate-400 rounded-none flex items-center justify-center mx-auto">
      <UIcon name="i-lucide-alert-circle" class="w-6 h-6" />
    </div>
    <h3 class="font-bold text-slate-900 text-lg">Aucun bulletin sélectionné</h3>
    <p class="text-xs text-slate-500">
      Veuillez retourner sur la liste des bulletins pour en sélectionner.
    </p>
    <NuxtLink 
      :to="`/dossiers/${dossierId}/etablissements/${etabId}?tab=bulletins`"
      class="inline-block px-4 py-2 border-2 border-slate-200 text-xs font-bold uppercase tracking-wider hover:bg-slate-50 text-slate-700 transition-all rounded-none"
    >
      Retourner aux bulletins
    </NuxtLink>
  </div>

  <div v-else class="space-y-6 print-container">
    <!-- Top toolbar hidden during printing -->
    <div class="bg-white border-2 border-slate-200 p-4 shadow-flat flex flex-col sm:flex-row justify-between items-center gap-4 no-print border-t-4 border-t-green-600">
      <div class="flex items-center space-x-3">
        <NuxtLink 
          :to="`/dossiers/${dossierId}/etablissements/${etabId}?tab=bulletins`"
          class="p-2 border-2 border-slate-200 rounded-none hover:bg-slate-50 text-slate-700 transition-colors"
        >
          <UIcon name="i-lucide-arrow-left" class="w-4 h-4" />
        </NuxtLink>
        <div>
          <h1 class="text-lg font-bold text-slate-900 leading-tight uppercase">
            Impression en Masse
          </h1>
          <p class="text-xs text-slate-500 uppercase font-semibold">
            {{ bulletinsData.length }} bulletin(s) sélectionné(s) prêt(s) à être imprimé(s)
          </p>
        </div>
      </div>

      <div>
        <button 
          @click="triggerPrint"
          class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-bold rounded-none shadow-flat transition-colors flex items-center gap-1.5 uppercase tracking-wider cursor-pointer shadow-flat-hover shadow-flat-active"
        >
          <UIcon name="i-lucide-printer" class="w-4 h-4" />
          Lancer l'impression
        </button>
        <button
          :disabled="telechargementEnCours"
          @click="telechargerPdfLot"
          class="ml-2 px-4 py-2 bg-slate-800 hover:bg-slate-900 disabled:bg-slate-400 text-white text-sm font-bold rounded-none transition-colors flex items-center gap-1.5 uppercase tracking-wider cursor-pointer"
        >
          <UIcon :name="telechargementEnCours ? 'i-lucide-loader-2' : 'i-lucide-download'"
                 class="w-4 h-4" :class="{ 'animate-spin': telechargementEnCours }" />
          Télécharger le PDF
        </button>
      </div>
    </div>

    <!-- Printable Payslips -->
    <!-- Bulletins de paie au format Sage Saari -->
    <div class="space-y-8 print:space-y-0">
      <BulletinPaieSaari
        v-for="(item, index) in bulletinsData"
        :key="item.bulletin.id"
        :bulletin="item.bulletin"
        :contrat="item.contrat"
        :salarie="item.salarie"
        :etablissement="etablissement"
        :rang="index + 1"
        :total="bulletinsData.length"
        class="print-payslip-page"
      />
    </div>
  </div>
</template>

<style scoped>
@media print {
  .no-print {
    display: none !important;
  }
  body, .print-container {
    background-color: transparent !important;
    color: black !important;
  }
  .print-payslip-page {
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    box-shadow: none !important;
    page-break-after: always;
    break-after: page;
  }
  .print-payslip-page:last-child {
    page-break-after: avoid;
    break-after: avoid;
  }
}
</style>
