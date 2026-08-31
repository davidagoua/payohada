<script setup>
definePageMeta({
  layout: 'blank'
})

const route = useRoute()
const router = useRouter()
const { get } = useApi()

const dossierId = route.params.dossierId
const etabId = route.params.etabId
const salarieId = route.params.salarieId
const contratId = route.params.contratId

const contrat = ref(null)
const salarie = ref(null)
const etab = ref(null)
const dossier = ref(null)
const departSalarie = ref(null)
const loading = ref(true)

const fetchPrintData = async () => {
  loading.value = true
  try {
    contrat.value = await get(`/contrats/${contratId}`)
    salarie.value = await get(`/salaries/${salarieId}`)
    etab.value = await get(`/etablissements/${etabId}`)
    dossier.value = await get(`/dossiers/${dossierId}`)
    departSalarie.value = await get(`/contrats/${contratId}/depart`)
  } catch (e) {
    console.error("Error loading print data:", e)
  } finally {
    loading.value = false
  }
}

const printPage = () => {
  window.print()
}

onMounted(() => {
  fetchPrintData()
})
</script>

<template>
  <div v-if="loading" class="flex flex-col items-center justify-center min-h-screen space-y-4">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement du document...</span>
  </div>

  <div v-else-if="contrat && salarie" class="max-w-3xl mx-auto p-8 bg-white min-h-screen flex flex-col justify-between text-slate-900 relative">
    
    <!-- Actions Banner (hidden during printing) -->
    <div class="no-print mb-8 p-4 bg-slate-50 border border-slate-200 rounded-lg flex justify-between items-center shadow-sm">
      <button 
        @click="router.back()"
        class="px-3 py-1.5 border border-slate-200 text-slate-700 font-semibold rounded-lg text-xs hover:bg-slate-100 transition-colors flex items-center gap-1"
      >
        <UIcon name="i-lucide-arrow-left" class="w-4 h-4" />
        Retour
      </button>
      <button 
        @click="printPage"
        class="px-4 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow"
      >
        <UIcon name="i-lucide-printer" class="w-4 h-4" />
        Imprimer l'attestation
      </button>
    </div>

    <!-- Letterhead -->
    <div class="space-y-8">
      <div class="flex justify-between items-start border-b border-slate-200 pb-6">
        <div class="space-y-1.5">
          <h2 class="text-lg font-bold text-slate-800 uppercase">{{ etab.nom || dossier.nom }}</h2>
          <p class="text-xs text-slate-500">
            {{ etab.adresse || 'Adresse de l\'établissement' }}<br />
            NIF/RCCM : {{ etab.nif || 'Non spécifié' }}
          </p>
        </div>
        <div class="text-right text-xs text-slate-500">
          <p class="font-mono">Fait à {{ etab.ville || 'Dakar' }}, le {{ new Date().toLocaleDateString('fr-FR') }}</p>
        </div>
      </div>

      <!-- Main Title -->
      <div class="text-center py-6">
        <h1 class="text-2xl font-extrabold uppercase tracking-wider text-slate-900 border-b-4 border-slate-900 pb-2 inline-block">
          ATTESTATION DE TRAVAIL
        </h1>
      </div>

      <!-- Content -->
      <div class="space-y-6 text-sm leading-relaxed text-slate-800 pt-6">
        <p>
          Je soussigné(e), en qualité de Responsable des Ressources Humaines de la société <strong>{{ dossier.nom }}</strong>,
          atteste par la présente que :
        </p>

        <div class="text-center py-4 bg-slate-50 border border-slate-200 rounded-lg">
          <p class="text-base font-bold text-slate-900">
            Monsieur / Madame {{ salarie.prenom }} {{ salarie.nom }}
          </p>
          <p class="text-xs text-slate-500 font-mono mt-1">
            Matricule : {{ salarie.matricule }}
          </p>
        </div>

        <p class="text-justify">
          a été employé(e) au sein de notre établissement <strong>{{ etab.nom }}</strong>
          du <strong>{{ contrat.date_debut_contrat }}</strong> au 
          <strong>{{ departSalarie?.date_sortie || contrat.date_fin_previsionnelle_contrat || 'la date prévue de fin' }}</strong>,
          en qualité de : <strong>{{ contrat.emploi || 'Salarié(e)' }}</strong>.
        </p>

        <p class="text-justify">
          Cette attestation lui est délivrée à sa demande pour servir et valoir ce que de droit.
        </p>
      </div>
    </div>

    <!-- Signatures -->
    <div class="flex justify-end pt-24">
      <div class="w-1/2 text-right space-y-16">
        <div class="text-sm">
          <p class="font-bold text-slate-800">La Direction</p>
          <p class="text-xs text-slate-500 italic">Signature et cachet de l'entreprise</p>
        </div>
      </div>
    </div>

  </div>

  <div v-else class="text-center py-20 text-red-500">
    Une erreur s'est produite lors du chargement des données.
  </div>
</template>

<style scoped>
@media print {
  .no-print {
    display: none !important;
  }
}
</style>
