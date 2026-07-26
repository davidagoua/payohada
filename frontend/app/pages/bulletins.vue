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
  if (!confirm('Êtes-vous sûr de vouloir valider définitivement ce bulletin ? Il ne pourra plus être modifié ni supprimé.')) return
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

// Active context for modal actions
const activeContrat = ref(null)
const activeBulletin = ref(null)

// Add Heure Supp state
const hsModalOpen = ref(false)
const hsCode = ref('HS_15')
const hsNombre = ref(0)

// Add Absence state
const absModalOpen = ref(false)
const absCode = ref('CONGES')
const absDateDebut = ref('')
const absDateFin = ref('')
const absNbrHeure = ref(0)
const absNbrJour = ref(0)

// Add Prime state
const primeModalOpen = ref(false)
const primeCode = ref('PRIME_RENDEMENT')
const primeLibelle = ref('')
const primeMontant = ref(0)
const primeMode = ref('direct')
const primeBase = ref(0)
const primeTaux = ref(0)
const primeEstPersistant = ref(false)

// Acompte state
const acompteModalOpen = ref(false)
const acompteMontant = ref(0)

// Plan de paie items & dynamic lists
const planPaieItems = ref([])

const primesDisponibles = computed(() => {
  const excludedCodes = ['BASE', 'SURSALAIRE', 'ABS', '1001', '1051', '1101', '1111', '1121', '1131', '1141', '1151', '1161', '1181']
  return planPaieItems.value.filter(item => {
    return item.type === 'B' &&
           !excludedCodes.includes(item.code) &&
           !item.code.startsWith('HS_') &&
           !item.code.startsWith('ABS_') &&
           item.est_actif
  })
})

const fetchPlanPaie = async () => {
  try {
    planPaieItems.value = await get('/plan-paie') || []
  } catch (e) {
    console.error("Error loading plan de paie:", e)
  }
}

watch(primeCode, (newCode) => {
  const match = primesDisponibles.value.find(p => p.code === newCode)
  if (match) {
    primeLibelle.value = match.libelle
  }
})

watch(primeModalOpen, (isOpen) => {
  if (isOpen && primesDisponibles.value.length > 0) {
    if (!primesDisponibles.value.some(p => p.code === primeCode.value)) {
      primeCode.value = primesDisponibles.value[0].code
    }
    const match = primesDisponibles.value.find(p => p.code === primeCode.value)
    if (match) {
      primeLibelle.value = match.libelle
    }
  }
})

// Modal quick open handlers
const openPrimeModal = (contratId) => {
  activeContrat.value = contracts.value.find(c => c.id === contratId)
  activeBulletin.value = bulletinsMap.value[contratId]
  if (primesDisponibles.value.length > 0) {
    primeCode.value = primesDisponibles.value[0].code
    primeLibelle.value = primesDisponibles.value[0].libelle
  } else {
    primeCode.value = 'PRIME_RENDEMENT'
    primeLibelle.value = 'Prime de rendement'
  }
  primeMontant.value = 0
  primeMode.value = 'direct'
  primeBase.value = 0
  primeTaux.value = 0
  primeEstPersistant.value = false
  primeModalOpen.value = true
}

const openAbsModal = (contratId) => {
  activeContrat.value = contracts.value.find(c => c.id === contratId)
  activeBulletin.value = bulletinsMap.value[contratId]
  absCode.value = 'CONGES'
  absDateDebut.value = ''
  absDateFin.value = ''
  absNbrHeure.value = 0
  absNbrJour.value = 0
  absModalOpen.value = true
}

const openHsModal = (contratId) => {
  activeContrat.value = contracts.value.find(c => c.id === contratId)
  activeBulletin.value = bulletinsMap.value[contratId]
  hsCode.value = 'HS_15'
  hsNombre.value = 0
  hsModalOpen.value = true
}

const openAcompteModal = (contratId) => {
  const b = bulletinsMap.value[contratId]
  activeContrat.value = contracts.value.find(c => c.id === contratId)
  activeBulletin.value = b
  if (b) {
    const acompteLine = (b.lignes || []).find(l => l.code === 'ACOMPTE')
    acompteMontant.value = acompteLine ? acompteLine.montant_cs : 0
  } else {
    acompteMontant.value = 0
  }
  acompteModalOpen.value = true
}

// Recalculate helper
const handleRecalculateForContrat = async (contratId, acompteVal = 0) => {
  try {
    const payload = {
      contrat_id: contratId,
      mois: Number(selectedMois.value),
      annee: Number(selectedAnnee.value),
      acompte: Number(acompteVal),
      commentaire: "Recalculé suite à modification des variables"
    }
    const res = await post('/bulletins/calculer', payload)
    if (res) {
      toast.add({
        title: 'Bulletin Recalculé',
        description: 'Les modifications ont été prises en compte.',
        color: 'success'
      })
      await fetchDossierData()
    }
  } catch (e) {
    console.error(e)
  }
}

// Modal submits
const handleAddHeureSupp = async () => {
  if (hsNombre.value <= 0) {
    toast.add({ title: 'Validation', description: 'Le nombre d\'heures doit être supérieur à 0.', color: 'warning' })
    return
  }
  try {
    const payload = {
      code: hsCode.value,
      nombre: Number(hsNombre.value),
      mois: Number(selectedMois.value),
      annee: String(selectedAnnee.value)
    }
    await post(`/contrats/${activeContrat.value.id}/heures-supplementaires`, payload)
    hsModalOpen.value = false
    hsNombre.value = 0

    let currentAcompte = 0
    if (activeBulletin.value) {
      const acompteLine = (activeBulletin.value.lignes || []).find(l => l.code === 'ACOMPTE')
      if (acompteLine) currentAcompte = acompteLine.montant_cs || 0
    }
    await handleRecalculateForContrat(activeContrat.value.id, currentAcompte)
  } catch (e) {
    console.error(e)
  }
}

const handleAddAbsence = async () => {
  if (!absDateDebut.value || !absDateFin.value) {
    toast.add({ title: 'Validation', description: 'Les dates de début et de fin sont obligatoires.', color: 'warning' })
    return
  }
  try {
    const payload = {
      code: absCode.value,
      date_debut: new Date(absDateDebut.value).toISOString(),
      date_fin: new Date(absDateFin.value).toISOString(),
      nbr_heure_by_user: Number(absNbrHeure.value),
      nbr_jour_by_user: Number(absNbrJour.value),
      mois: Number(selectedMois.value),
      annee: String(selectedAnnee.value)
    }
    await post(`/contrats/${activeContrat.value.id}/absences`, payload)
    absModalOpen.value = false
    absDateDebut.value = ''
    absDateFin.value = ''
    absNbrHeure.value = 0
    absNbrJour.value = 0

    let currentAcompte = 0
    if (activeBulletin.value) {
      const acompteLine = (activeBulletin.value.lignes || []).find(l => l.code === 'ACOMPTE')
      if (acompteLine) currentAcompte = acompteLine.montant_cs || 0
    }
    await handleRecalculateForContrat(activeContrat.value.id, currentAcompte)
  } catch (e) {
    console.error(e)
  }
}

const handleAddPrime = async () => {
  if (primeMontant.value <= 0) {
    toast.add({ title: 'Validation', description: 'Le montant de la prime doit être supérieur à 0.', color: 'warning' })
    return
  }
  try {
    const payload = {
      code: primeCode.value,
      libelle: primeLibelle.value || primeCode.value,
      montant: Number(primeMontant.value),
      base: primeMode.value === 'calcul' ? (Number(primeBase.value) || null) : null,
      taux: primeMode.value === 'calcul' ? (Number(primeTaux.value) || null) : null,
      mois: Number(selectedMois.value),
      annee: String(selectedAnnee.value),
      est_persistant: primeEstPersistant.value
    }
    await post(`/contrats/${activeContrat.value.id}/primes`, payload)
    primeModalOpen.value = false
    primeLibelle.value = ''
    primeMontant.value = 0
    primeBase.value = 0
    primeTaux.value = 0
    primeEstPersistant.value = false

    let currentAcompte = 0
    if (activeBulletin.value) {
      const acompteLine = (activeBulletin.value.lignes || []).find(l => l.code === 'ACOMPTE')
      if (acompteLine) currentAcompte = acompteLine.montant_cs || 0
    }
    await handleRecalculateForContrat(activeContrat.value.id, currentAcompte)
  } catch (e) {
    console.error(e)
  }
}

const handleSaveAcompte = async () => {
  acompteModalOpen.value = false
  await handleRecalculateForContrat(activeContrat.value.id, acompteMontant.value)
}

onMounted(async () => {
  await fetchDossiers()
  await fetchPlanPaie()
  if (selectedDossierId.value) {
    await fetchDossierData()
  }
})
</script>

<template>
  <div class="space-y-6">

    <!-- Top Action / Title Header -->
    <div class="bg-white border-2 border-slate-200 p-6 shadow-flat flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-t-4 border-t-green-600">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-50 text-green-700 flex items-center justify-center font-bold text-xl border border-green-200">
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
          class="px-4 py-2 border-2 border-slate-200 text-xs font-bold uppercase tracking-wider hover:bg-slate-50 text-slate-700 transition-all flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-flat-hover shadow-flat-active"
        >
          <UIcon name="i-lucide-check-circle-2" class="w-4 h-4 text-green-600" />
          Valider la période
        </button>
        <button
          @click="handleCalculateAll"
          :disabled="loadingData || bulkProcessing || stats.pendingCount === 0"
          class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-xs font-bold uppercase tracking-wider shadow-flat transition-all flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-flat-hover shadow-flat-active"
        >
          <UIcon name="i-lucide-calculator" class="w-4 h-4" />
          Calculer les bulletins
        </button>
      </div>
    </div>

    <!-- Main Filter Bar -->
    <div class="bg-white border-2 border-slate-200 p-4 shadow-flat flex flex-col md:flex-row items-center gap-4">
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
        <div class="bg-white border-2 border-slate-200 p-5 shadow-flat space-y-2 border-t-4 border-t-slate-500">
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
        <div class="bg-white border-2 border-slate-200 p-5 shadow-flat space-y-2 border-t-4 border-t-green-600">
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
        <div class="bg-white border-2 border-slate-200 p-5 shadow-flat space-y-2 border-t-4 border-t-blue-500">
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
        <div class="bg-white border-2 border-slate-200 p-5 shadow-flat space-y-2 border-t-4 border-t-emerald-600">
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

      <!-- Bulk Actions Bar -->
      <div v-if="selectedBulletins.length > 0" class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row justify-between items-center gap-3 text-xs transition-all mb-4">
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

      <!-- Employees & Bulletins List Table Card -->
      <div class="bg-white border-2 border-slate-200 shadow-flat overflow-hidden border-t-4 border-t-slate-500">
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
                <th scope="col" class="px-4 py-3 text-left w-10">
                  <input type="checkbox" v-model="allBulletinsSelected" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </th>
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
                <td class="px-4 py-4" @click.stop>
                  <input type="checkbox" :value="c.id" v-model="selectedBulletins" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </td>

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
                        class="px-2.5 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-none text-xs font-bold transition-colors flex items-center gap-1 uppercase tracking-wider"
                      >
                        <UIcon name="i-lucide-eye" class="w-3.5 h-3.5" />
                        Voir
                      </NuxtLink>

                      <!-- Recalculate (recalculate is just running compute again) -->
                      <button
                        v-if="bulletinsMap[c.id].statut !== 'valide'"
                        @click="handleCalculateSingle(c.id)"
                        class="px-2.5 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-750 transition-colors rounded-none text-xs font-bold flex items-center gap-1 uppercase tracking-wider cursor-pointer"
                        title="Recalculer le bulletin"
                      >
                        <UIcon name="i-lucide-refresh-cw" class="w-3.5 h-3.5 text-green-600" />
                        Recalculer
                      </button>

                      <!-- Validate (if draft) -->
                      <button
                        v-if="bulletinsMap[c.id].statut !== 'valide'"
                        @click="handleValidateSingle(bulletinsMap[c.id].id)"
                        class="px-2.5 py-1.5 border border-yellow-250 bg-yellow-50 hover:bg-yellow-100 text-yellow-750 transition-colors rounded-none text-xs font-bold flex items-center gap-1 uppercase tracking-wider cursor-pointer"
                        title="Valider définitivement"
                      >
                        <UIcon name="i-lucide-check-circle" class="w-3.5 h-3.5 text-yellow-600" />
                        Valider
                      </button>

                      <!-- Dropdown quick entries -->
                      <UDropdownMenu
                        v-if="bulletinsMap[c.id].statut !== 'valide'"
                        :items="[[
                          {
                            label: 'Ajouter une prime',
                            icon: 'i-lucide-gift',
                            onSelect: () => openPrimeModal(c.id)
                          },
                          {
                            label: 'Déclarer une absence',
                            icon: 'i-lucide-calendar-x',
                            onSelect: () => openAbsModal(c.id)
                          },
                          {
                            label: 'Ajouter des heures sup',
                            icon: 'i-lucide-clock',
                            onSelect: () => openHsModal(c.id)
                          },
                          {
                            label: 'Saisir un acompte',
                            icon: 'i-lucide-banknote',
                            onSelect: () => openAcompteModal(c.id)
                          }
                        ]]"
                      >
                        <button
                          class="px-2.5 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-none text-xs font-bold transition-colors flex items-center gap-1 uppercase tracking-wider cursor-pointer"
                        >
                          Saisies
                          <UIcon name="i-lucide-chevron-down" class="w-3.5 h-3.5" />
                        </button>
                      </UDropdownMenu>

                      <!-- Delete (if draft) -->
                      <button
                        v-if="bulletinsMap[c.id].statut !== 'valide'"
                        @click="handleDeleteSingle(bulletinsMap[c.id].id)"
                        class="px-2.5 py-1.5 border border-red-200 bg-red-50 hover:bg-red-100 text-red-650 transition-colors rounded-none cursor-pointer flex items-center justify-center"
                        title="Supprimer"
                      >
                        <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
                      </button>

                    </template>

                    <!-- If not generated yet -->
                    <button
                      v-else
                      @click="handleCalculateSingle(c.id)"
                      class="px-2.5 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-none text-xs font-bold transition-colors flex items-center gap-1 shadow-flat uppercase tracking-wider cursor-pointer"
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

    <!-- Modals for adding variables -->

    <!-- Modal: Overtime -->
    <UModal v-model:open="hsModalOpen" title="Saisir des Heures Supplémentaires">
      <template #content>
        <div class="p-6 space-y-4 bg-white border border-slate-200">
          <h2 class="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Nouvelle Heure Supp.</h2>

          <div class="space-y-4">
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Taux de majoration</label>
              <select v-model="hsCode" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white select">
                <option value="HS_15">Majoration à 15%</option>
                <option value="HS_25">Majoration à 25%</option>
                <option value="HS_50">Majoration à 50%</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Nombre d'heures</label>
              <input v-model="hsNombre" type="number" step="0.5" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button type="button" @click="hsModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-none hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
              Annuler
            </button>
            <button type="button" @click="handleAddHeureSupp" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-none shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
              Enregistrer et Recalculer
            </button>
          </div>
        </div>
      </template>
    </UModal>

    <!-- Modal: Absence -->
    <UModal v-model:open="absModalOpen" title="Saisir une Absence / Congé">
      <template #content>
        <div class="p-6 space-y-4 bg-white border border-slate-200">
          <h2 class="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Saisir Absence</h2>

          <div class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Motif de l'absence</label>
                <select v-model="absCode" class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-none text-sm bg-white select">
                  <option value="CONGES">Congés payés</option>
                  <option value="MALADIE">Maladie</option>
                  <option value="AT">Accident du travail</option>
                  <option value="SANS_SOLDE">Absence non autorisée (Sans solde)</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Nbr jours d'absence</label>
                <input v-model="absNbrJour" type="number" step="0.5" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Date début</label>
                <input v-model="absDateDebut" type="date" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Date fin</label>
                <input v-model="absDateFin" type="date" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
              </div>
            </div>

            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Nombre d'heures correspondantes (Si contrat horaire)</label>
              <input v-model="absNbrHeure" type="number" step="1" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button type="button" @click="absModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-none hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
              Annuler
            </button>
            <button type="button" @click="handleAddAbsence" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-none shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
              Enregistrer et Recalculer
            </button>
          </div>
        </div>
      </template>
    </UModal>

    <!-- Modal: Prime -->
    <UModal v-model:open="primeModalOpen" title="Saisir une Prime">
      <template #content>
        <div class="p-6 space-y-4 bg-white border border-slate-200">
          <h2 class="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Nouvelle Prime</h2>

          <div class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Code Identifiant</label>
                <select v-model="primeCode" class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-none text-sm bg-white select">
                  <option v-for="p in primesDisponibles" :key="p.code" :value="p.code">
                    {{ p.libelle }} ({{ p.code }})
                  </option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Mode de saisie</label>
                <select v-model="primeMode" class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-none text-sm bg-white select">
                  <option value="direct">Montant Direct</option>
                  <option value="calcul">Calcul par Base et Taux</option>
                </select>
              </div>
            </div>

            <div v-if="primeMode === 'calcul'" class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Base (FCFA)</label>
                <input v-model="primeBase" type="number" @input="primeMontant = (Number(primeBase) || 0) * ((Number(primeTaux) || 0) / 100)" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Taux (%)</label>
                <input v-model="primeTaux" type="number" step="0.01" @input="primeMontant = (Number(primeBase) || 0) * ((Number(primeTaux) || 0) / 100)" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Montant de la prime (FCFA)</label>
                <input v-model="primeMontant" type="number" :disabled="primeMode === 'calcul'" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white disabled:bg-slate-100" />
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Libellé (Affiché sur le bulletin)</label>
                <input v-model="primeLibelle" type="text" placeholder="Ex: Prime de rendement" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
              </div>
            </div>
            <div class="flex items-center space-x-2 pt-2">
              <input v-model="primeEstPersistant" type="checkbox" id="prime_est_persistant" class="w-4 h-4 text-green-600 focus:ring-green-500 border-slate-300 rounded" />
              <label for="prime_est_persistant" class="text-xs font-semibold uppercase tracking-wider text-slate-500 cursor-pointer">
                Répéter les mois suivants (Persistant)
              </label>
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button type="button" @click="primeModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-none hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
              Annuler
            </button>
            <button type="button" @click="handleAddPrime" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-none shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
              Enregistrer et Recalculer
            </button>
          </div>
        </div>
      </template>
    </UModal>

    <!-- Modal: Acompte -->
    <UModal v-model:open="acompteModalOpen" title="Définir un Acompte">
      <template #content>
        <div class="p-6 space-y-4 bg-white border border-slate-200">
          <h2 class="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Acompte sur salaire</h2>

          <div class="space-y-4">
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Montant de l'acompte (FCFA)</label>
              <input v-model="acompteMontant" type="number" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
              <p class="text-[10px] text-slate-500 mt-1">Sera déduit directement du salaire net à payer.</p>
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button type="button" @click="acompteModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-none hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
              Annuler
            </button>
            <button type="button" @click="handleSaveAcompte" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-none shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
              Enregistrer et Recalculer
            </button>
          </div>
        </div>
      </template>
    </UModal>

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
