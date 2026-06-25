<script setup>
const route = useRoute()
const router = useRouter()
const { get, put, delete: apiDelete } = useApi()
const toast = useToast()

const dossierId = route.params.dossierId
const etabId = route.params.etabId
const salarieId = route.params.salarieId
const contratId = route.params.contratId
const bulletinId = route.params.id

// Context & Data states
const loading = ref(true)
const currentDossier = useState('current-dossier')
const etablissement = ref(null)
const salarie = ref(null)
const contrat = ref(null)
const bulletin = ref(null)

const fetchDetails = async () => {
  loading.value = true
  try {
    // 1. Fetch Dossier Context
    if (!currentDossier.value) {
      currentDossier.value = await get(`/dossiers/${dossierId}`)
    }
    
    // 2. Fetch Etablissement
    etablissement.value = await get(`/etablissements/${etabId}`)
    
    // 3. Fetch Salarie
    salarie.value = await get(`/salaries/${salarieId}`)
    
    // 4. Fetch Contrat
    contrat.value = await get(`/contrats/${contratId}`)
    
    // 5. Fetch Bulletin details (includes lines and cumuls)
    bulletin.value = await get(`/bulletins/${bulletinId}`)
  } catch (e) {
    console.error("Error loading payslip details:", e)
    router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/${contratId}`)
  } finally {
    loading.value = false
  }
}

const handleValidate = async () => {
  if (!confirm('Êtes-vous sûr de vouloir valider définitivement ce bulletin ? Il ne pourra plus être modifié ni supprimé.')) return
  try {
    const res = await put(`/bulletins/${bulletinId}/valider`)
    if (res) {
      toast.add({
        title: 'Bulletin Validé',
        description: 'Le bulletin a été validé définitivement.',
        color: 'success'
      })
      await fetchDetails()
    }
  } catch (e) {
    console.error(e)
  }
}

const handleDelete = async () => {
  if (!confirm('Supprimer définitivement ce bulletin ?')) return
  try {
    await apiDelete(`/bulletins/${bulletinId}`)
    toast.add({
      title: 'Bulletin Supprimé',
      description: 'Le bulletin de salaire a été supprimé.',
      color: 'success'
    })
    router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/${contratId}`)
  } catch (e) {
    console.error(e)
  }
}

const triggerPrint = () => {
  window.print()
}

// Formatting helpers
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

const getPeriodLabel = (mois, annee) => {
  const months = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
  ]
  return `${months[mois - 1]} ${annee}`
}

onMounted(() => {
  fetchDetails()
})
</script>

<template>
  <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4 no-print">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement du bulletin de paie...</span>
  </div>

  <div v-else-if="bulletin" class="space-y-6">
    
    <!-- Action Bar (Hidden on Print) -->
    <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row justify-between items-center gap-4 no-print">
      <div class="flex items-center space-x-3">
        <NuxtLink 
          :to="`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/${contratId}`"
          class="p-2 border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-700 transition-colors"
        >
          <UIcon name="i-lucide-arrow-left" class="w-4 h-4" />
        </NuxtLink>
        <div>
          <h1 class="text-lg font-bold text-slate-900 leading-tight">
            Bulletin {{ getPeriodLabel(bulletin.mois, bulletin.annee) }}
          </h1>
          <p class="text-xs text-slate-500">
            Salarié : {{ salarie?.prenom }} {{ salarie?.nom?.toUpperCase() }} | Statut : 
            <span class="font-semibold uppercase" :class="bulletin.statut === 'valide' ? 'text-green-600' : 'text-yellow-600'">
              {{ bulletin.statut }}
            </span>
          </p>
        </div>
      </div>

      <div class="flex space-x-3 w-full sm:w-auto justify-end">
        <button 
          v-if="bulletin.statut !== 'valide'"
          @click="handleDelete"
          class="px-4 py-2 border border-red-200 text-sm font-semibold rounded-lg hover:bg-red-50 text-red-650 transition-colors flex items-center gap-1.5"
        >
          <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
          Supprimer
        </button>
        <button 
          v-if="bulletin.statut !== 'valide'"
          @click="handleValidate"
          class="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white text-sm font-semibold rounded-lg shadow transition-colors flex items-center gap-1.5"
        >
          <UIcon name="i-lucide-check-circle" class="w-4 h-4" />
          Valider
        </button>
        <button 
          @click="triggerPrint"
          class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded-lg shadow transition-colors flex items-center gap-1.5"
        >
          <UIcon name="i-lucide-printer" class="w-4 h-4" />
          Imprimer
        </button>
      </div>
    </div>

    <!-- Official Printable Payslip Container -->
    <div class="bg-white border border-slate-200 shadow-lg rounded-2xl p-8 max-w-4xl mx-auto print-payslip text-slate-800">
      
      <!-- Top Columns: Employer vs Employee -->
      <div class="grid grid-cols-2 gap-8 border-b border-slate-200 pb-6 text-xs">
        
        <!-- Left Side: Employer Info -->
        <div class="space-y-2">
          <div class="space-y-1">
            <h2 class="text-sm font-extrabold text-slate-900 uppercase">{{ etablissement?.raison_sociale }}</h2>
            <p class="text-slate-500 leading-relaxed">
              {{ etablissement?.adresse?.adresse_postale }}<br />
              {{ etablissement?.adresse?.adresse_postale2 || '' }}<br />
              {{ etablissement?.adresse?.code_postal }} {{ etablissement?.adresse?.ville }}<br />
              {{ etablissement?.adresse?.pays }}
            </p>
          </div>
          
          <div class="grid grid-cols-2 gap-2 border-t border-slate-100 pt-2 font-mono text-[10px] text-slate-500">
            <div>
              <span class="block text-[8px] font-bold uppercase tracking-wider text-slate-400">N° SIRET</span>
              <span>{{ etablissement?.siret || '-' }}</span>
            </div>
            <div>
              <span class="block text-[8px] font-bold uppercase tracking-wider text-slate-400">Code APE / NAF</span>
              <span>{{ etablissement?.ape || '-' }}</span>
            </div>
            <div class="col-span-2">
              <span class="block text-[8px] font-bold uppercase tracking-wider text-slate-400">N° Cotisant</span>
              <span>{{ etablissement?.numero_cotisant || '-' }}</span>
            </div>
          </div>
        </div>

        <!-- Right Side: Employee Info -->
        <div class="space-y-3">
          <div class="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
            <div class="flex justify-between border-b border-slate-200 pb-1">
              <span class="font-bold text-slate-900">{{ salarie?.civilite }} {{ salarie?.prenom }} {{ salarie?.nom?.toUpperCase() }}</span>
              <span class="font-mono text-slate-500 text-[10px]">Matricule : {{ salarie?.matricule }}</span>
            </div>
            
            <div class="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[10px] leading-tight">
              <div>
                <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">Emploi / Poste</span>
                <span class="font-medium text-slate-800">{{ contrat?.emploi || 'Non spécifié' }}</span>
              </div>
              <div>
                <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">Date d'embauche</span>
                <span class="font-mono text-slate-800">{{ contrat?.date_debut_contrat || '-' }}</span>
              </div>
              <div class="col-span-2 border-t border-slate-100 pt-1">
                <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">Adresse du Salarié</span>
                <span class="text-slate-650 font-sans">
                  {{ salarie?.adresse || '-' }} {{ salarie?.adresse2 || '' }}<br />
                  {{ salarie?.code_postal }} {{ salarie?.ville }}
                </span>
              </div>
              <div class="border-t border-slate-100 pt-1">
                <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">N° Securité Sociale</span>
                <span class="font-mono text-slate-800">{{ salarie?.numero_securite_sociale || '-' }}</span>
              </div>
              <div class="border-t border-slate-100 pt-1">
                <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">Régime</span>
                <span class="font-bold" :class="salarie?.expatrie ? 'text-amber-700' : 'text-slate-700'">
                  {{ salarie?.expatrie ? 'EXPATRIÉ (8.0% CN)' : 'LOCAL (1.5% CN)' }}
                </span>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Payslip Metadata / Period Bar -->
      <div class="my-4 py-3 px-4 bg-slate-50 border border-slate-200 rounded-xl flex justify-between items-center text-xs font-semibold">
        <div>
          <span>PÉRIODE : </span>
          <span class="font-bold text-slate-900 font-mono uppercase">{{ getPeriodLabel(bulletin.mois, bulletin.annee) }}</span>
        </div>
        <div>
          <span>DATE DE PAIEMENT : </span>
          <span class="font-mono text-slate-900">{{ bulletin.date_paiement ? new Date(bulletin.date_paiement).toLocaleDateString('fr-FR') : '-' }}</span>
        </div>
        <div>
          <span>MODE DE RÈGLEMENT : </span>
          <span class="text-slate-900">VIREMENT BANCAIRE</span>
        </div>
      </div>

      <!-- Main Pay Lines Table -->
      <div class="overflow-x-auto border border-slate-200 rounded-xl">
        <table class="min-w-full divide-y divide-slate-250 text-xs">
          <thead class="bg-slate-100 text-slate-650 font-bold uppercase tracking-wider text-[9px]">
            <tr>
              <th scope="col" class="px-4 py-3 text-left w-2/5">Rubrique / Libellé</th>
              <th scope="col" class="px-3 py-3 text-right">Base / Nombre</th>
              <th scope="col" class="px-3 py-3 text-right bg-slate-50/50">Taux Sal.</th>
              <th scope="col" class="px-3 py-3 text-right bg-slate-50/50">Ret. Salariale</th>
              <th scope="col" class="px-3 py-3 text-right bg-slate-100/50">Taux Pat.</th>
              <th scope="col" class="px-3 py-3 text-right bg-slate-100/50">Charge Patr.</th>
              <th scope="col" class="px-4 py-3 text-right">Gains</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-150 font-mono text-slate-700 bg-white">
            <tr v-for="line in bulletin.lignes" :key="line.code" class="hover:bg-slate-50/50">
              <td class="px-4 py-2 text-left font-sans font-medium text-slate-900">{{ line.libelle }}</td>
              
              <!-- Base/Nombre -->
              <td class="px-3 py-2 text-right text-slate-500">
                {{ line.base_s || line.base_p || '-' }}
              </td>
              
              <!-- Salariale -->
              <td class="px-3 py-2 text-right bg-slate-50/20 text-slate-400">
                {{ line.taux_s > 0 ? formatPercent(line.taux_s) : '-' }}
              </td>
              <td class="px-3 py-2 text-right bg-slate-50/20" :class="line.montant_cs > 0 ? 'text-slate-900 font-semibold' : 'text-slate-400'">
                {{ line.montant_cs > 0 ? formatXOF(line.montant_cs) : '-' }}
              </td>
              
              <!-- Patronale -->
              <td class="px-3 py-2 text-right bg-slate-100/10 text-slate-400">
                {{ line.taux_p > 0 ? formatPercent(line.taux_p) : '-' }}
              </td>
              <td class="px-3 py-2 text-right bg-slate-100/10" :class="line.montant_cp > 0 ? 'text-slate-900 font-semibold' : 'text-slate-400'">
                {{ line.montant_cp > 0 ? formatXOF(line.montant_cp) : '-' }}
              </td>

              <!-- Gains (sauf cotisations) -->
              <td class="px-4 py-2 text-right font-semibold text-slate-900" :class="{ 'text-red-600': line.montant_pr < 0 }">
                {{ line.montant_pr !== 0 ? formatXOF(line.montant_pr) : '-' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Totals & Net Pay Card Layout -->
      <div class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        
        <!-- Totals Table -->
        <div class="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2 text-xs">
          <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500 font-semibold">Total Salaire Brut :</span>
            <span class="font-bold font-mono text-slate-900">{{ formatXOF(bulletin.salaire_brut) }}</span>
          </div>
          <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500 font-semibold">Total Retenues Salariales :</span>
            <span class="font-bold font-mono text-slate-900">{{ formatXOF(bulletin.cotisations_salariales) }}</span>
          </div>
          <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500 font-semibold">Total Charges Patronales :</span>
            <span class="font-bold font-mono text-slate-900">{{ formatXOF(bulletin.cotisations_patronales) }}</span>
          </div>
          <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500 font-semibold">Net Imposable :</span>
            <span class="font-bold font-mono text-slate-900">{{ formatXOF(bulletin.net_imposable) }}</span>
          </div>
        </div>

        <!-- High-contrast Premium Net à Payer Callout -->
        <div class="bg-green-600 rounded-2xl p-5 text-white flex justify-between items-center shadow-lg">
          <div class="space-y-0.5">
            <p class="text-[9px] font-extrabold uppercase tracking-widest text-green-200">NET À PAYER</p>
            <p class="text-3xl font-black tracking-tight font-mono">
              {{ formatXOF(bulletin.net_a_payer) }}
            </p>
          </div>
          <div class="text-right text-[10px] text-green-100 leading-snug max-w-[160px] font-sans">
            Versement par virement bancaire.<br />
            <span class="italic text-[9px] text-green-200">Conservez ce bulletin sans limite de durée.</span>
          </div>
        </div>

      </div>

      <!-- Bottom Tables: Monthly/Annual Cumulates & Vacation Tracker -->
      <div v-if="bulletin.cumuls" class="mt-8 border-t border-slate-200 pt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <!-- Cumuls Table (cols-span 2) -->
        <div class="md:col-span-2 space-y-2">
          <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider">Cumuls Période et Annuel</h4>
          <div class="overflow-x-auto rounded-lg border border-slate-200">
            <table class="min-w-full divide-y divide-slate-200 text-[10px] text-left">
              <thead class="bg-slate-100 font-bold text-slate-650">
                <tr>
                  <th scope="col" class="px-2 py-1.5">Période</th>
                  <th scope="col" class="px-2 py-1.5 text-right">Heures/Jours</th>
                  <th scope="col" class="px-2 py-1.5 text-right">Brut (FCFA)</th>
                  <th scope="col" class="px-2 py-1.5 text-right">Brut CNPS</th>
                  <th scope="col" class="px-2 py-1.5 text-right">Retraite</th>
                  <th scope="col" class="px-2 py-1.5 text-right">IBS</th>
                  <th scope="col" class="px-2 py-1.5 text-right">CMU</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-150 font-mono text-slate-700 bg-white">
                <tr class="hover:bg-slate-50/50">
                  <td class="px-2 py-1.5 font-sans font-bold text-slate-900">Mensuel</td>
                  <td class="px-2 py-1.5 text-right">{{ bulletin.cumuls.mensuel.heures_jours }}</td>
                  <td class="px-2 py-1.5 text-right">{{ formatXOF(bulletin.cumuls.mensuel.salaire_brut) }}</td>
                  <td class="px-2 py-1.5 text-right">{{ formatXOF(bulletin.cumuls.mensuel.brut_cnps) }}</td>
                  <td class="px-2 py-1.5 text-right">{{ formatXOF(bulletin.cumuls.mensuel.cot_retraite) }}</td>
                  <td class="px-2 py-1.5 text-right">{{ formatXOF(bulletin.cumuls.mensuel.ibs) }}</td>
                  <td class="px-2 py-1.5 text-right">{{ formatXOF(bulletin.cumuls.mensuel.cmu) }}</td>
                </tr>
                <tr class="hover:bg-slate-50/50 bg-slate-50/30">
                  <td class="px-2 py-1.5 font-sans font-bold text-slate-900">Annuel</td>
                  <td class="px-2 py-1.5 text-right">{{ bulletin.cumuls.annuel.heures_jours }}</td>
                  <td class="px-2 py-1.5 text-right">{{ formatXOF(bulletin.cumuls.annuel.salaire_brut) }}</td>
                  <td class="px-2 py-1.5 text-right">{{ formatXOF(bulletin.cumuls.annuel.brut_cnps) }}</td>
                  <td class="px-2 py-1.5 text-right">{{ formatXOF(bulletin.cumuls.annuel.cot_retraite) }}</td>
                  <td class="px-2 py-1.5 text-right">{{ formatXOF(bulletin.cumuls.annuel.ibs) }}</td>
                  <td class="px-2 py-1.5 text-right">{{ formatXOF(bulletin.cumuls.annuel.cmu) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Congés Payés Card -->
        <div class="space-y-2">
          <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider">Congés Payés</h4>
          <div class="bg-white border border-slate-200 rounded-lg p-3 space-y-1.5 shadow-sm text-[10px] text-slate-650">
            <div class="flex justify-between font-mono">
              <span>Droits acquis :</span>
              <span class="font-bold text-slate-900">2.50 / mois</span>
            </div>
            <div class="flex justify-between font-mono">
              <span>Pris ce mois :</span>
              <span class="font-bold text-slate-900">0.00</span>
            </div>
            <div class="flex justify-between font-mono border-t border-slate-100 pt-1.5">
              <span>Solde disponible :</span>
              <span class="font-bold text-green-700 text-sm">2.50 jours</span>
            </div>
          </div>
        </div>

      </div>

    </div>
  </div>
</template>

<style scoped>
@media print {
  .no-print {
    display: none !important;
  }
  .print-payslip {
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    max-w: 100% !important;
    background: white !important;
    color: black !important;
  }
  body {
    background-color: white !important;
  }
}
</style>
