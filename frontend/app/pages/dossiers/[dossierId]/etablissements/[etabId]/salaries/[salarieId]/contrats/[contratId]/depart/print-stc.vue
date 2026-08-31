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
const soldeToutCompte = ref(null)
const loading = ref(true)

const fetchPrintData = async () => {
  loading.value = true
  try {
    contrat.value = await get(`/contrats/${contratId}`)
    salarie.value = await get(`/salaries/${salarieId}`)
    etab.value = await get(`/etablissements/${etabId}`)
    dossier.value = await get(`/dossiers/${dossierId}`)
    departSalarie.value = await get(`/contrats/${contratId}/depart`)
    soldeToutCompte.value = await get(`/contrats/${contratId}/solde-tout-compte`)
  } catch (e) {
    console.error("Error loading print data:", e)
  } finally {
    loading.value = false
  }
}

const getMotifLabel = (code) => {
  const motifs = {
    10: 'Démission',
    20: 'Licenciement',
    30: 'Rupture conventionnelle',
    40: 'Fin de CDD',
    50: 'Retraite',
    60: 'Décès',
    70: 'Force majeure',
    99: 'Autre motif'
  }
  return motifs[code] || 'Non spécifié'
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
        Imprimer le reçu
      </button>
    </div>

    <!-- Letterhead -->
    <div class="space-y-6">
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
        <h1 class="text-xl font-extrabold uppercase tracking-wider text-slate-900 border-2 border-slate-900 py-2.5 px-4 inline-block">
          REÇU POUR SOLDE DE TOUT COMPTE
        </h1>
      </div>

      <!-- Content -->
      <div class="space-y-4 text-sm leading-relaxed text-slate-800">
        <p>
          Je soussigné(e), <strong>{{ salarie.prenom }} {{ salarie.nom }}</strong>, demeurant au {{ salarie.adresse || 'l\'adresse renseignée' }},
          reconnais avoir reçu de la société <strong>{{ dossier.nom }} (Établissement {{ etab.nom }})</strong>,
          la somme totale nette de :
        </p>

        <div v-if="soldeToutCompte" class="bg-slate-50 border border-slate-200 p-4 font-mono rounded-lg space-y-2">
          <div class="text-center text-lg font-bold text-green-700 border-b border-slate-200 pb-2 mb-2">
            {{ soldeToutCompte.total?.toLocaleString('fr-FR') }} FCFA
          </div>
          <div class="space-y-1.5 text-xs text-slate-655">
            <div class="flex justify-between">
              <span>- Indemnité compensatrice de congés payés :</span>
              <span>{{ soldeToutCompte.indemnite_conges_payes?.toLocaleString('fr-FR') }} FCFA</span>
            </div>
            <div class="flex justify-between">
              <span>- Indemnité de licenciement / rupture :</span>
              <span>{{ soldeToutCompte.indemnite_licenciement?.toLocaleString('fr-FR') }} FCFA</span>
            </div>
            <div class="flex justify-between">
              <span>- Indemnité compensatrice de préavis :</span>
              <span>{{ soldeToutCompte.indemnite_preavis?.toLocaleString('fr-FR') }} FCFA</span>
            </div>
            <div class="flex justify-between border-t border-slate-200 pt-1.5 font-bold text-slate-900">
              <span>Total :</span>
              <span>{{ soldeToutCompte.total?.toLocaleString('fr-FR') }} FCFA</span>
            </div>
          </div>
        </div>

        <p>
          Cette somme m'est versée en règlement de tout compte, pour solde de tout salaire, indemnités de toutes natures
          dues au titre de l'exécution et de la cessation de mon contrat de travail, lequel a pris fin le 
          <strong>{{ departSalarie?.date_sortie || contrat.date_fin_previsionnelle_contrat || 'la date prévue' }}</strong>
          pour le motif suivant : <strong>{{ getMotifLabel(departSalarie?.motif_sortie) }}</strong>.
        </p>

        <p class="text-justify">
          Le présent reçu pour solde de tout compte est établi en double exemplaire, dont un m'a été remis.
          Je reconnais avoir été informé(e) que je dispose d'un délai de six (6) mois à compter de la signature de ce document
          pour le dénoncer par lettre recommandée, passé ce délai, le reçu devient libératoire pour l'employeur pour les sommes qui y sont portées.
        </p>
      </div>
    </div>

    <!-- Signatures -->
    <div class="grid grid-cols-2 gap-12 pt-16 border-t border-slate-100">
      <div class="space-y-12">
        <p class="text-xs font-semibold text-slate-500 uppercase">Le Salarié</p>
        <div class="text-xs text-slate-450 italic">
          (Faire précéder de la mention manuscrite<br />"Bon pour solde de tout compte")
        </div>
      </div>
      <div class="space-y-12 text-right">
        <p class="text-xs font-semibold text-slate-500 uppercase">L'Employeur</p>
        <div class="text-xs text-slate-450 italic">
          (Signature et cachet de l'entreprise)
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
