<script setup>
const route = useRoute()
const router = useRouter()
const { get, post, put } = useApi()
const toast = useToast()

const dossierId = route.params.dossierId
const currentDossier = useState('current-dossier')

// Period filters
const selectedMois = ref(new Date().getMonth() + 1)
const selectedAnnee = ref(new Date().getFullYear())

// Data states
const contracts = ref([])
const bulletinsMap = ref({})
const loading = ref(true)
const bulkProcessing = ref(false)
const bulkProgress = ref(0)
const bulkTotal = ref(0)

const selectedBulletins = ref([])

const allBulletinsSelected = computed({
  get: () => contracts.value.length > 0 && selectedBulletins.value.length === contracts.value.length,
  set: (val) => {
    if (val) {
      selectedBulletins.value = contracts.value.map(c => c.id)
    } else {
      selectedBulletins.value = []
    }
  }
})

const handleCalculateSelected = async () => {
  const pending = selectedBulletins.value.filter(cId => !bulletinsMap.value[cId])
  if (pending.length === 0) {
    toast.add({
      title: 'Info',
      description: 'Tous les bulletins de la sélection sont déjà générés.',
      color: 'warning'
    })
    return
  }

  if (!confirm(`Générer les bulletins de paie pour les ${pending.length} salarié(s) sélectionnés en attente ?`)) return

  bulkProcessing.value = true
  bulkProgress.value = 0
  bulkTotal.value = pending.length

  let successCount = 0
  for (let i = 0; i < pending.length; i++) {
    const cId = pending[i]
    try {
      const payload = {
        contrat_id: cId,
        mois: Number(selectedMois.value),
        annee: Number(selectedAnnee.value),
        acompte: 0.0,
        commentaire: "Calcul groupé de la sélection"
      }
      await post('/bulletins/calculer', payload)
      successCount++
    } catch (e) {
      console.error(`Error calculating for contract ${cId}:`, e)
    }
    bulkProgress.value = i + 1
  }

  bulkProcessing.value = false
  toast.add({
    title: 'Génération terminée',
    description: `${successCount} bulletin(s) de salaire calculé(s) avec succès.`,
    color: 'success'
  })
  selectedBulletins.value = []
  await fetchDossierData()
}

const handleValidateSelected = async () => {
  const drafts = selectedBulletins.value
    .map(cId => bulletinsMap.value[cId])
    .filter(b => b && b.statut !== 'valide')

  if (drafts.length === 0) {
    toast.add({
      title: 'Info',
      description: 'Aucun bulletin en brouillon sélectionné à valider.',
      color: 'warning'
    })
    return
  }

  if (!confirm(`Valider définitivement les ${drafts.length} bulletin(s) sélectionnés en brouillon ?`)) return

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
  selectedBulletins.value = []
  await fetchDossierData()
}

const fetchDossierData = async () => {
  loading.value = true
  try {
    if (!currentDossier.value) {
      currentDossier.value = await get(`/dossiers/${dossierId}`)
    }
    
    // Fetch all contracts of this dossier
    const cts = await get(`/dossiers/${dossierId}/contrats`)
    contracts.value = cts || []
    
    // Fetch all generated bulletins of this dossier for the selected period
    const bList = await get(`/dossiers/${dossierId}/bulletins`, { 
      query: { 
        mois: selectedMois.value, 
        annee: selectedAnnee.value 
      } 
    })
    
    // Map bulletins by contract_id for easy lookup
    const map = {}
    if (bList) {
      bList.forEach(b => {
        map[b.contrat_id] = b
      })
    }
    bulletinsMap.value = map
  } catch (e) {
    console.error("Error loading bulk payroll dashboard:", e)
  } finally {
    loading.value = false
  }
}

// Watch period changes to reload data
watch([selectedMois, selectedAnnee], () => {
  fetchDossierData()
})

const handleCalculateSingle = async (contratId) => {
  try {
    const payload = {
      contrat_id: contratId,
      mois: Number(selectedMois.value),
      annee: Number(selectedAnnee.value),
      acompte: 0.0,
      commentaire: "Généré depuis le tableau de bord global"
    }
    const res = await post('/bulletins/calculer', payload)
    if (res) {
      toast.add({
        title: 'Bulletin calculé',
        description: `Bulletin généré pour le contrat ID ${contratId}.`,
        color: 'success'
      })
      await fetchDossierData()
    }
  } catch (e) {
    console.error(e)
  }
}

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

onMounted(() => {
  fetchDossierData()
})
</script>

<template>
  <div class="space-y-6">
    
    <!-- Header bar -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-50 text-green-700 rounded-lg flex items-center justify-center font-bold text-xl border border-green-200">
          <UIcon name="i-lucide-files" class="w-6 h-6" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-900 leading-tight">Traitement de la Paie Globale</h1>
          <p class="text-xs text-slate-500 mt-1">
            Dossier : <span class="font-bold text-slate-700">{{ currentDossier?.nom_dossier }}</span> | Gérer les bulletins en masse.
          </p>
        </div>
      </div>

      <!-- Action buttons -->
      <div class="flex flex-wrap gap-3 w-full md:w-auto justify-end">
        <button 
          @click="handleValidateAll"
          :disabled="loading || bulkProcessing"
          class="px-4 py-2 border border-slate-200 text-sm font-semibold rounded-lg hover:bg-slate-50 text-slate-700 transition-colors flex items-center gap-1.5 disabled:opacity-50"
        >
          <UIcon name="i-lucide-check-circle-2" class="w-4 h-4 text-green-600" />
          Valider la période
        </button>
        <button 
          @click="handleCalculateAll"
          :disabled="loading || bulkProcessing"
          class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors flex items-center gap-1.5 disabled:opacity-50"
        >
          <UIcon name="i-lucide-calculator" class="w-4 h-4" />
          Calculer les bulletins
        </button>
      </div>
    </div>

    <!-- Filters Section -->
    <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row items-center gap-4">
      <span class="text-xs font-bold uppercase tracking-wider text-slate-400 shrink-0">Filtre Période :</span>
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
      
      <div class="text-xs font-medium text-slate-500 sm:ml-auto">
        Salariés actifs : <span class="font-bold text-slate-800">{{ contracts.length }}</span> | 
        Bulletins générés : <span class="font-bold text-green-600">{{ Object.keys(bulletinsMap).length }}</span>
      </div>
    </div>

    <!-- Progress bar for bulk actions -->
    <div v-if="bulkProcessing" class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-2">
      <div class="flex justify-between text-xs font-semibold text-slate-700">
        <span>Traitement groupé en cours...</span>
        <span>{{ bulkProgress }} / {{ bulkTotal }} ({{ Math.round((bulkProgress / bulkTotal) * 100) }}%)</span>
      </div>
      <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
        <div class="bg-green-600 h-full transition-all duration-300" :style="{ width: `${(bulkProgress / bulkTotal) * 100}%` }"></div>
      </div>
    </div>

    <!-- Bulk Actions Bar -->
    <div v-if="selectedBulletins.length > 0" class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row justify-between items-center gap-3 text-xs transition-all">
      <div class="font-bold text-slate-700">
        {{ selectedBulletins.length }} bulletin(s) sélectionné(s)
      </div>
      <div class="flex flex-wrap gap-2 justify-end w-full sm:w-auto">
        <button 
          @click="handleCalculateSelected"
          class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors flex items-center gap-1 cursor-pointer"
        >
          <UIcon name="i-lucide-calculator" class="w-3.5 h-3.5" />
          Calculer la sélection
        </button>
        <button 
          @click="handleValidateSelected"
          class="px-3 py-1.5 bg-yellow-500 hover:bg-yellow-650 text-slate-900 font-semibold rounded-lg transition-colors flex items-center gap-1 cursor-pointer"
        >
          <UIcon name="i-lucide-check-circle-2" class="w-3.5 h-3.5" />
          Valider la sélection
        </button>
      </div>
    </div>

    <!-- Employees & Bulletins List Table -->
    <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4">
        <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
        <span class="text-sm text-slate-500 font-medium">Chargement des fiches paie...</span>
      </div>

      <div v-else-if="contracts.length === 0" class="text-center py-16 text-slate-500 italic text-sm bg-white">
        Aucun salarié / contrat de travail trouvé dans ce dossier d'entreprise.
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
          <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
            <tr>
              <th scope="col" class="px-4 py-3 text-left w-10">
                <input type="checkbox" v-model="allBulletinsSelected" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
              </th>
              <th scope="col" class="px-6 py-3 text-left">Employé</th>
              <th scope="col" class="px-6 py-3 text-left">N° Contrat / Poste</th>
              <th scope="col" class="px-6 py-3 text-left">Statut Bulletin</th>
              <th scope="col" class="px-6 py-3 text-right">Salaire Brut</th>
              <th scope="col" class="px-6 py-3 text-right">Net à Payer</th>
              <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-150 bg-white">
            <tr v-for="c in contracts" :key="c.id" class="hover:bg-slate-50 transition-colors">
              <td class="px-4 py-4" @click.stop>
                <input type="checkbox" :value="c.id" v-model="selectedBulletins" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
              </td>
              
              <!-- Employee Column -->
              <td class="px-6 py-4">
                <div class="flex items-center space-x-3">
                  <div class="w-8 h-8 bg-green-50 text-green-700 rounded-full flex items-center justify-center font-bold text-xs border border-green-200">
                    {{ c.matricule_salarie.substring(c.matricule_salarie.lastIndexOf('-') + 1) }}
                  </div>
                  <div>
                    <span class="block font-bold text-slate-900 leading-tight">
                      {{ c.matricule_salarie }}
                    </span>
                    <span class="text-xs text-slate-500">
                      Régime : {{ c.unite_temps === 'Jours' ? 'Journalier' : 'Horaire' }}
                    </span>
                  </div>
                </div>
              </td>

              <!-- Contract Column -->
              <td class="px-6 py-4">
                <span class="block font-medium text-slate-800 leading-tight">
                  {{ c.emploi || 'Poste non spécifié' }}
                </span>
                <span class="text-[10px] font-mono text-slate-450">
                  N° {{ c.numero_contrat }}
                </span>
              </td>

              <!-- Payslip Status Column -->
              <td class="px-6 py-4">
                <span 
                  v-if="bulletinsMap[c.id]"
                  :class="[
                    bulletinsMap[c.id].statut === 'valide' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-yellow-50 text-yellow-700 border-yellow-200',
                    'px-2.5 py-0.5 rounded text-[10px] uppercase font-bold border inline-block'
                  ]"
                >
                  {{ bulletinsMap[c.id].statut }}
                </span>
                <span 
                  v-else 
                  class="bg-slate-100 text-slate-400 border-slate-200 px-2.5 py-0.5 rounded text-[10px] uppercase font-bold border inline-block"
                >
                  Non calculé
                </span>
              </td>

              <!-- Brut Column -->
              <td class="px-6 py-4 text-right font-mono text-slate-650">
                {{ bulletinsMap[c.id] ? formatXOF(bulletinsMap[c.id].salaire_brut) : '-' }}
              </td>

              <!-- Net Column -->
              <td class="px-6 py-4 text-right font-mono font-bold text-slate-900">
                {{ bulletinsMap[c.id] ? formatXOF(bulletinsMap[c.id].net_a_payer) : '-' }}
              </td>

              <!-- Actions Column -->
              <td class="px-6 py-4 text-right">
                <div class="flex justify-end space-x-2">
                  <NuxtLink 
                    v-if="bulletinsMap[c.id]"
                    :to="`/dossiers/${dossierId}/etablissements/${c.etablissement_id}/salaries/${c.salarie_id}/contrats/${c.id}/bulletins/${bulletinsMap[c.id].id}`"
                    class="px-2.5 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1"
                  >
                    <UIcon name="i-lucide-eye" class="w-3.5 h-3.5" />
                    Voir
                  </NuxtLink>
                  <button 
                    v-else
                    @click="handleCalculateSingle(c.id)"
                    class="px-2.5 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1"
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
</template>
