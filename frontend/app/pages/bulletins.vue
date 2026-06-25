<script setup>
const route = useRoute()
const router = useRouter()
const { get, post, put, delete: apiDelete } = useApi()
const toast = useToast()

// Global State for breadcrumbs / context
const currentDossier = useState('current-dossier')

// Period & Dossier state
const selectedDossierId = ref(null)
const selectedMois = ref(new Date().getMonth() + 1)
const selectedAnnee = ref(new Date().getFullYear())

// Data states
const dossiers = ref([])
const contracts = ref([])
const bulletinsMap = ref({})
const loadingDossiers = ref(true)
const loadingData = ref(false)

// Bulk processing states
const bulkProcessing = ref(false)
const bulkProgress = ref(0)
const bulkTotal = ref(0)

// Fetch all available dossiers
const fetchDossiers = async () => {
  loadingDossiers.value = true
  try {
    const data = await get('/dossiers')
    dossiers.value = data || []
    
    // Set initial selected dossier
    if (currentDossier.value) {
      selectedDossierId.value = currentDossier.value.id
    } else if (dossiers.value.length > 0) {
      // Default to first if none in state
      selectedDossierId.value = dossiers.value[0].id
      currentDossier.value = dossiers.value[0]
    }
  } catch (e) {
    console.error("Error loading dossiers:", e)
  } finally {
    loadingDossiers.value = false
  }
}

// Fetch contracts and bulletins for the selected dossier and period
const fetchDossierData = async () => {
  if (!selectedDossierId.value) return
  
  loadingData.value = true
  try {
    // Sync currentDossier state with selection
    const activeDossier = dossiers.value.find(d => d.id === Number(selectedDossierId.value))
    if (activeDossier) {
      currentDossier.value = activeDossier
    }
    
    // 1. Fetch contracts of this dossier
    const cts = await get(`/dossiers/${selectedDossierId.value}/contrats`)
    contracts.value = cts || []
    
    // 2. Fetch all generated bulletins of this dossier for the selected period
    const bList = await get(`/dossiers/${selectedDossierId.value}/bulletins`, { 
      query: { 
        mois: selectedMois.value, 
        annee: selectedAnnee.value 
      } 
    })
    
    // Map bulletins by contract_id
    const map = {}
    if (bList) {
      bList.forEach(b => {
        map[b.contrat_id] = b
      })
    }
    bulletinsMap.value = map
  } catch (e) {
    console.error("Error loading payroll data:", e)
  } finally {
    loadingData.value = false
  }
}

// Watch selected dossier or period to load data
watch([selectedDossierId, selectedMois, selectedAnnee], async () => {
  await fetchDossierData()
})

// Quick switcher to set dossier
const handleSelectDossier = (dId) => {
  selectedDossierId.value = dId
}

// Calculate single payslip (can also recalculate)
const handleCalculateSingle = async (contratId) => {
  try {
    const payload = {
      contrat_id: contratId,
      mois: Number(selectedMois.value),
      annee: Number(selectedAnnee.value),
      acompte: 0.0,
      commentaire: "Généré depuis la gestion globale des bulletins"
    }
    const res = await post('/bulletins/calculer', payload)
    if (res) {
      toast.add({
        title: 'Bulletin calculé',
        description: `Le bulletin a été généré avec succès.`,
        color: 'success'
      })
      await fetchDossierData()
    }
  } catch (e) {
    console.error(e)
  }
}

// Validate single draft payslip
const handleValidateSingle = async (bulletinId) => {
  try {
    const res = await put(`/bulletins/${bulletinId}/valider`)
    if (res) {
      toast.add({
        title: 'Bulletin Validé',
        description: 'Le bulletin a été validé définitivement.',
        color: 'success'
      })
      await fetchDossierData()
    }
  } catch (e) {
    console.error(e)
  }
}

// Delete single draft payslip
const handleDeleteSingle = async (bulletinId) => {
  if (!confirm('Supprimer définitivement ce bulletin de paie ?')) return
  try {
    await apiDelete(`/bulletins/${bulletinId}`)
    toast.add({
      title: 'Bulletin Supprimé',
      description: 'Le bulletin de salaire a été supprimé.',
      color: 'success'
    })
    await fetchDossierData()
  } catch (e) {
    console.error(e)
  }
}

// Calculate all missing bulletins in bulk
const handleCalculateAll = async () => {
  const pending = contracts.value.filter(c => !bulletinsMap.value[c.id])
  if (pending.length === 0) {
    toast.add({
      title: 'Info',
      description: 'Tous les bulletins sont déjà générés pour cette période.',
      color: 'warning'
    })
    return
  }

  if (!confirm(`Générer les bulletins de paie pour les ${pending.length} salarié(s) en attente ?`)) return

  bulkProcessing.value = true
  bulkProgress.value = 0
  bulkTotal.value = pending.length

  let successCount = 0
  for (let i = 0; i < pending.length; i++) {
    const c = pending[i]
    try {
      const payload = {
        contrat_id: c.id,
        mois: Number(selectedMois.value),
        annee: Number(selectedAnnee.value),
        acompte: 0.0,
        commentaire: "Calcul groupé automatique"
      }
      await post('/bulletins/calculer', payload)
      successCount++
    } catch (e) {
      console.error(`Error calculating for contract ${c.id}:`, e)
    }
    bulkProgress.value = i + 1
  }

  bulkProcessing.value = false
  toast.add({
    title: 'Génération terminée',
    description: `${successCount} bulletin(s) de salaire calculé(s) avec succès.`,
    color: 'success'
  })
  await fetchDossierData()
}

// Validate all draft bulletins in bulk
const handleValidateAll = async () => {
  const drafts = Object.values(bulletinsMap.value).filter(b => b.statut !== 'valide')
  if (drafts.length === 0) {
    toast.add({
      title: 'Info',
      description: 'Aucun bulletin en brouillon à valider.',
      color: 'warning'
    })
    return
  }

  if (!confirm(`Valider définitivement les ${drafts.length} bulletin(s) en brouillon pour la période ?`)) return

  bulkProcessing.value = true
  bulkProgress.value = 0
  bulkTotal.value = drafts.length

  let successCount = 0
  for (let i = 0; i < drafts.length; i++) {
    const b = drafts[i]
    try {
      await put(`/bulletins/${b.id}/valider`)
      successCount++
    } catch (e) {
      console.error(`Error validating bulletin ${b.id}:`, e)
    }
    bulkProgress.value = i + 1
  }

  bulkProcessing.value = false
  toast.add({
    title: 'Validation terminée',
    description: `${successCount} bulletin(s) validé(s) définitivement.`,
    color: 'success'
  })
  await fetchDossierData()
}

// Total Stats Calculators
const stats = computed(() => {
  const generatedBulletins = Object.values(bulletinsMap.value)
  let masseBrut = 0
  let masseNet = 0
  
  generatedBulletins.forEach(b => {
    masseBrut += b.salaire_brut || 0
    masseNet += b.net_a_payer || 0
  })

  return {
    totalEmployees: contracts.value.length,
    generatedCount: generatedBulletins.length,
    pendingCount: contracts.value.length - generatedBulletins.length,
    masseBrut,
    masseNet
  }
})

// Format helpers
const formatXOF = (value) => {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'XOF',
    maximumFractionDigits: 0
  }).format(value).replace('XOF', 'FCFA')
}

const getPeriodLabel = (mois, annee) => {
  const months = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
  ]
  return `${months[mois - 1]} ${annee}`
}

onMounted(async () => {
  await fetchDossiers()
  if (selectedDossierId.value) {
    await fetchDossierData()
  }
})
</script>

<template>
  <div class="space-y-6">
    
    <!-- Top Action / Title Header -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-50 text-green-700 rounded-lg flex items-center justify-center font-bold text-xl border border-green-200">
          <UIcon name="i-lucide-files" class="w-6 h-6" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-900 leading-tight">Gestion Administrative des Bulletins</h1>
          <p class="text-xs text-slate-500 mt-1">
            Gérez la paie, calculez et validez les bulletins de vos salariés par période.
          </p>
        </div>
      </div>

      <!-- Action buttons for selected dossier -->
      <div v-if="selectedDossierId && contracts.length > 0" class="flex flex-wrap gap-3 w-full md:w-auto justify-end">
        <button 
          @click="handleValidateAll"
          :disabled="loadingData || bulkProcessing || stats.generatedCount === 0"
          class="px-4 py-2 border border-slate-200 text-sm font-semibold rounded-lg hover:bg-slate-50 text-slate-700 transition-colors flex items-center gap-1.5 disabled:opacity-50"
        >
          <UIcon name="i-lucide-check-circle-2" class="w-4 h-4 text-green-600" />
          Valider la période
        </button>
        <button 
          @click="handleCalculateAll"
          :disabled="loadingData || bulkProcessing || stats.pendingCount === 0"
          class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors flex items-center gap-1.5 disabled:opacity-50"
        >
          <UIcon name="i-lucide-calculator" class="w-4 h-4" />
          Calculer les bulletins
        </button>
      </div>
    </div>

    <!-- Main Filter Bar -->
    <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center gap-4">
      <div class="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
        <span class="text-xs font-bold uppercase tracking-wider text-slate-400 shrink-0">Entreprise :</span>
        <select 
          v-model="selectedDossierId" 
          :disabled="loadingDossiers"
          class="block w-full sm:w-64 px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select"
        >
          <option v-if="dossiers.length === 0" value="">Aucune entreprise disponible</option>
          <option v-for="d in dossiers" :key="d.id" :value="d.id">{{ d.nom_dossier }} ({{ d.code }})</option>
        </select>
      </div>

      <div class="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto md:ml-4">
        <span class="text-xs font-bold uppercase tracking-wider text-slate-400 shrink-0">Période :</span>
        <div class="flex space-x-3 w-full sm:w-auto">
          <select v-model="selectedMois" class="block w-full sm:w-40 px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
            <option v-for="m in 12" :key="m" :value="m">{{ getPeriodLabel(m, 2026).split(' ')[0] }}</option>
          </select>
          <input 
            v-model="selectedAnnee" 
            type="number" 
            placeholder="Année" 
            class="block w-full sm:w-28 px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" 
          />
        </div>
      </div>
    </div>

    <!-- Progress bar for bulk actions -->
    <div v-if="bulkProcessing" class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-2">
      <div class="flex justify-between text-xs font-semibold text-slate-700">
        <span>Traitement groupé des fiches de paye...</span>
        <span>{{ bulkProgress }} / {{ bulkTotal }} ({{ Math.round((bulkProgress / bulkTotal) * 100) }}%)</span>
      </div>
      <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
        <div class="bg-green-600 h-full transition-all duration-300" :style="{ width: `${(bulkProgress / bulkTotal) * 100}%` }"></div>
      </div>
    </div>

    <!-- LOADING / INITIAL STATES -->
    <div v-if="loadingDossiers" class="flex flex-col items-center justify-center py-20 space-y-4">
      <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
      <span class="text-sm text-slate-500 font-medium">Chargement des dossiers d'entreprises...</span>
    </div>

    <!-- NO DOSSIER STATE -->
    <div v-else-if="dossiers.length === 0" class="bg-white border border-dashed border-slate-300 rounded-xl p-12 text-center max-w-xl mx-auto space-y-4 shadow-sm">
      <div class="w-12 h-12 bg-green-50 rounded-lg flex items-center justify-center text-green-600 mx-auto">
        <UIcon name="i-lucide-folder-open" class="w-6 h-6" />
      </div>
      <h3 class="font-bold text-slate-900 text-lg">Aucune entreprise trouvée</h3>
      <p class="text-sm text-slate-500">
        Vous devez d'abord créer un dossier d'entreprise avant de pouvoir gérer et générer des bulletins de paie.
      </p>
      <NuxtLink 
        to="/dossiers"
        class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-sm transition-colors inline-flex items-center space-x-2 shadow"
      >
        <UIcon name="i-lucide-folder-plus" class="w-4 h-4" />
        <span>Créer un dossier</span>
      </NuxtLink>
    </div>

    <!-- ENTERPRISE DETAILS DASHBOARD -->
    <div v-else-if="selectedDossierId" class="space-y-6">
      
      <!-- Statistics Cards Row -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        <!-- Total Employees -->
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Effectif Actif</span>
            <div class="w-7 h-7 bg-slate-100 text-slate-600 rounded-lg flex items-center justify-center">
              <UIcon name="i-lucide-users" class="w-4 h-4" />
            </div>
          </div>
          <p class="text-2xl font-bold text-slate-900">{{ stats.totalEmployees }} salariés</p>
          <div class="text-[10px] text-slate-450">Contrats déclarés au dossier</div>
        </div>

        <!-- Generated Bulletins -->
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Bulletins Calculés</span>
            <div class="w-7 h-7 bg-green-50 text-green-700 rounded-lg flex items-center justify-center">
              <UIcon name="i-lucide-check-circle-2" class="w-4 h-4" />
            </div>
          </div>
          <p class="text-2xl font-bold text-slate-900">{{ stats.generatedCount }} / {{ stats.totalEmployees }}</p>
          <div class="text-[10px] text-slate-450 flex items-center gap-1">
            <span v-if="stats.pendingCount > 0" class="text-yellow-600 font-semibold flex items-center gap-0.5">
              <span class="w-1.5 h-1.5 rounded-full bg-yellow-500 inline-block animate-pulse"></span>
              {{ stats.pendingCount }} en attente
            </span>
            <span v-else class="text-green-600 font-semibold flex items-center gap-0.5">
              Tous générés
            </span>
          </div>
        </div>

        <!-- Masse Salariale Brut -->
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Masse Brut</span>
            <div class="w-7 h-7 bg-blue-50 text-blue-700 rounded-lg flex items-center justify-center">
              <UIcon name="i-lucide-coins" class="w-4 h-4" />
            </div>
          </div>
          <p class="text-2xl font-bold text-slate-900 font-mono tracking-tight">{{ formatXOF(stats.masseBrut) }}</p>
          <div class="text-[10px] text-slate-450 font-sans">Total salaire brut brut pour la période</div>
        </div>

        <!-- Masse Salariale Net -->
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Masse Nette (Net à Payer)</span>
            <div class="w-7 h-7 bg-emerald-50 text-emerald-700 rounded-lg flex items-center justify-center">
              <UIcon name="i-lucide-banknote" class="w-4 h-4" />
            </div>
          </div>
          <p class="text-2xl font-bold text-green-700 font-mono tracking-tight">{{ formatXOF(stats.masseNet) }}</p>
          <div class="text-[10px] text-slate-450 font-sans">Montant total net versé par virement</div>
        </div>
      </div>

      <!-- Employees & Bulletins List Table Card -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div v-if="loadingData" class="flex flex-col items-center justify-center py-20 space-y-4">
          <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
          <span class="text-sm text-slate-500 font-medium">Chargement des fiches de paye...</span>
        </div>

        <div v-else-if="contracts.length === 0" class="text-center py-16 px-4 bg-white space-y-3">
          <div class="w-10 h-10 bg-slate-100 text-slate-400 rounded-full flex items-center justify-center mx-auto">
            <UIcon name="i-lucide-user-x" class="w-5 h-5" />
          </div>
          <h4 class="font-bold text-slate-800">Aucun salarié avec contrat actif</h4>
          <p class="text-xs text-slate-500 max-w-sm mx-auto">
            Afin de calculer la paie, vous devez d'abord ajouter des salariés et créer des contrats de travail actifs dans cette entreprise.
          </p>
          <NuxtLink 
            :to="`/dossiers/${selectedDossierId}`"
            class="px-3.5 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg transition-colors inline-flex items-center gap-1.5"
          >
            Aller au Dossier Client
          </NuxtLink>
        </div>

        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Employé</th>
                <th scope="col" class="px-6 py-3 text-left">Poste / Contrat</th>
                <th scope="col" class="px-6 py-3 text-left">Établissement</th>
                <th scope="col" class="px-6 py-3 text-left">Statut Bulletin</th>
                <th scope="col" class="px-6 py-3 text-right">Salaire Brut</th>
                <th scope="col" class="px-6 py-3 text-right">Net à Payer</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="c in contracts" :key="c.id" class="hover:bg-slate-50/50 transition-colors">
                
                <!-- Employee Column -->
                <td class="px-6 py-4">
                  <div class="flex items-center space-x-3">
                    <div class="w-8 h-8 bg-green-50 text-green-700 rounded-full flex items-center justify-center font-bold text-xs border border-green-200">
                      {{ c.matricule_salarie.substring(c.matricule_salarie.lastIndexOf('-') + 1) || 'EMP' }}
                    </div>
                    <div>
                      <span class="block font-bold text-slate-900 leading-tight">
                        {{ c.matricule_salarie }}
                      </span>
                      <span class="text-xs text-slate-500">
                        Type : {{ c.unite_temps === 'Jours' ? 'Journalier (Jours)' : 'Horaire (Heures)' }}
                      </span>
                    </div>
                  </div>
                </td>

                <!-- Job / Contract Column -->
                <td class="px-6 py-4">
                  <span class="block font-medium text-slate-800 leading-tight">
                    {{ c.emploi || 'Poste non renseigné' }}
                  </span>
                  <span class="text-[10px] font-mono text-slate-450">
                    Contrat N° {{ c.numero_contrat }}
                  </span>
                </td>

                <!-- Establishment Column -->
                <td class="px-6 py-4">
                  <div class="flex items-center space-x-1.5">
                    <UIcon name="i-lucide-building" class="w-3.5 h-3.5 text-slate-400" />
                    <span class="font-mono text-xs font-semibold text-slate-650 bg-slate-100 px-1.5 py-0.5 rounded">
                      {{ c.code_etablissement || 'NA' }}
                    </span>
                  </div>
                </td>

                <!-- Payslip Status Column -->
                <td class="px-6 py-4">
                  <span 
                    v-if="bulletinsMap[c.id]"
                    :class="[
                      bulletinsMap[c.id].statut === 'valide' 
                        ? 'bg-green-50 text-green-700 border-green-200' 
                        : 'bg-yellow-50 text-yellow-700 border-yellow-200',
                      'px-2.5 py-0.5 rounded text-[10px] uppercase font-bold border inline-block tracking-wider'
                    ]"
                  >
                    {{ bulletinsMap[c.id].statut }}
                  </span>
                  <span 
                    v-else 
                    class="bg-slate-100 text-slate-400 border-slate-200 px-2.5 py-0.5 rounded text-[10px] uppercase font-bold border inline-block tracking-wider"
                  >
                    Non calculé
                  </span>
                </td>

                <!-- Brut Salary -->
                <td class="px-6 py-4 text-right font-mono text-slate-600">
                  {{ bulletinsMap[c.id] ? formatXOF(bulletinsMap[c.id].salaire_brut) : '-' }}
                </td>

                <!-- Net Salary -->
                <td class="px-6 py-4 text-right font-mono font-bold text-slate-900">
                  {{ bulletinsMap[c.id] ? formatXOF(bulletinsMap[c.id].net_a_payer) : '-' }}
                </td>

                <!-- Individual Actions -->
                <td class="px-6 py-4 text-right">
                  <div class="flex justify-end items-center space-x-2">
                    
                    <!-- If payslip is generated -->
                    <template v-if="bulletinsMap[c.id]">
                      
                      <!-- View Link -->
                      <NuxtLink 
                        :to="`/dossiers/${selectedDossierId}/etablissements/${c.etablissement_id}/salaries/${c.salarie_id}/contrats/${c.id}/bulletins/${bulletinsMap[c.id].id}`"
                        class="px-2.5 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1"
                      >
                        <UIcon name="i-lucide-eye" class="w-3.5 h-3.5" />
                        Voir
                      </NuxtLink>
                      
                      <!-- Recalculate (recalculate is just running compute again) -->
                      <button 
                        v-if="bulletinsMap[c.id].statut !== 'valide'"
                        @click="handleCalculateSingle(c.id)"
                        class="p-1.5 border border-slate-200 hover:bg-slate-50 text-slate-500 hover:text-green-600 rounded-lg transition-colors"
                        title="Recalculer le bulletin"
                      >
                        <UIcon name="i-lucide-refresh-cw" class="w-3.5 h-3.5" />
                      </button>

                      <!-- Validate (if draft) -->
                      <button 
                        v-if="bulletinsMap[c.id].statut !== 'valide'"
                        @click="handleValidateSingle(bulletinsMap[c.id].id)"
                        class="p-1.5 border border-yellow-250 bg-yellow-50 hover:bg-yellow-100 text-yellow-700 rounded-lg transition-colors"
                        title="Valider définitivement"
                      >
                        <UIcon name="i-lucide-check-circle" class="w-3.5 h-3.5" />
                      </button>

                      <!-- Delete (if draft) -->
                      <button 
                        v-if="bulletinsMap[c.id].statut !== 'valide'"
                        @click="handleDeleteSingle(bulletinsMap[c.id].id)"
                        class="p-1.5 border border-red-200 bg-red-50 hover:bg-red-100 text-red-650 rounded-lg transition-colors"
                        title="Supprimer"
                      >
                        <UIcon name="i-lucide-trash-2" class="w-3.5 h-3.5" />
                      </button>

                    </template>

                    <!-- If not generated yet -->
                    <button 
                      v-else
                      @click="handleCalculateSingle(c.id)"
                      class="px-2.5 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 shadow-sm"
                    >
                      <UIcon name="i-lucide-calculator" class="w-3.5 h-3.5" />
                      Calculer
                    </button>
                    
                  </div>
                </td>

              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>

  </div>
</template>

<style scoped>
.select {
  appearance: none;
  background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236B7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='m6 8 4 4 4-4'/%3E%3C/svg%3E");
  background-position: right 0.5rem center;
  background-repeat: no-repeat;
  background-size: 1.25em 1.25em;
  padding-right: 2.5rem;
}
</style>
