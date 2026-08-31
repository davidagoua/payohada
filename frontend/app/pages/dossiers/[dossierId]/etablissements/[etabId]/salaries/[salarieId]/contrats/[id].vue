<script setup>
const route = useRoute()
const router = useRouter()
const { get, put, delete: apiDelete, extractFieldErrors } = useApi()
const toast = useToast()
const fieldErrors = ref({})

const dossierId = route.params.dossierId
const etabId = route.params.etabId
const salarieId = route.params.salarieId
const contratId = route.params.id

const contrat = ref(null)
const loading = ref(true)

// Global State for breadcrumbs
const currentDossier = useState('current-dossier')

// Editable fields (supported by ContratUpdate schema)
const editEmploi = ref('')
const editTypeContrat = ref(10)
const editSalaireMensuel = ref(0.0)
const editSalaireHoraire = ref(0.0)
const editTypeSalaire = ref('Mensuel')
const editModeCalcul = ref('brut')
const editStatut = ref('actif')
const editUniteTemps = ref('Heures')
const editSursalaire = ref(0.0)
const editIndemniteTransport = ref(0.0)
const editDotationTelephonique = ref(0.0)

// Departure & STC State
const departSalarie = ref(null)
const soldeToutCompte = ref(null)
const showDepartModal = ref(false)

const departDateSortie = ref('')
const departMotifSortie = ref(10)
const departDernierJourTravaille = ref('')
const departMaintienAffiliation = ref(false)
const departCommentaire = ref('')

const editIndemniteLicenciement = ref(0.0)
const editIndemniteCongesPayes = ref(0.0)
const editIndemnitePreavis = ref(0.0)
const editIndemniteAutre = ref(0.0)
const editStcCommentaire = ref('')
const savingStc = ref(false)

const totalStc = computed(() => {
  return (Number(editIndemniteCongesPayes.value) || 0) +
         (Number(editIndemniteLicenciement.value) || 0) +
         (Number(editIndemnitePreavis.value) || 0) +
         (Number(editIndemniteAutre.value) || 0)
})

const currentEtab = ref(null)
const postes = ref([])
const editPosteSalaireId = ref(null)

const fetchPostes = async () => {
  try {
    const etabData = await get(`/etablissements/${etabId}`)
    currentEtab.value = etabData
    if (etabData.secteur_id) {
      const sectorPostes = await get(`/secteurs/${etabData.secteur_id}/postes`)
      if (sectorPostes && sectorPostes.length > 0) {
        postes.value = sectorPostes
        return
      }
    }
    // Fallback if no sector or sector has no predefined postes in grid
    postes.value = await get('/postes-salaires') || []
  } catch (e) {
    console.error("Error loading postes:", e)
  }
}

watch(editPosteSalaireId, (newId) => {
  if (!newId) return
  const match = postes.value.find(p => p.id === Number(newId))
  if (match) {
    editEmploi.value = `${match.categorie_professionnelle} - ${match.echelon_categorie}`
    updateSursalaire()
  }
})

const updateSursalaire = () => {
  if (!editPosteSalaireId.value) return
  const match = postes.value.find(p => p.id === Number(editPosteSalaireId.value))
  if (match) {
    if (editTypeSalaire.value === 'Mensuel') {
      const baseSalary = match.salaire_mensuel_fcfa || 0
      editSursalaire.value = Math.max(0, Number(editSalaireMensuel.value || 0) - baseSalary)
    } else {
      const baseSalary = Number(match.taux_horaire_fcfa || 0)
      editSursalaire.value = Math.max(0, Number(editSalaireHoraire.value || 0) - baseSalary)
    }
  }
}

watch([editSalaireMensuel, editSalaireHoraire, editTypeSalaire], () => {
  updateSursalaire()
})

// Bulletins list & modal
const bulletins = ref([])
const showModal = ref(false)
const calcMois = ref(new Date().getMonth() + 1)
const calcAnnee = ref(new Date().getFullYear())
const calcAcompte = ref(0.0)
const calcCommentaire = ref('')
const calcLoading = ref(false)

const fetchContratDetails = async () => {
  loading.value = true
  try {
    // Ensure parent dossier context is loaded
    if (!currentDossier.value) {
      const parentDossier = await get(`/dossiers/${dossierId}`)
      currentDossier.value = parentDossier
    }

    const data = await get(`/contrats/${contratId}`)
    contrat.value = data

    // Fetch postes first so that they are available when editPosteSalaireId is populated
    await fetchPostes()

    // Populate Editable Fields
    editEmploi.value = data.emploi || ''
    editTypeContrat.value = data.type_contrat_travail || 10
    editSalaireMensuel.value = data.salaire_mensuel || 0.0
    editSalaireHoraire.value = data.salaire_horaire || 0.0
    editTypeSalaire.value = data.type_salaire || 'Mensuel'
    editModeCalcul.value = data.mode_calcul || 'brut'
    editPosteSalaireId.value = data.poste_salaire_id || null
    editStatut.value = data.statut || 'actif'
    editUniteTemps.value = data.unite_temps || 'Heures'
    editSursalaire.value = data.sursalaire || 0.0
    editIndemniteTransport.value = data.indemnite_transport || 0.0
    editDotationTelephonique.value = data.dotation_telephonique || 0.0

    // Fetch bulletins
    const bList = await get(`/dossiers/${dossierId}/bulletins`, { query: { contrat_id: contratId } })
    bulletins.value = bList || []

    // Fetch departure info
    await fetchDepartInfo()

  } catch (e) {
    console.error(e)
    router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}`)
  } finally {
    loading.value = false
  }
}

const handleUpdateContrat = async () => {
  fieldErrors.value = {}
  try {
    const payload = {
      emploi: editEmploi.value || null,
      poste_salaire_id: editPosteSalaireId.value ? Number(editPosteSalaireId.value) : null,
      type_contrat_travail: Number(editTypeContrat.value),
      salaire_mensuel: Number(editSalaireMensuel.value) || 0.0,
      salaire_horaire: Number(editSalaireHoraire.value) || 0.0,
      type_salaire: editTypeSalaire.value,
      mode_calcul: editModeCalcul.value,
      statut: editStatut.value,
      unite_temps: editUniteTemps.value,
      sursalaire: Number(editSursalaire.value) || 0.0,
      indemnite_transport: Number(editIndemniteTransport.value) || 0.0,
      dotation_telephonique: Number(editDotationTelephonique.value) || 0.0
    }

    const res = await put(`/contrats/${contratId}`, payload)
    if (res) {
      toast.add({
        title: 'Mis à jour',
        description: 'Le contrat de travail a été mis à jour avec succès.',
        color: 'success'
      })
      await fetchContratDetails()
    }
  } catch (e) {
    console.error(e)
    if (e.status === 422) {
      fieldErrors.value = extractFieldErrors(e)
    }
  }
}

const handleCalculateBulletin = async () => {
  calcLoading.value = true
  try {
    const payload = {
      contrat_id: Number(contratId),
      mois: Number(calcMois.value),
      annee: Number(calcAnnee.value),
      acompte: Number(calcAcompte.value) || 0.0,
      commentaire: calcCommentaire.value || null
    }
    const res = await post('/bulletins/calculer', payload)
    if (res) {
      toast.add({
        title: 'Bulletin calculé',
        description: `Le bulletin pour la période ${calcMois.value}/${calcAnnee.value} a été généré avec succès.`,
        color: 'success'
      })
      showModal.value = false
      calcAcompte.value = 0.0
      calcCommentaire.value = ''
      await fetchContratDetails()
    }
  } catch (e) {
    console.error(e)
  } finally {
    calcLoading.value = false
  }
}

const handleDeleteContrat = async () => {
  if (!confirm('Supprimer définitivement ce contrat de travail ?')) return
  try {
    await apiDelete(`/contrats/${contratId}`)
    toast.add({
      title: 'Contrat supprimé',
      description: 'Le contrat de travail a été supprimé.',
      color: 'success'
    })
    router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}`)
  } catch (e) {
    console.error(e)
  }
}

const fetchDepartInfo = async () => {
  try {
    const dep = await get(`/contrats/${contratId}/depart`)
    departSalarie.value = dep
    if (dep) {
      departDateSortie.value = dep.date_sortie || ''
      departMotifSortie.value = dep.motif_sortie || 10
      departDernierJourTravaille.value = dep.dernier_jour_travaille || ''
      departMaintienAffiliation.value = dep.maintien_affiliation || false
      departCommentaire.value = dep.commentaire || ''

      const stcData = await get(`/contrats/${contratId}/solde-tout-compte`)
      soldeToutCompte.value = stcData
      if (stcData) {
        editIndemniteLicenciement.value = stcData.indemnite_licenciement || 0.0
        editIndemniteCongesPayes.value = stcData.indemnite_conges_payes || 0.0
        editIndemnitePreavis.value = stcData.indemnite_preavis || 0.0
        editIndemniteAutre.value = stcData.indemnite_autre || 0.0
        editStcCommentaire.value = stcData.commentaire || ''
      }
    } else {
      soldeToutCompte.value = null
    }
  } catch (e) {
    console.error("Error fetching departure info:", e)
  }
}

const handleDeclareDepart = async () => {
  if (!departDateSortie.value) {
    toast.add({
      title: 'Validation',
      description: 'La date de sortie est obligatoire.',
      color: 'warning'
    })
    return
  }
  try {
    const payload = {
      date_sortie: departDateSortie.value,
      motif_sortie: Number(departMotifSortie.value),
      dernier_jour_travaille: departDernierJourTravaille.value || null,
      maintien_affiliation: departMaintienAffiliation.value,
      commentaire: departCommentaire.value || null
    }
    const res = await post(`/contrats/${contratId}/depart`, payload)
    if (res) {
      toast.add({
        title: 'Départ enregistré',
        description: 'Le départ du salarié a été enregistré avec succès.',
        color: 'success'
      })
      showDepartModal.value = false
      await fetchContratDetails()
    }
  } catch (e) {
    console.error("Error declaring departure:", e)
  }
}

const handleCancelDepart = async () => {
  if (!confirm('Êtes-vous sûr de vouloir annuler le départ de ce salarié ? Cela réactivera le contrat et supprimera le Solde de Tout Compte.')) return
  try {
    await apiDelete(`/contrats/${contratId}/depart`)
    toast.add({
      title: 'Départ annulé',
      description: 'Le départ a été annulé et le contrat est repassé à l\'état actif.',
      color: 'success'
    })
    departSalarie.value = null
    soldeToutCompte.value = null
    await fetchContratDetails()
  } catch (e) {
    console.error("Error cancelling departure:", e)
  }
}

const handleSaveStc = async () => {
  savingStc.value = true
  try {
    const payload = {
      indemnite_licenciement: Number(editIndemniteLicenciement.value) || 0.0,
      indemnite_conges_payes: Number(editIndemniteCongesPayes.value) || 0.0,
      indemnite_preavis: Number(editIndemnitePreavis.value) || 0.0,
      indemnite_autre: Number(editIndemniteAutre.value) || 0.0,
      commentaire: editStcCommentaire.value || null,
      statut: soldeToutCompte.value ? soldeToutCompte.value.statut : 'genere'
    }
    const res = await put(`/contrats/${contratId}/solde-tout-compte`, payload)
    if (res) {
      toast.add({
        title: 'Solde Tout Compte mis à jour',
        description: 'Les montants du Solde de Tout Compte ont été enregistrés.',
        color: 'success'
      })
      await fetchContratDetails()
    }
  } catch (e) {
    console.error("Error saving STC:", e)
  } finally {
    savingStc.value = false
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

onMounted(() => {
  fetchContratDetails()
})
</script>

<template>
  <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement du contrat de travail...</span>
  </div>

  <div v-else-if="contrat" class="space-y-6">
    <!-- Header Object page -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-50 text-green-700 rounded-lg flex items-center justify-center font-bold text-lg border border-green-200">
          CT
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-900 leading-tight">
            Contrat N° {{ contrat.numero_contrat }}
          </h1>
          <p class="text-xs text-slate-500 font-mono mt-1">Poste : {{ contrat.emploi || 'Non spécifié' }}</p>
        </div>
      </div>
      
      <div class="flex space-x-3">
        <button 
          @click="handleDeleteContrat"
          class="px-4 py-2 border border-red-200 text-sm font-semibold rounded-lg hover:bg-red-50 text-red-600 transition-colors flex items-center gap-1.5"
        >
          <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
          Rupture / Supprimer
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Left 2 Cols: Edit Form -->
      <div class="lg:col-span-2 space-y-6">
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <form @submit.prevent="handleUpdateContrat" class="space-y-6">
            <h3 class="text-lg font-bold text-slate-900 border-b border-slate-100 pb-2">Paramètres du Contrat</h3>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Poste (Grille Salariale)</label>
                <select 
                  v-model="editPosteSalaireId"
                  class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 w-full"
                >
                  <option :value="null">-- Aucun poste (saisie libre) --</option>
                  <option v-for="p in postes" :key="p.id" :value="p.id">
                    {{ p.categorie_professionnelle }} - {{ p.echelon_categorie }} 
                    {{ p.salaire_mensuel_fcfa ? `(${p.salaire_mensuel_fcfa} FCFA)` : `(${p.taux_horaire_fcfa} FCFA/h)` }}
                  </option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Intitulé de l'emploi (Poste)</label>
                <input 
                  v-model="editEmploi" 
                  type="text" 
                  placeholder="Ex: Développeur Senior" 
                  :class="[
                    'mt-1 block w-full px-3 py-2 border rounded-lg text-sm transition-colors',
                    fieldErrors.emploi ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                  ]"
                />
                <p v-if="fieldErrors.emploi" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.emploi }}</p>
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Statut du contrat</label>
                <select v-model="editStatut" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                  <option value="actif">Actif</option>
                  <option value="suspendu">Suspendu (ex: congé sabbatique)</option>
                  <option value="termine">Terminé (sortie de grille)</option>
                </select>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Type de Contrat</label>
                <select v-model="editTypeContrat" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                  <option :value="10">CDI - Contrat à durée indéterminée (10)</option>
                  <option :value="29">CDD - Contrat à durée déterminée (29)</option>
                  <option :value="18">Contrat Apprentissage (18)</option>
                  <option :value="28">Contrat de professionnalisation (28)</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Mode de Rémunération</label>
                <select v-model="editTypeSalaire" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                  <option value="Mensuel">Salaire Mensuel Fixe</option>
                  <option value="Horaire">Taux Horaire</option>
                </select>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 border-t border-slate-100 pt-4">
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Salaire Mensuel {{ editModeCalcul === 'net' ? 'Net' : 'Brut' }} (FCFA)
                </label>
                <input 
                  v-model="editSalaireMensuel" 
                  type="number" 
                  step="0.01" 
                  :class="[
                    'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono transition-colors',
                    fieldErrors.salaire_mensuel ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300'
                  ]"
                />
                <p v-if="fieldErrors.salaire_mensuel" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.salaire_mensuel }}</p>
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Taux Horaire {{ editModeCalcul === 'net' ? 'Net' : 'Brut' }} (FCFA)
                </label>
                <input 
                  v-model="editSalaireHoraire" 
                  type="number" 
                  step="0.01" 
                  :class="[
                    'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono transition-colors',
                    fieldErrors.salaire_horaire ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300'
                  ]"
                />
                <p v-if="fieldErrors.salaire_horaire" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.salaire_horaire }}</p>
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nature du salaire</label>
                <select v-model="editModeCalcul" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                  <option value="brut">Brut</option>
                  <option value="net">Net</option>
                </select>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 border-t border-slate-100 pt-4">
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Unité de Temps</label>
                <select v-model="editUniteTemps" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                  <option value="Heures">Heures</option>
                  <option value="Jours">Jours</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Sursalaire (FCFA)</label>
                <input 
                  v-model="editSursalaire" 
                  type="number" 
                  step="0.01" 
                  :class="[
                    'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono transition-colors',
                    fieldErrors.sursalaire ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300'
                  ]"
                />
                <p v-if="fieldErrors.sursalaire" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.sursalaire }}</p>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Indemnité de Transport (FCFA)</label>
                <input 
                  v-model="editIndemniteTransport" 
                  type="number" 
                  step="0.01" 
                  :class="[
                    'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono transition-colors',
                    fieldErrors.indemnite_transport ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300'
                  ]"
                />
                <p v-if="fieldErrors.indemnite_transport" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.indemnite_transport }}</p>
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Dotation Téléphonique (FCFA)</label>
                <input 
                  v-model="editDotationTelephonique" 
                  type="number" 
                  step="0.01" 
                  :class="[
                    'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono transition-colors',
                    fieldErrors.dotation_telephonique ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300'
                  ]"
                />
                <p v-if="fieldErrors.dotation_telephonique" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.dotation_telephonique }}</p>
              </div>
            </div>

            <div class="flex justify-end pt-4 border-t border-slate-100">
              <button type="submit" class="px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow transition-colors">
                Mettre à jour le contrat
              </button>
            </div>
          </form>
        </div>

        <!-- Bulletins de paie list -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
            <div>
              <h3 class="text-lg font-bold text-slate-900">Bulletins de Paie</h3>
              <p class="text-xs text-slate-500">Bulletins calculés pour ce contrat.</p>
            </div>
            <button 
              @click="showModal = true"
              class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <UIcon name="i-lucide-calculator" class="w-3.5 h-3.5" />
              Calculer un bulletin
            </button>
          </div>

          <div v-if="bulletins.length === 0" class="text-center py-8 text-slate-500 italic text-sm">
            Aucun bulletin généré pour ce contrat.
          </div>
          <div v-else class="overflow-x-auto">
            <table class="min-w-full divide-y divide-slate-200 text-sm">
              <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th scope="col" class="px-4 py-3 text-left">Période</th>
                  <th scope="col" class="px-4 py-3 text-left">Statut</th>
                  <th scope="col" class="px-4 py-3 text-right">Brut (FCFA)</th>
                  <th scope="col" class="px-4 py-3 text-right">Retenues (FCFA)</th>
                  <th scope="col" class="px-4 py-3 text-right">Net à Payer (FCFA)</th>
                  <th scope="col" class="relative px-4 py-3"><span class="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-150 bg-white">
                <tr 
                  v-for="b in bulletins" 
                  :key="b.id"
                  @click="router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/${contratId}/bulletins/${b.id}`)"
                  class="hover:bg-slate-50 cursor-pointer group"
                >
                  <td class="px-4 py-3 font-semibold text-slate-800">
                    {{ String(b.mois).padStart(2, '0') }}/{{ b.annee }}
                  </td>
                  <td class="px-4 py-3">
                    <span 
                      :class="[
                        b.statut === 'valide' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-yellow-50 text-yellow-700 border-yellow-200',
                        'px-2 py-0.5 rounded text-[10px] uppercase font-bold border'
                      ]"
                    >
                      {{ b.statut }}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-right font-mono text-slate-600">
                    {{ b.salaire_brut?.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) }}
                  </td>
                  <td class="px-4 py-3 text-right font-mono text-slate-600">
                    {{ b.cotisations_salariales?.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) }}
                  </td>
                  <td class="px-4 py-3 text-right font-mono font-bold text-slate-900">
                    {{ b.net_a_payer?.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) }}
                  </td>
                  <td class="px-4 py-3 text-right">
                    <span class="text-green-600 group-hover:underline text-xs font-semibold flex items-center justify-end gap-1">
                      Visualiser
                      <UIcon name="i-lucide-eye" class="w-4 h-4" />
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Right Col: Read-only Metadata Details -->
      <div class="space-y-6">
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h3 class="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">Informations Administratives</h3>
          
          <div class="space-y-3 text-xs">
            <div>
              <span class="block font-semibold text-slate-400 uppercase tracking-wider">Identifiant Contrat</span>
              <span class="text-sm font-mono font-bold text-slate-700">{{ contrat.numero_contrat }}</span>
            </div>
            <div>
              <span class="block font-semibold text-slate-400 uppercase tracking-wider">Date d'embauche</span>
              <span class="text-sm font-bold text-slate-700">{{ contrat.date_debut_contrat || 'Non renseignée' }}</span>
            </div>
            <div v-if="contrat.date_fin_previsionnelle_contrat">
              <span class="block font-semibold text-slate-400 uppercase tracking-wider">Fin de contrat prévue</span>
              <span class="text-sm font-bold text-slate-700">{{ contrat.date_fin_previsionnelle_contrat }}</span>
            </div>
            <div>
              <span class="block font-semibold text-slate-400 uppercase tracking-wider">Ancienneté retenue</span>
              <span class="text-sm font-bold text-slate-700">{{ contrat.date_anciennete || contrat.date_debut_contrat || 'Non renseignée' }}</span>
            </div>
            <div>
              <span class="block font-semibold text-slate-400 uppercase tracking-wider">IDCC (CCN)</span>
              <span class="text-sm font-mono font-bold text-slate-700">{{ contrat.idcc || 'Non renseigné' }}</span>
            </div>
            <div>
              <span class="block font-semibold text-slate-400 uppercase tracking-wider">Matricule Salarié</span>
              <span class="text-sm font-mono text-slate-700">{{ contrat.matricule_salarie }}</span>
            </div>
            <div>
              <span class="block font-semibold text-slate-400 uppercase tracking-wider">Code Établissement</span>
              <span class="text-sm font-mono text-slate-700">{{ contrat.code_etablissement }}</span>
            </div>
          </div>
        </div>

        <!-- Départ Salarié & Solde Tout Compte -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h3 class="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">Départ & Solde Tout Compte</h3>
          
          <div v-if="!departSalarie" class="space-y-4">
            <p class="text-xs text-slate-500 italic">
              Aucun départ n'a été enregistré pour ce salarié.
            </p>
            <button 
              type="button"
              @click="showDepartModal = true"
              class="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center justify-center gap-1.5 shadow-sm"
            >
              <UIcon name="i-lucide-log-out" class="w-4 h-4" />
              Déclarer la sortie du salarié
            </button>
          </div>

          <div v-else class="space-y-6">
            <!-- Summary -->
            <div class="bg-red-50/50 border border-red-200 rounded-lg p-3 space-y-2 text-xs text-slate-700">
              <div class="flex justify-between items-center">
                <span class="font-bold uppercase tracking-wider text-[10px] text-red-700">Sortie enregistrée</span>
                <span class="bg-red-100 text-red-800 text-[9px] font-bold px-1.5 py-0.5 rounded uppercase">
                  {{ getMotifLabel(departSalarie.motif_sortie) }}
                </span>
              </div>
              <div class="space-y-1">
                <p><strong>Date de sortie :</strong> {{ departSalarie.date_sortie }}</p>
                <p v-if="departSalarie.dernier_jour_travaille"><strong>Dernier jour travaillé :</strong> {{ departSalarie.dernier_jour_travaille }}</p>
                <p><strong>Maintien affiliation prévoyance :</strong> {{ departSalarie.maintien_affiliation ? 'Oui' : 'Non' }}</p>
              </div>
            </div>

            <!-- STC Form -->
            <div v-if="soldeToutCompte" class="space-y-3 pt-2 border-t border-slate-100">
              <h4 class="text-xs font-bold text-slate-800 uppercase tracking-wide">Indemnités de rupture (FCFA)</h4>
              
              <div class="space-y-2">
                <div>
                  <label class="block text-[10px] font-semibold text-slate-500 uppercase">Indemnité Congés Payés (brute)</label>
                  <input v-model="editIndemniteCongesPayes" type="number" step="0.01" class="mt-1 block w-full px-2 py-1 border border-slate-350 rounded-lg text-xs font-mono bg-white focus:outline-none focus:ring-1 focus:ring-green-500" />
                </div>
                <div>
                  <label class="block text-[10px] font-semibold text-slate-500 uppercase">Indemnité Licenciement / Rupture</label>
                  <input v-model="editIndemniteLicenciement" type="number" step="0.01" class="mt-1 block w-full px-2 py-1 border border-slate-350 rounded-lg text-xs font-mono bg-white focus:outline-none focus:ring-1 focus:ring-green-500" />
                </div>
                <div>
                  <label class="block text-[10px] font-semibold text-slate-500 uppercase">Indemnité de Préavis</label>
                  <input v-model="editIndemnitePreavis" type="number" step="0.01" class="mt-1 block w-full px-2 py-1 border border-slate-350 rounded-lg text-xs font-mono bg-white focus:outline-none focus:ring-1 focus:ring-green-500" />
                </div>
                <div>
                  <label class="block text-[10px] font-semibold text-slate-500 uppercase">Autre Indemnité</label>
                  <input v-model="editIndemniteAutre" type="number" step="0.01" class="mt-1 block w-full px-2 py-1 border border-slate-350 rounded-lg text-xs font-mono bg-white focus:outline-none focus:ring-1 focus:ring-green-500" />
                </div>
                <div class="bg-slate-50 border border-slate-200 rounded-lg p-2 flex justify-between items-center text-xs font-bold text-slate-900 font-mono">
                  <span>TOTAL STC :</span>
                  <span class="text-green-700 text-sm">{{ totalStc.toLocaleString('fr-FR') }} FCFA</span>
                </div>
                <div>
                  <label class="block text-[10px] font-semibold text-slate-500 uppercase">Notes / Commentaires</label>
                  <textarea v-model="editStcCommentaire" rows="2" class="mt-1 block w-full px-2 py-1 border border-slate-350 rounded-lg text-xs bg-white focus:outline-none focus:ring-1 focus:ring-green-500"></textarea>
                </div>
              </div>

              <button 
                type="button"
                @click="handleSaveStc"
                :disabled="savingStc"
                class="w-full px-3 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center justify-center gap-1.5 shadow-sm"
              >
                <UIcon name="i-lucide-save" class="w-4 h-4" />
                Mettre à jour le STC
              </button>
            </div>

            <!-- Exit Documents print links -->
            <div class="space-y-2 pt-4 border-t border-slate-100">
              <h4 class="text-xs font-bold text-slate-800 uppercase tracking-wide">Documents de sortie</h4>
              
              <div class="grid grid-cols-1 gap-2">
                <a 
                  :href="`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/${contratId}/depart/print-stc`" 
                  target="_blank"
                  class="px-3 py-2 border border-slate-250 hover:bg-slate-50 text-slate-700 font-semibold rounded-lg text-xs transition-colors flex items-center justify-between"
                >
                  <span class="flex items-center gap-1.5">
                    <UIcon name="i-lucide-printer" class="w-4 h-4 text-green-600" />
                    Reçu pour Solde de Tout Compte
                  </span>
                  <UIcon name="i-lucide-external-link" class="w-3.5 h-3.5 text-slate-400" />
                </a>

                <a 
                  :href="`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/${contratId}/depart/print-certificat`" 
                  target="_blank"
                  class="px-3 py-2 border border-slate-250 hover:bg-slate-50 text-slate-700 font-semibold rounded-lg text-xs transition-colors flex items-center justify-between"
                >
                  <span class="flex items-center gap-1.5">
                    <UIcon name="i-lucide-file-text" class="w-4 h-4 text-green-600" />
                    Certificat de travail
                  </span>
                  <UIcon name="i-lucide-external-link" class="w-3.5 h-3.5 text-slate-400" />
                </a>

                <a 
                  :href="`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/${contratId}/depart/print-attestation`" 
                  target="_blank"
                  class="px-3 py-2 border border-slate-250 hover:bg-slate-50 text-slate-700 font-semibold rounded-lg text-xs transition-colors flex items-center justify-between"
                >
                  <span class="flex items-center gap-1.5">
                    <UIcon name="i-lucide-file-signature" class="w-4 h-4 text-green-600" />
                    Attestation de travail
                  </span>
                  <UIcon name="i-lucide-external-link" class="w-3.5 h-3.5 text-slate-400" />
                </a>
              </div>
            </div>

            <!-- Cancel -->
            <button 
              type="button"
              @click="handleCancelDepart"
              class="w-full px-3 py-1.5 border border-red-200 text-red-650 hover:bg-red-50 font-semibold rounded-lg text-xs transition-colors flex items-center justify-center gap-1"
            >
              <UIcon name="i-lucide-x-circle" class="w-4 h-4" />
              Annuler la déclaration de sortie
            </button>
          </div>
        </div>
      </div>

    </div>

    <!-- Modal Calculer Bulletin -->
    <div v-if="showModal" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-xl w-full max-w-md space-y-4">
        <div class="flex justify-between items-center border-b border-slate-100 pb-3">
          <h3 class="text-lg font-bold text-slate-900">Calculer un Bulletin</h3>
          <button @click="showModal = false" class="text-slate-400 hover:text-slate-600">
            <UIcon name="i-lucide-x" class="w-5 h-5" />
          </button>
        </div>

        <form @submit.prevent="handleCalculateBulletin" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Mois</label>
              <select v-model="calcMois" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option v-for="m in 12" :key="m" :value="m">{{ String(m).padStart(2, '0') }}</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Année</label>
              <input v-model="calcAnnee" type="number" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Acompte à déduire (FCFA)</label>
            <input v-model="calcAcompte" type="number" step="0.01" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Commentaire (Optionnel)</label>
            <textarea v-model="calcCommentaire" rows="2" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"></textarea>
          </div>

          <div class="flex justify-end space-x-3 pt-3 border-t border-slate-100">
            <button type="button" @click="showModal = false" class="px-4 py-2 border border-slate-200 text-sm font-semibold rounded-lg hover:bg-slate-50 text-slate-700 transition-colors">
              Annuler
            </button>
            <button type="submit" :disabled="calcLoading" class="px-4 py-2 text-sm font-semibold bg-green-600 hover:bg-green-700 text-white rounded-lg shadow transition-colors flex items-center gap-1.5">
              <UIcon v-if="calcLoading" name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
              Lancer le calcul
            </button>
          </div>
        </form>
      </div>
    </div>
    <!-- Modal Déclarer Départ Salarié -->
    <div v-if="showDepartModal" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-xl w-full max-w-md space-y-4">
        <div class="flex justify-between items-center border-b border-slate-100 pb-3">
          <h3 class="text-lg font-bold text-slate-900">Déclarer le départ du salarié</h3>
          <button @click="showDepartModal = false" class="text-slate-400 hover:text-slate-600">
            <UIcon name="i-lucide-x" class="w-5 h-5" />
          </button>
        </div>

        <form @submit.prevent="handleDeclareDepart" class="space-y-4">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Date de sortie</label>
            <input v-model="departDateSortie" type="date" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Motif de la sortie</label>
            <select v-model="departMotifSortie" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
              <option :value="10">Démission</option>
              <option :value="20">Licenciement</option>
              <option :value="30">Rupture conventionnelle</option>
              <option :value="40">Fin de CDD</option>
              <option :value="50">Retraite</option>
              <option :value="60">Décès</option>
              <option :value="70">Force majeure</option>
              <option :value="99">Autre motif</option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Dernier jour travaillé (Optionnel)</label>
            <input v-model="departDernierJourTravaille" type="date" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
          </div>

          <div class="flex items-center space-x-2 pt-1">
            <input v-model="departMaintienAffiliation" type="checkbox" id="maintien_aff" class="w-4 h-4 text-green-600 border-slate-300 rounded focus:ring-green-500" />
            <label for="maintien_aff" class="text-xs text-slate-650">Maintien de l'affiliation prévoyance / santé</label>
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Commentaire / Motif détaillé</label>
            <textarea v-model="departCommentaire" rows="2" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" placeholder="Ex: rupture d'un commun accord..."></textarea>
          </div>

          <div class="flex justify-end space-x-3 pt-3 border-t border-slate-100">
            <button type="button" @click="showDepartModal = false" class="px-4 py-2 border border-slate-200 text-sm font-semibold rounded-lg hover:bg-slate-50 text-slate-700 transition-colors">
              Annuler
            </button>
            <button type="submit" class="px-4 py-2 text-sm font-semibold bg-red-600 hover:bg-red-700 text-white rounded-lg shadow transition-colors flex items-center gap-1.5">
              Déclarer le départ
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
