<script setup>
import { INFOS_EMPLOYEUR, normaliserAffichage } from '~/utils/bulletinAffichage'

const route = useRoute()
const router = useRouter()
const { get } = useApi()

const dossierId = route.params.dossierId
const etabId = route.params.etabId

const ids = route.query.ids ? String(route.query.ids).split(',') : []

const etablissement = ref(null)
const logo = ref(null)
const bulletinsData = ref([])
const loading = ref(true)

// Informations de l'employeur et signatures à imprimer. Le choix est mémorisé
// par établissement dans ce navigateur ; il s'applique aussi au PDF téléchargé.
const CLE_MEMOIRE = `bulletin-affichage:${etabId}`
const lireAffichage = () => {
  try {
    return normaliserAffichage(JSON.parse(localStorage.getItem(CLE_MEMOIRE) || 'null'))
  } catch {
    return normaliserAffichage(null)
  }
}
const affichage = ref(lireAffichage())
watch(affichage, (valeur) => {
  try {
    localStorage.setItem(CLE_MEMOIRE, JSON.stringify(valeur))
  } catch {
    // Stockage indisponible (navigation privée) : le choix vaut pour la page.
  }
}, { deep: true })

const loadAllData = async () => {
  if (ids.length === 0) {
    loading.value = false
    return
  }
  try {
    etablissement.value = await get(`/etablissements/${etabId}`)
    // Logo de l'entreprise : demandé seulement s'il existe (un 404 afficherait une erreur).
    const dossier = await get(`/dossiers/${dossierId}`)
    if (dossier?.a_logo) {
      logo.value = (await get(`/dossiers/${dossierId}/logo`))?.data_url || null
    }
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
    const apiBase = resoudreApiBase(config.public.apiBase)
    const reponse = await fetch(`${apiBase}/bulletins/pdf-lot`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token.value}`
      },
      body: JSON.stringify({ bulletin_ids: identifiants, affichage: affichage.value })
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
    <Icon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Préparation de l'impression...</span>
  </div>

  <div v-else-if="bulletinsData.length === 0" class="max-w-md mx-auto py-20 text-center space-y-4 no-print bg-white p-8 border-2 border-slate-200 shadow-flat">
    <div class="w-12 h-12 bg-slate-100 text-slate-400 rounded-lg flex items-center justify-center mx-auto">
      <Icon name="i-lucide-alert-circle" class="w-6 h-6" />
    </div>
    <h3 class="font-bold text-navy-900 text-lg">Aucun bulletin sélectionné</h3>
    <p class="text-xs text-slate-500">
      Veuillez retourner sur la liste des bulletins pour en sélectionner.
    </p>
    <NuxtLink 
      :to="`/dossiers/${dossierId}/etablissements/${etabId}?tab=bulletins`"
      class="inline-block px-4 py-2 border-2 border-slate-200 text-xs font-bold uppercase tracking-wider hover:bg-slate-50 text-slate-700 transition-all rounded-lg"
    >
      Retourner aux bulletins
    </NuxtLink>
  </div>

  <div v-else class="space-y-6 print-container">
    <!-- Top toolbar hidden during printing -->
    <div class="bg-white border-2 border-slate-200 p-4 shadow-flat flex flex-col sm:flex-row justify-between items-center gap-4 no-print border-t-4 border-t-navy-900">
      <div class="flex items-center space-x-3">
        <NuxtLink 
          :to="`/dossiers/${dossierId}/etablissements/${etabId}?tab=bulletins`"
          class="p-2 border-2 border-slate-200 rounded-lg hover:bg-slate-50 text-slate-700 transition-colors"
        >
          <Icon name="i-lucide-arrow-left" class="w-4 h-4" />
        </NuxtLink>
        <div>
          <h1 class="text-lg font-bold text-navy-900 leading-tight uppercase">
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
          class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-bold rounded-lg shadow-flat transition-colors flex items-center gap-1.5 uppercase tracking-wider cursor-pointer shadow-flat-hover shadow-flat-active"
        >
          <Icon name="i-lucide-printer" class="w-4 h-4" />
          Lancer l'impression
        </button>
        <button
          :disabled="telechargementEnCours"
          @click="telechargerPdfLot"
          class="ml-2 px-4 py-2 bg-slate-800 hover:bg-slate-900 disabled:bg-slate-400 text-white text-sm font-bold rounded-lg transition-colors flex items-center gap-1.5 uppercase tracking-wider cursor-pointer"
        >
          <Icon :name="telechargementEnCours ? 'i-lucide-loader-2' : 'i-lucide-download'"
                 class="w-4 h-4" :class="{ 'animate-spin': telechargementEnCours }" />
          Télécharger le PDF
        </button>
      </div>
    </div>

    <!-- Options d'affichage, masquées à l'impression -->
    <section
      class="bg-white border-2 border-slate-200 p-4 shadow-flat no-print space-y-3"
      aria-labelledby="titre-options-bulletin"
    >
      <h2 id="titre-options-bulletin" class="text-sm font-bold text-navy-900 uppercase tracking-wider">
        Informations à afficher sur le bulletin
      </h2>
      <fieldset>
        <legend class="text-xs text-slate-500 mb-2">Entreprise / établissement</legend>
        <div class="flex flex-wrap gap-x-6 gap-y-2">
          <div v-for="info in INFOS_EMPLOYEUR" :key="info.cle" class="flex items-center gap-2">
            <Checkbox v-model="affichage.infos_employeur" :input-id="`info-${info.cle}`" :value="info.cle" />
            <label :for="`info-${info.cle}`">{{ info.libelle }}</label>
          </div>
        </div>
      </fieldset>
      <div class="flex items-center gap-2 border-t border-slate-200 pt-3">
        <Checkbox v-model="affichage.signatures" input-id="info-signatures" binary />
        <label for="info-signatures">Afficher la zone des signatures</label>
      </div>
    </section>

    <!-- Printable Payslips -->
    <!-- Bulletins de paie au format Sage Saari -->
    <div class="space-y-8 print:space-y-0">
      <BulletinPaieSaari
        v-for="item in bulletinsData"
        :key="item.bulletin.id"
        :bulletin="item.bulletin"
        :contrat="item.contrat"
        :salarie="item.salarie"
        :etablissement="etablissement"
        :affichage="affichage"
        :logo="logo"
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
