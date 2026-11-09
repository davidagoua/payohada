<script setup>
/**
 * Onglet « Bulletins » d'un établissement : calcul, validation, envoi et
 * saisie des variables (heures supplémentaires, absences, primes, acompte)
 * pour la période choisie.
 */
const props = defineProps({
  dossierId: { type: [String, Number], required: true },
  etabId: { type: [String, Number], required: true },
  contracts: { type: Array, required: true },
  salaries: { type: Array, required: true }
})
const { contracts, salaries } = toRefs(props)
const dossierId = props.dossierId
const etabId = props.etabId

const { get, put, post, delete: apiDelete } = useApi()
const toast = useToast()

const rechercheBulletin = ref('')

const contratsBulletinsFiltres = computed(() => {
  const terme = normaliserRecherche(rechercheBulletin.value).trim()
  if (!terme) return contracts.value
  return contracts.value.filter((contrat) =>
    [getSalarieName(contrat.salarie_id), contrat.matricule_salarie, contrat.numero_contrat]
      .some((valeur) => normaliserRecherche(valeur).includes(terme))
  )
})
const selectedBulletins = ref([])

const allBulletinsSelected = computed({
  get: () => contratsBulletinsFiltres.value.length > 0
    && contratsBulletinsFiltres.value.every((contrat) => selectedBulletins.value.includes(contrat.id)),
  set: (val) => {
    if (val) {
      selectedBulletins.value = [...new Set([...selectedBulletins.value, ...contratsBulletinsFiltres.value.map(c => c.id)])]
    } else {
      const ids = new Set(contratsBulletinsFiltres.value.map(c => c.id))
      selectedBulletins.value = selectedBulletins.value.filter(id => !ids.has(id))
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
  await fetchBulletins()
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
  await fetchBulletins()
}

const handleDeleteSelectedBulletins = async () => {
  const drafts = selectedBulletins.value
    .map(cId => bulletinsMap.value[cId])
    .filter(b => b && b.statut !== 'valide')

  if (drafts.length === 0) {
    toast.add({
      title: 'Info',
      description: 'Aucun bulletin en brouillon sélectionné à supprimer.',
      color: 'warning'
    })
    return
  }

  if (!confirm(`Supprimer définitivement les ${drafts.length} bulletin(s) sélectionnés ?`)) return

  bulkProcessing.value = true
  bulkProgress.value = 0
  bulkTotal.value = drafts.length

  let successCount = 0
  for (let i = 0; i < drafts.length; i++) {
    const b = drafts[i]
    try {
      await apiDelete(`/bulletins/${b.id}`)
      successCount++
    } catch (e) {
      console.error(`Error deleting bulletin ${b.id}:`, e)
    }
    bulkProgress.value = i + 1
  }

  bulkProcessing.value = false
  toast.add({
    title: 'Suppression terminée',
    description: `${successCount} bulletin(s) de salaire supprimé(s).`,
    color: 'success'
  })
  selectedBulletins.value = []
  await fetchBulletins()
}

const handlePrintSelected = () => {
  const ids = selectedBulletins.value.map(cId => bulletinsMap.value[cId]?.id).filter(Boolean)
  if (ids.length === 0) {
    toast.add({ title: 'Info', description: 'Aucun bulletin généré dans la sélection.', color: 'warning' })
    return
  }
  window.open(`/dossiers/${dossierId}/etablissements/${etabId}/print-bulletins?ids=${ids.join(',')}`, '_blank')
}

const handleSendEmployeeEmailsSelected = async () => {
  const generated = selectedBulletins.value
    .map(cId => bulletinsMap.value[cId])
    .filter(b => b && b.id)

  if (generated.length === 0) {
    toast.add({ title: 'Info', description: 'Aucun bulletin généré dans la sélection.', color: 'warning' })
    return
  }

  if (!confirm(`Envoyer par email les ${generated.length} bulletin(s) sélectionnés aux employés ?`)) return

  bulkProcessing.value = true
  bulkProgress.value = 0
  bulkTotal.value = generated.length

  let successCount = 0
  let errorMessages = []

  for (let i = 0; i < generated.length; i++) {
    const b = generated[i]
    try {
      await post(`/bulletins/${b.id}/envoyer-employe`)
      successCount++
    } catch (e) {
      console.error(`Error sending email to employee for bulletin ${b.id}:`, e)
      const errorMsg = e.response?._data?.detail || e.message || String(e)
      errorMessages.push(`${getSalarieName(b.contrat_id)}: ${errorMsg}`)
    }
    bulkProgress.value = i + 1
  }

  bulkProcessing.value = false
  toast.add({
    title: 'Envoi d\'emails aux employés terminé',
    description: `${successCount} email(s) envoyé(s) avec succès.`,
    color: successCount === generated.length ? 'success' : 'warning'
  })

  if (errorMessages.length > 0) {
    toast.add({
      title: 'Certains emails n\'ont pas pu être envoyés',
      description: errorMessages.slice(0, 3).join('\n'),
      color: 'danger'
    })
  }

  selectedBulletins.value = []
}

const handleSendManagerEmailsSelected = async () => {
  const generated = selectedBulletins.value
    .map(cId => bulletinsMap.value[cId])
    .filter(b => b && b.id)

  if (generated.length === 0) {
    toast.add({ title: 'Info', description: 'Aucun bulletin généré dans la sélection.', color: 'warning' })
    return
  }

  if (!confirm(`Envoyer par email les ${generated.length} bulletin(s) sélectionnés au gestionnaire de l'entreprise ?`)) return

  bulkProcessing.value = true
  bulkProgress.value = 0
  bulkTotal.value = generated.length

  let successCount = 0
  for (let i = 0; i < generated.length; i++) {
    const b = generated[i]
    try {
      await post(`/bulletins/${b.id}/envoyer-gestionnaire`)
      successCount++
    } catch (e) {
      console.error(`Error sending email to manager for bulletin ${b.id}:`, e)
    }
    bulkProgress.value = i + 1
  }

  bulkProcessing.value = false
  toast.add({
    title: 'Envoi d\'emails au gestionnaire terminé',
    description: `${successCount} email(s) envoyé(s) au gestionnaire avec succès.`,
    color: 'success'
  })
  selectedBulletins.value = []
}

const bulletinsMap = ref({})

// Period filter state for bulletins
const selectedMois = ref(new Date().getMonth() + 1)
const selectedAnnee = ref(new Date().getFullYear())

// Bulk processing states for bulletins
const bulkProcessing = ref(false)
const bulkProgress = ref(0)
const bulkTotal = ref(0)

const fetchBulletins = async () => {
  try {
    const bList = await get(`/dossiers/${dossierId}/bulletins`, {
      query: {
        mois: selectedMois.value,
        annee: selectedAnnee.value
      }
    })
    const map = {}
    if (bList) {
      bList.forEach(b => {
        map[b.contrat_id] = b
      })
    }
    bulletinsMap.value = map
  } catch (e) {
    console.error("Error loading bulletins:", e)
  }
}

const getSalarieName = (salarieId) => {
  const s = salaries.value.find(emp => emp.id === salarieId)
  return s ? `${s.nom.toUpperCase()} ${s.prenom}` : 'Inconnu'
}

const handleCalculateSingle = async (contratId) => {
  try {
    const payload = {
      contrat_id: contratId,
      mois: Number(selectedMois.value),
      annee: Number(selectedAnnee.value),
      acompte: 0.0,
      commentaire: "Généré depuis la gestion des bulletins de l'établissement"
    }
    const res = await post('/bulletins/calculer', payload)
    if (res) {
      toast.add({
        title: 'Bulletin calculé',
        description: `Le bulletin a été généré avec succès.`,
        color: 'success'
      })
      await fetchBulletins()
    }
  } catch (e) {
    console.error(e)
  }
}

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
      await fetchBulletins()
    }
  } catch (e) {
    console.error(e)
  }
}

const handleDeleteSingle = async (bulletinId) => {
  if (!confirm('Supprimer définitivement ce bulletin de paie ?')) return
  try {
    await apiDelete(`/bulletins/${bulletinId}`)
    toast.add({
      title: 'Bulletin Supprimé',
      description: 'Le bulletin de salaire a été supprimé.',
      color: 'success'
    })
    await fetchBulletins()
  } catch (e) {
    console.error(e)
  }
}

const handleCalculateAll = async () => {
  const pending = contracts.value.filter(c => !bulletinsMap.value[c.id])
  if (pending.length === 0) {
    toast.add({
      title: 'Info',
      description: 'Tous les bulletins de cet établissement sont déjà générés pour cette période.',
      color: 'warning'
    })
    return
  }

  if (!confirm(`Générer les bulletins de paie pour les ${pending.length} salarié(s) en attente dans cet établissement ?`)) return

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
  await fetchBulletins()
}

const handleValidateAll = async () => {
  const drafts = Object.values(bulletinsMap.value).filter(b => {
    return contracts.value.some(c => c.id === b.contrat_id) && b.statut !== 'valide'
  })
  if (drafts.length === 0) {
    toast.add({
      title: 'Info',
      description: 'Aucun bulletin en brouillon à valider pour cet établissement.',
      color: 'warning'
    })
    return
  }

  if (!confirm(`Valider définitivement les ${drafts.length} bulletin(s) en brouillon dans cet établissement ?`)) return

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
  await fetchBulletins()
}

const stats = computed(() => {
  const generatedBulletins = Object.values(bulletinsMap.value).filter(b => {
    return contracts.value.some(c => c.id === b.contrat_id)
  })
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

watch([selectedMois, selectedAnnee], async () => {
  await fetchBulletins()
})

// Saisie des variables (heures sup., absences, primes, acompte)
const modalesVariables = ref(null)

onMounted(async () => {
  await fetchBulletins()
})
</script>

<template>
  <div class="space-y-6">
      <!-- Title & Mass Actions Header -->


      <!-- Period Filter Bar -->
      <div class="bg-white border-2 border-slate-200 p-4 shadow-flat flex flex-col md:flex-row justify-between items-center gap-4">
        <div class="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
          <span class="text-xs font-bold uppercase tracking-wider text-slate-400 shrink-0">Période de Paie :</span>
          <div class="flex space-x-3 w-full sm:w-auto">
            <select v-model="selectedMois" class="block w-full sm:w-40 px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white select">
              <option v-for="m in 12" :key="m" :value="m">{{ getPeriodLabel(m, 2026).split(' ')[0] }}</option>
            </select>
            <input
              v-model="selectedAnnee"
              type="number"
              placeholder="Année"
              class="block w-full sm:w-28 px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white"
            />
          </div>
        </div>
        <div v-if="contracts.length > 0" class="flex flex-wrap gap-3 w-full md:w-auto justify-end">
          <button
            @click="handleValidateAll"
            :disabled="bulkProcessing || stats.generatedCount === 0"
            class="px-4 py-2 border-2 border-slate-200 text-xs font-bold uppercase tracking-wider hover:bg-slate-50 text-slate-700 transition-all flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-flat-hover shadow-flat-active"
          >
            <UIcon name="i-lucide-check-circle-2" class="w-4 h-4 text-green-600" />
            Valider la période
          </button>
          <button
            @click="handleCalculateAll"
            :disabled="bulkProcessing || stats.pendingCount === 0"
            class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-xs font-bold uppercase tracking-wider shadow-flat transition-all flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-flat-hover shadow-flat-active"
          >
            <UIcon name="i-lucide-calculator" class="w-4 h-4" />
            Calculer les bulletins
          </button>
        </div>
      </div>

      <!-- Bulk action progress -->
      <div v-if="bulkProcessing" class="bg-white border-2 border-slate-200 p-4 shadow-flat space-y-2">
        <div class="flex justify-between text-xs font-semibold text-slate-700">
          <span>Traitement groupé des fiches de paye de l'établissement...</span>
          <span>{{ bulkProgress }} / {{ bulkTotal }} ({{ Math.round((bulkProgress / bulkTotal) * 100) }}%)</span>
        </div>
        <div class="w-full bg-slate-100 h-2 overflow-hidden">
          <div class="bg-green-600 h-full transition-all duration-300" :style="{ width: `${(bulkProgress / bulkTotal) * 100}%` }"></div>
        </div>
      </div>

      <!-- Statistics cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-white border-2 border-slate-200 p-5 shadow-flat space-y-2 border-t-4 border-t-navy-900">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Effectif Établissement</span>
            <div class="w-7 h-7 bg-navy-50 text-navy-700 rounded-lg flex items-center justify-center">
              <UIcon name="i-lucide-users" class="w-4 h-4" />
            </div>
          </div>
          <p class="text-2xl font-bold text-navy-900">{{ stats.totalEmployees }} salariés</p>
          <div class="text-[10px] text-slate-450 font-sans">Avec contrat actif rattaché</div>
        </div>

        <div class="bg-white border-2 border-slate-200 p-5 shadow-flat space-y-2 border-t-4 border-t-green-600">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Bulletins Calculés</span>
            <div class="w-7 h-7 bg-green-50 text-green-700 rounded-lg flex items-center justify-center">
              <UIcon name="i-lucide-check-circle-2" class="w-4 h-4" />
            </div>
          </div>
          <p class="text-2xl font-bold text-navy-900">{{ stats.generatedCount }} / {{ stats.totalEmployees }}</p>
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

        <div class="bg-white border-2 border-slate-200 p-5 shadow-flat space-y-2 border-t-4 border-t-navy-900">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Masse Brut</span>
            <div class="w-7 h-7 bg-navy-50 text-navy-700 rounded-lg flex items-center justify-center">
              <UIcon name="i-lucide-coins" class="w-4 h-4" />
            </div>
          </div>
          <p class="text-2xl font-bold text-navy-900 font-mono tracking-tight">{{ formatXOF(stats.masseBrut) }}</p>
          <div class="text-[10px] text-slate-450 font-sans">Brut total sur la période</div>
        </div>

        <div class="bg-white border-2 border-slate-200 p-5 shadow-flat space-y-2 border-t-4 border-t-green-600">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Masse Nette</span>
            <div class="w-7 h-7 bg-green-50 text-green-700 rounded-lg flex items-center justify-center">
              <UIcon name="i-lucide-banknote" class="w-4 h-4" />
            </div>
          </div>
          <p class="text-2xl font-bold text-green-700 font-mono tracking-tight">{{ formatXOF(stats.masseNet) }}</p>
          <div class="text-[10px] text-slate-450 font-sans">Net total sur la période</div>
        </div>
      </div>

      <!-- Bulk Actions Bar for Bulletins -->
      <div v-if="selectedBulletins.length > 0" class="bg-slate-100 border border-slate-350 p-4 flex flex-col sm:flex-row justify-between items-center gap-3 text-xs transition-all mb-4">
        <div class="font-bold text-slate-700">
          {{ selectedBulletins.length }} bulletin(s) sélectionné(s)
        </div>
        <div class="flex flex-wrap gap-2 justify-end w-full sm:w-auto">
          <button
            @click="handleCalculateSelected"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-bold uppercase tracking-wider transition-colors shadow-flat cursor-pointer"
          >
            <UIcon name="i-lucide-calculator" class="w-3.5 h-3.5 inline mr-1" />
            Calculer
          </button>
          <UDropdownMenu :items="modalesVariables?.menuSaisieGroupee(selectedBulletins) ?? []">
            <button
              class="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-bold uppercase tracking-wider transition-colors shadow-flat cursor-pointer"
            >
              <UIcon name="i-lucide-list-plus" class="w-3.5 h-3.5 inline mr-1" />
              Ajouter des variables
              <UIcon name="i-lucide-chevron-down" class="w-3.5 h-3.5 inline ml-1" />
            </button>
          </UDropdownMenu>
          <button
            @click="handleValidateSelected"
            class="px-3 py-1.5 bg-yellow-500 hover:bg-yellow-600 text-slate-900 font-bold uppercase tracking-wider transition-colors shadow-flat cursor-pointer"
          >
            <UIcon name="i-lucide-check-circle" class="w-3.5 h-3.5 inline mr-1" />
            Valider
          </button>
          <button
            @click="handlePrintSelected"
            class="px-3 py-1.5 bg-navy-800 hover:bg-navy-700 text-white font-bold uppercase tracking-wider transition-colors shadow-flat cursor-pointer"
          >
            <UIcon name="i-lucide-printer" class="w-3.5 h-3.5 inline mr-1" />
            Imprimer
          </button>
          <button
            @click="handleSendEmployeeEmailsSelected"
            class="px-3 py-1.5 bg-navy-800 hover:bg-navy-700 text-white font-bold uppercase tracking-wider transition-colors shadow-flat cursor-pointer"
          >
            <UIcon name="i-lucide-mail" class="w-3.5 h-3.5 inline mr-1" />
            Mail Employé
          </button>
          <button
            @click="handleSendManagerEmailsSelected"
            class="px-3 py-1.5 bg-navy-800 hover:bg-navy-700 text-white font-bold uppercase tracking-wider transition-colors shadow-flat cursor-pointer"
          >
            <UIcon name="i-lucide-mail" class="w-3.5 h-3.5 inline mr-1" />
            Mail Gestionnaire
          </button>
          <button
            @click="handleDeleteSelectedBulletins"
            class="p-1.5 bg-red-650 hover:bg-red-755 text-white transition-colors shadow-flat cursor-pointer flex items-center justify-center"
            title="Supprimer"
          >
            <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Bulletins Table Card -->
      <div class="bg-white border-2 border-slate-200 shadow-flat overflow-hidden border-t-4 border-t-navy-900">
        <!-- Recherche : sous les statistiques, juste au-dessus de l'en-tête du tableau -->
        <div v-if="contracts.length > 0" class="px-5 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div class="relative w-full sm:w-96">
            <UIcon name="i-lucide-search" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input
              v-model="rechercheBulletin"
              type="search"
              placeholder="Rechercher un salarié par nom ou matricule…"
              class="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          <span class="text-xs text-slate-500 whitespace-nowrap">
            {{ contratsBulletinsFiltres.length }} / {{ contracts.length }} salarié(s)
          </span>
        </div>

        <div v-if="contracts.length === 0" class="text-center py-16 px-4 bg-white space-y-3">
          <div class="w-10 h-10 bg-slate-100 text-slate-400 rounded-lg flex items-center justify-center mx-auto">
            <UIcon name="i-lucide-user-x" class="w-5 h-5" />
          </div>
          <h4 class="font-bold text-navy-900">Aucun salarié avec contrat actif</h4>
          <p class="text-xs text-slate-500 max-w-sm mx-auto">
            Pour générer des bulletins de paie, vous devez d'abord associer des salariés avec des contrats de travail actifs dans cet établissement.
          </p>
        </div>

        <div v-else-if="contratsBulletinsFiltres.length === 0" class="text-center py-16 px-4 bg-white space-y-2">
          <UIcon name="i-lucide-search-x" class="w-6 h-6 text-slate-400 mx-auto" />
          <h4 class="font-bold text-navy-900">Aucun salarié ne correspond à la recherche</h4>
          <p class="text-xs text-slate-500">Recherche : « {{ rechercheBulletin }} »</p>
        </div>

        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left w-10">
                  <input type="checkbox" v-model="allBulletinsSelected" class="rounded-lg border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </th>
                <th scope="col" class="px-6 py-3 text-left">Employé</th>
                <th scope="col" class="px-6 py-3 text-left">Statut Bulletin</th>
                <th scope="col" class="px-6 py-3 text-right">Salaire Brut</th>
                <th scope="col" class="px-6 py-3 text-right">Net à Payer</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="c in contratsBulletinsFiltres" :key="c.id" class="hover:bg-slate-50/50 transition-colors">
                <td class="px-4 py-4" @click.stop>
                  <input type="checkbox" :value="c.id" v-model="selectedBulletins" class="rounded-lg border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </td>
                <!-- Employee -->
                <td class="px-6 py-4">
                  <div class="flex items-center space-x-3">
                    <div class="w-8 h-8 bg-navy-50 text-navy-700 rounded-lg flex items-center justify-center font-bold text-xs border border-navy-200">
                      {{ c.matricule_salarie.substring(c.matricule_salarie.lastIndexOf('-') + 1) || 'EMP' }}
                    </div>
                    <div>
                      <span class="block font-bold text-slate-900 leading-tight">
                        {{ getSalarieName(c.salarie_id) }}
                      </span>
                      <span class="text-xs text-slate-500 font-mono">
                        {{ c.matricule_salarie }}
                      </span>
                    </div>
                  </div>
                </td>



                <!-- Status -->
                <td class="px-6 py-4">
                  <span
                    v-if="bulletinsMap[c.id]"
                    :class="[
                      bulletinsMap[c.id].statut === 'valide'
                        ? 'bg-green-50 text-green-700 border-green-200'
                        : 'bg-yellow-50 text-yellow-700 border-yellow-200',
                      'px-2.5 py-0.5 rounded-lg text-[10px] uppercase font-bold border inline-block tracking-wider'
                    ]"
                  >
                    {{ bulletinsMap[c.id].statut }}
                  </span>
                  <span
                    v-else
                    class="bg-slate-100 text-slate-400 border-slate-200 px-2.5 py-0.5 rounded-lg text-[10px] uppercase font-bold border inline-block tracking-wider"
                  >
                    Non calculé
                  </span>
                </td>



                <!-- Salaire Brut -->
                <td class="px-6 py-4 text-right font-mono text-slate-650 font-medium">
                  {{ bulletinsMap[c.id] ? formatXOF(bulletinsMap[c.id].salaire_brut) : '-' }}
                </td>

                <!-- Net à payer -->
                <td class="px-6 py-4 text-right font-mono font-bold text-slate-900">
                  {{ bulletinsMap[c.id] ? formatXOF(bulletinsMap[c.id].net_a_payer) : '-' }}
                </td>

                <!-- Actions -->
                <td class="px-6 py-4 text-right">
                  <div class="flex justify-end items-center space-x-2">
                    <template v-if="bulletinsMap[c.id]">
                      <!-- View Link -->
                      <NuxtLink
                        :to="`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${c.salarie_id}/contrats/${c.id}/bulletins/${bulletinsMap[c.id].id}`"
                        class="px-2.5 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-bold transition-colors flex items-center gap-1 uppercase tracking-wider"
                      >
                        <UIcon name="i-lucide-eye" class="w-3.5 h-3.5" />
                        Voir
                      </NuxtLink>

                      <!-- Recalculate -->
                      <button
                        v-if="bulletinsMap[c.id].statut !== 'valide'"
                        @click="handleCalculateSingle(c.id)"
                        class="px-2.5 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 transition-colors rounded-lg text-xs font-bold flex items-center gap-1 uppercase tracking-wider cursor-pointer"
                        title="Recalculer le bulletin"
                      >
                        <UIcon name="i-lucide-refresh-cw" class="w-3.5 h-3.5 text-green-600" />
                        Recalculer
                      </button>

                      <!-- Validate -->
                      <button
                        v-if="bulletinsMap[c.id].statut !== 'valide'"
                        @click="handleValidateSingle(bulletinsMap[c.id].id)"
                        class="px-2.5 py-1.5 border border-yellow-250 bg-yellow-50 hover:bg-yellow-100 text-yellow-750 transition-colors rounded-lg text-xs font-bold flex items-center gap-1 uppercase tracking-wider cursor-pointer"
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
                            onSelect: () => modalesVariables?.openPrimeModal(c.id)
                          },
                          {
                            label: 'Déclarer une absence',
                            icon: 'i-lucide-calendar-x',
                            onSelect: () => modalesVariables?.openAbsModal(c.id)
                          },
                          {
                            label: 'Ajouter des heures sup',
                            icon: 'i-lucide-clock',
                            onSelect: () => modalesVariables?.openHsModal(c.id)
                          },
                          {
                            label: 'Saisir un acompte',
                            icon: 'i-lucide-banknote',
                            onSelect: () => modalesVariables?.openAcompteModal(c.id)
                          }
                        ]]"
                      >
                        <button
                          class="px-2.5 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-bold transition-colors flex items-center gap-1 uppercase tracking-wider cursor-pointer"
                        >
                          Saisies
                          <UIcon name="i-lucide-chevron-down" class="w-3.5 h-3.5" />
                        </button>
                      </UDropdownMenu>

                      <!-- Delete -->
                      <button
                        v-if="bulletinsMap[c.id].statut !== 'valide'"
                        @click="handleDeleteSingle(bulletinsMap[c.id].id)"
                        class="px-2.5 py-1.5 border border-red-200 bg-red-50 hover:bg-red-100 text-red-650 transition-colors rounded-lg cursor-pointer flex items-center justify-center"
                        title="Supprimer"
                      >
                        <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
                      </button>
                    </template>

                    <button
                      v-else
                      @click="handleCalculateSingle(c.id)"
                      class="px-2.5 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-bold transition-colors flex items-center gap-1 shadow-flat uppercase tracking-wider cursor-pointer"
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

    <BulletinVariablesModales
      ref="modalesVariables"
      :bulletins-map="bulletinsMap"
      :mois="selectedMois"
      :annee="selectedAnnee"
      @recalcule="fetchBulletins"
    />
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
