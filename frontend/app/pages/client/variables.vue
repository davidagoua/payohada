<script setup>
const { user, token } = useSupabase()
const { get, post, del } = useApi()
const toast = useToast()
const config = useRuntimeConfig()
const apiBase = config.public.apiBase || 'http://localhost:8000'

const loading = ref(true)
const dossier = ref(null)
const selectedMois = ref(new Date().getMonth() + 1)
const selectedAnnee = ref(String(new Date().getFullYear()))
const searchQuery = ref('')

const periodeStatut = ref({ statut: 'saisie_en_cours' })
const salariesRows = ref([])

// Modals state
const hsModalOpen = ref(false)
const absenceModalOpen = ref(false)
const primeModalOpen = ref(false)
const transmitModalOpen = ref(false)
const excelImportModalOpen = ref(false)

const selectedContract = ref(null)

// Form states
const hsForm = ref({ code: 'HS15', nombre: 1 })
const absenceForm = ref({
  code: 'CP',
  date_debut: '',
  date_fin: '',
  nbr_jour_by_user: 1,
  nbr_heure_by_user: 0
})
const primeForm = ref({
  code: 'PRIME_RENDEMENT',
  montant: 0,
  libelle: 'Prime de rendement'
})
const transmitNotes = ref('')
const transmitting = ref(false)
const excelImporting = ref(false)
const excelExporting = ref(false)

const months = [
  { value: 1, label: 'Janvier' },
  { value: 2, label: 'Février' },
  { value: 3, label: 'Mars' },
  { value: 4, label: 'Avril' },
  { value: 5, label: 'Mai' },
  { value: 6, label: 'Juin' },
  { value: 7, label: 'Juillet' },
  { value: 8, label: 'Août' },
  { value: 9, label: 'Septembre' },
  { value: 10, label: 'Octobre' },
  { value: 11, label: 'Novembre' },
  { value: 12, label: 'Décembre' }
]

const years = [
  String(new Date().getFullYear() - 1),
  String(new Date().getFullYear()),
  String(new Date().getFullYear() + 1)
]

const currentPeriodLabel = computed(() => {
  const m = months.find(item => item.value === Number(selectedMois.value))
  return `${m ? m.label : ''} ${selectedAnnee.value}`
})

const fetchDossierAndVariables = async () => {
  loading.value = true
  try {
    const dossiers = await get('/dossiers')
    if (dossiers && dossiers.length > 0) {
      const targetId = user.value?.dossier_id || dossiers[0].id
      dossier.value = dossiers.find(d => d.id === targetId) || dossiers[0]
    }

    if (dossier.value) {
      // 1. Statut de la période
      try {
        periodeStatut.value = await get(
          `/dossiers/${dossier.value.id}/periodes/${selectedAnnee.value}/${selectedMois.value}/statut`
        )
      } catch (e) {
        periodeStatut.value = { statut: 'saisie_en_cours' }
      }

      // 2. Grille des salariés et variables
      salariesRows.value = await get(
        `/dossiers/${dossier.value.id}/variables-mensuelles?mois=${selectedMois.value}&annee=${selectedAnnee.value}`
      )
    }
  } catch (e) {
    console.error("Erreur chargement variables:", e)
    toast.add({ title: "Erreur", description: "Impossible de charger la grille des variables.", color: "danger" })
  } finally {
    loading.value = false
  }
}

watch([selectedMois, selectedAnnee], () => {
  fetchDossierAndVariables()
})

onMounted(() => {
  fetchDossierAndVariables()
})

const filteredRows = computed(() => {
  if (!searchQuery.value) return salariesRows.value
  const q = searchQuery.value.toLowerCase()
  return salariesRows.value.filter(r => 
    r.nom.toLowerCase().includes(q) ||
    r.prenom.toLowerCase().includes(q) ||
    r.matricule.toLowerCase().includes(q) ||
    (r.intitule_poste && r.intitule_poste.toLowerCase().includes(q))
  )
})

const formatFCFA = (amount) => {
  if (amount === undefined || amount === null) return '0 FCFA'
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XOF', minimumFractionDigits: 0 })
    .format(amount)
    .replace('XOF', 'FCFA')
}

// ── Modals Triggers ──
const openHsModal = (row) => {
  selectedContract.value = row
  hsForm.value = { code: 'HS15', nombre: 1 }
  hsModalOpen.value = true
}

const openAbsenceModal = (row) => {
  selectedContract.value = row
  const today = new Date().toISOString().split('T')[0]
  absenceForm.value = {
    code: 'CP',
    date_debut: today,
    date_fin: today,
    nbr_jour_by_user: 1,
    nbr_heure_by_user: 0
  }
  absenceModalOpen.value = true
}

const openPrimeModal = (row) => {
  selectedContract.value = row
  primeForm.value = {
    code: 'PRIME_RENDEMENT',
    montant: 25000,
    libelle: 'Prime de rendement'
  }
  primeModalOpen.value = true
}

// ── Save Handlers ──
const submitHs = async () => {
  if (!selectedContract.value) return
  try {
    await post(`/contrats/${selectedContract.value.contrat_id}/heures-supplementaires`, {
      code: hsForm.value.code,
      nombre: parseFloat(hsForm.value.nombre),
      mois: Number(selectedMois.value),
      annee: String(selectedAnnee.value)
    })
    toast.add({ title: "Succès", description: "Heures supplémentaires ajoutées.", color: "success" })
    hsModalOpen.value = false
    await fetchDossierAndVariables()
  } catch (e) {
    toast.add({ title: "Erreur", description: "Impossible d'ajouter les heures sup.", color: "danger" })
  }
}

const submitAbsence = async () => {
  if (!selectedContract.value) return
  try {
    const dDebut = absenceForm.value.date_debut ? new Date(absenceForm.value.date_debut).toISOString() : new Date().toISOString()
    const dFin = absenceForm.value.date_fin ? new Date(absenceForm.value.date_fin).toISOString() : new Date().toISOString()
    
    await post(`/contrats/${selectedContract.value.contrat_id}/absences`, {
      code: absenceForm.value.code,
      date_debut: dDebut,
      date_fin: dFin,
      nbr_jour_by_user: parseFloat(absenceForm.value.nbr_jour_by_user || 0),
      nbr_heure_by_user: parseFloat(absenceForm.value.nbr_heure_by_user || 0),
      mois: Number(selectedMois.value),
      annee: String(selectedAnnee.value)
    })
    toast.add({ title: "Succès", description: "Absence / congé enregistré.", color: "success" })
    absenceModalOpen.value = false
    await fetchDossierAndVariables()
  } catch (e) {
    toast.add({ title: "Erreur", description: "Impossible d'enregistrer l'absence.", color: "danger" })
  }
}

const submitPrime = async () => {
  if (!selectedContract.value) return
  try {
    await post(`/contrats/${selectedContract.value.contrat_id}/primes`, {
      code: primeForm.value.code,
      montant: parseFloat(primeForm.value.montant || 0),
      libelle: primeForm.value.libelle || primeForm.value.code,
      mois: Number(selectedMois.value),
      annee: String(selectedAnnee.value)
    })
    toast.add({ title: "Succès", description: "Prime enregistrée.", color: "success" })
    primeModalOpen.value = false
    await fetchDossierAndVariables()
  } catch (e) {
    toast.add({ title: "Erreur", description: "Impossible d'enregistrer la prime.", color: "danger" })
  }
}

// ── Delete Handlers ──
const removeHs = async (hsId) => {
  if (!confirm("Voulez-vous supprimer cette déclaration d'heures supplémentaires ?")) return
  try {
    await del(`/contrats/heures-supplementaires/${hsId}`)
    toast.add({ title: "Supprimé", description: "Heures sup supprimées.", color: "info" })
    await fetchDossierAndVariables()
  } catch (e) {
    toast.add({ title: "Erreur", description: "Erreur lors de la suppression.", color: "danger" })
  }
}

const removeAbsence = async (absId) => {
  if (!confirm("Voulez-vous supprimer cette absence ?")) return
  try {
    await del(`/contrats/absences/${absId}`)
    toast.add({ title: "Supprimé", description: "Absence supprimée.", color: "info" })
    await fetchDossierAndVariables()
  } catch (e) {
    toast.add({ title: "Erreur", description: "Erreur lors de la suppression.", color: "danger" })
  }
}

const removePrime = async (primeId) => {
  if (!confirm("Voulez-vous supprimer cette prime ?")) return
  try {
    await del(`/contrats/primes/${primeId}`)
    toast.add({ title: "Supprimé", description: "Prime supprimée.", color: "info" })
    await fetchDossierAndVariables()
  } catch (e) {
    toast.add({ title: "Erreur", description: "Erreur lors de la suppression.", color: "danger" })
  }
}

// ── Transmission au Cabinet ──
const openTransmitModal = () => {
  transmitNotes.value = ''
  transmitModalOpen.value = true
}

const submitTransmission = async () => {
  if (!dossier.value) return
  transmitting.value = true
  try {
    await post(`/dossiers/${dossier.value.id}/periodes/${selectedAnnee.value}/${selectedMois.value}/transmettre`, {
      notes: transmitNotes.value
    })
    toast.add({
      title: "Variables Transmises !",
      description: "Votre cabinet a été notifié. La période est prête pour le calcul.",
      color: "success"
    })
    transmitModalOpen.value = false
    await fetchDossierAndVariables()
  } catch (e) {
    toast.add({ title: "Erreur", description: "La transmission a échoué.", color: "danger" })
  } finally {
    transmitting.value = false
  }
}

// ── Excel Export / Import ──
const handleExportExcel = async () => {
  if (!dossier.value) return
  excelExporting.value = true
  try {
    const params = new URLSearchParams({
      mois: String(selectedMois.value),
      annee: String(selectedAnnee.value)
    })
    const url = `${apiBase}/api/v1/dossiers/${dossier.value.id}/export-variables-excel?${params}`
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    if (!response.ok) throw new Error("Échec du téléchargement")
    const blob = await response.blob()
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `variables_${dossier.value.code}_${String(selectedMois.value).padStart(2, '0')}_${selectedAnnee.value}.xlsx`
    link.click()
    URL.revokeObjectURL(link.href)
    toast.add({ title: "Téléchargement réussi", description: "Maquette Excel prête à être remplie.", color: "success" })
  } catch (e) {
    toast.add({ title: "Erreur", description: "Impossible d'exporter la maquette Excel.", color: "danger" })
  } finally {
    excelExporting.value = false
  }
}

const handleImportExcel = async (event) => {
  const input = event.target
  if (!input.files || input.files.length === 0 || !dossier.value) return
  const file = input.files[0]
  excelImporting.value = true
  try {
    const params = new URLSearchParams({
      mois: String(selectedMois.value),
      annee: String(selectedAnnee.value)
    })
    const url = `${apiBase}/api/v1/dossiers/${dossier.value.id}/import-variables-excel?${params}`
    const formData = new FormData()
    formData.append('fichier', file)
    const response = await fetch(url, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token.value}` },
      body: formData
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || "Erreur lors de l'import")
    }
    const res = await response.json()
    toast.add({
      title: "Importation terminée !",
      description: `${res.salaries_traites} salarié(s) traités, ${res.variables_creees} variables créées.`,
      color: "success"
    })
    excelImportModalOpen.value = false
    await fetchDossierAndVariables()
  } catch (e) {
    toast.add({ title: "Erreur import", description: e.message || "Échec de l'importation.", color: "danger" })
  } finally {
    excelImporting.value = false
    input.value = ''
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- En-tête de page & sélecteur de période -->
    <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <div class="flex items-center gap-2">
          <NuxtLink to="/client" class="text-xs text-slate-500 hover:text-green-600 font-semibold flex items-center gap-1">
            <UIcon name="i-lucide-arrow-left" class="w-3.5 h-3.5" />
            Tableau de bord
          </NuxtLink>
        </div>
        <h1 class="text-xl font-bold text-slate-900 mt-1">
          Saisie des Variables de Paie
        </h1>
        <p class="text-xs text-slate-500 mt-0.5">
          Renseignez les heures supplémentaires, congés, absences et primes nécessaires au calcul des bulletins.
        </p>
      </div>

      <!-- Contrôles Période & Actions -->
      <div class="flex flex-wrap items-center gap-3">
        <!-- Mois -->
        <div class="flex items-center gap-1.5 bg-slate-50 p-1.5 rounded-lg border border-slate-200">
          <label class="text-xs font-bold text-slate-600 ml-1">Mois :</label>
          <select 
            v-model="selectedMois" 
            class="bg-white border border-slate-250 rounded px-2.5 py-1 text-xs font-bold text-slate-800 focus:outline-hidden focus:ring-1 focus:ring-green-500"
          >
            <option v-for="m in months" :key="m.value" :value="m.value">
              {{ m.label }}
            </option>
          </select>

          <!-- Année -->
          <label class="text-xs font-bold text-slate-600 ml-2">Année :</label>
          <select 
            v-model="selectedAnnee" 
            class="bg-white border border-slate-250 rounded px-2.5 py-1 text-xs font-bold text-slate-800 focus:outline-hidden focus:ring-1 focus:ring-green-500"
          >
            <option v-for="y in years" :key="y" :value="y">
              {{ y }}
            </option>
          </select>
        </div>

        <!-- Export Excel -->
        <UButton 
          color="neutral" 
          variant="outline" 
          size="sm"
          :loading="excelExporting"
          @click="handleExportExcel"
        >
          <UIcon name="i-lucide-download" class="w-4 h-4 mr-1 text-green-600" />
          Maquette Excel
        </UButton>

        <!-- Import Excel -->
        <UButton 
          color="neutral" 
          variant="outline" 
          size="sm"
          @click="excelImportModalOpen = true"
        >
          <UIcon name="i-lucide-upload" class="w-4 h-4 mr-1 text-blue-600" />
          Importer Excel
        </UButton>

        <!-- Bouton de transmission au cabinet -->
        <UButton 
          color="primary" 
          size="sm"
          class="bg-green-600 hover:bg-green-700 text-white font-bold shadow-xs"
          @click="openTransmitModal"
        >
          <UIcon name="i-lucide-send" class="w-4 h-4 mr-1.5" />
          Transmettre au Cabinet
        </UButton>
      </div>
    </div>

    <!-- Bandeau Statut Période -->
    <div class="bg-white border rounded-xl p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3" :class="[
      periodeStatut?.statut === 'transmis' ? 'border-amber-300 bg-amber-50/50' : 
      (periodeStatut?.statut === 'calcule' ? 'border-green-300 bg-green-50/50' : 'border-slate-200')
    ]">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" :class="[
          periodeStatut?.statut === 'transmis' ? 'bg-amber-100 text-amber-700' :
          (periodeStatut?.statut === 'calcule' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-700')
        ]">
          <UIcon :name="
            periodeStatut?.statut === 'transmis' ? 'i-lucide-clock' :
            (periodeStatut?.statut === 'calcule' ? 'i-lucide-check-circle-2' : 'i-lucide-edit-3')
          " class="w-5 h-5" />
        </div>
        <div>
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold uppercase tracking-wider text-slate-600">Statut de la période :</span>
            <span class="text-xs font-black" :class="[
              periodeStatut?.statut === 'transmis' ? 'text-amber-700' :
              (periodeStatut?.statut === 'calcule' ? 'text-green-700' : 'text-slate-800')
            ]">
              {{
                periodeStatut?.statut === 'transmis' ? 'Transmis au cabinet • En attente de calcul' :
                (periodeStatut?.statut === 'calcule' ? 'Bulletins calculés par le cabinet' : 'Saisie en cours • Modifiable')
              }}
            </span>
          </div>
          <p v-if="periodeStatut?.date_transmission" class="text-[11px] text-slate-500 mt-0.5">
            Transmis le {{ new Date(periodeStatut.date_transmission).toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' }) }}
          </p>
          <p v-else class="text-[11px] text-slate-500 mt-0.5">
            Vous pouvez modifier librement les variables ci-dessous avant de cliquer sur "Transmettre au Cabinet".
          </p>
        </div>
      </div>

      <div class="flex items-center gap-3 self-end sm:self-center">
        <span class="text-xs font-semibold text-slate-500">
          {{ filteredRows.length }} salarié(s) dans la grille
        </span>
      </div>
    </div>

    <!-- Barre de recherche -->
    <div class="flex items-center justify-between gap-4">
      <div class="relative w-full max-w-sm">
        <UIcon name="i-lucide-search" class="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Filtrer par nom, prénom, matricule ou poste..."
          class="w-full bg-white border border-slate-200 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-hidden focus:ring-1 focus:ring-green-500"
        />
      </div>
    </div>

    <!-- Tableau de saisie collective -->
    <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
      <div v-if="loading" class="p-12 text-center text-slate-400">
        <UIcon name="i-lucide-loader-2" class="w-8 h-8 mx-auto animate-spin mb-2" />
        <p class="text-xs">Chargement de la grille des variables...</p>
      </div>

      <div v-else-if="filteredRows.length === 0" class="p-12 text-center text-slate-500">
        <UIcon name="i-lucide-users" class="w-10 h-10 mx-auto text-slate-300 mb-2" />
        <p class="text-sm font-bold text-slate-800">Aucun salarié trouvé</p>
        <p class="text-xs text-slate-500 mt-1">Aucun contrat actif n'est associé à cette entreprise pour cette période.</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 text-left">
          <thead class="bg-slate-50 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
            <tr>
              <th scope="col" class="px-4 py-3">Salarié</th>
              <th scope="col" class="px-4 py-3">Salaire de Base</th>
              <th scope="col" class="px-4 py-3">Heures Supplémentaires</th>
              <th scope="col" class="px-4 py-3">Congés & Absences</th>
              <th scope="col" class="px-4 py-3">Primes & Indemnités</th>
              <th scope="col" class="px-4 py-3 text-right">Statut Bulletin</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-150 text-xs">
            <tr v-for="row in filteredRows" :key="row.contrat_id" class="hover:bg-slate-50/70 transition-colors">
              <!-- Salarié Info -->
              <td class="px-4 py-3.5">
                <div class="font-bold text-slate-900 flex items-center gap-1.5">
                  {{ row.nom }} {{ row.prenom }}
                </div>
                <div class="text-[11px] text-slate-500 flex items-center gap-2 mt-0.5">
                  <span class="font-mono bg-slate-100 px-1 rounded text-slate-600">{{ row.matricule }}</span>
                  <span>{{ row.intitule_poste }}</span>
                </div>
              </td>

              <!-- Salaire Base -->
              <td class="px-4 py-3.5 font-medium text-slate-700">
                {{ formatFCFA(row.salaire_base) }}
              </td>

              <!-- Heures Sup -->
              <td class="px-4 py-3.5">
                <div class="flex flex-wrap items-center gap-1.5">
                  <span 
                    v-for="hs in row.heures_supplementaires" 
                    :key="hs.id"
                    class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-amber-50 text-amber-800 border border-amber-200 group"
                  >
                    <span>{{ hs.nombre }}h ({{ hs.code }})</span>
                    <button 
                      type="button" 
                      class="hover:text-red-600 opacity-60 group-hover:opacity-100 cursor-pointer ml-0.5" 
                      title="Supprimer"
                      @click="removeHs(hs.id)"
                    >
                      &times;
                    </button>
                  </span>

                  <!-- Bouton + HS -->
                  <button 
                    type="button" 
                    class="inline-flex items-center gap-0.5 px-2 py-0.5 rounded text-[11px] font-semibold text-amber-700 hover:bg-amber-100 border border-dashed border-amber-300 transition-colors cursor-pointer"
                    @click="openHsModal(row)"
                  >
                    <UIcon name="i-lucide-plus" class="w-3 h-3" />
                    HS
                  </button>
                </div>
              </td>

              <!-- Absences / Congés -->
              <td class="px-4 py-3.5">
                <div class="flex flex-wrap items-center gap-1.5">
                  <span 
                    v-for="abs in row.absences" 
                    :key="abs.id"
                    class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-red-50 text-red-800 border border-red-200 group"
                  >
                    <span>{{ abs.code }}: {{ abs.nbr_jour_by_user || 0 }}j</span>
                    <button 
                      type="button" 
                      class="hover:text-red-700 opacity-60 group-hover:opacity-100 cursor-pointer ml-0.5" 
                      title="Supprimer"
                      @click="removeAbsence(abs.id)"
                    >
                      &times;
                    </button>
                  </span>

                  <!-- Bouton + Absence -->
                  <button 
                    type="button" 
                    class="inline-flex items-center gap-0.5 px-2 py-0.5 rounded text-[11px] font-semibold text-red-700 hover:bg-red-100 border border-dashed border-red-300 transition-colors cursor-pointer"
                    @click="openAbsenceModal(row)"
                  >
                    <UIcon name="i-lucide-plus" class="w-3 h-3" />
                    Absence
                  </button>
                </div>
              </td>

              <!-- Primes -->
              <td class="px-4 py-3.5">
                <div class="flex flex-wrap items-center gap-1.5">
                  <span 
                    v-for="p in row.primes" 
                    :key="p.id"
                    class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-purple-50 text-purple-800 border border-purple-200 group"
                  >
                    <span>{{ p.libelle || p.code }}: {{ formatFCFA(p.montant) }}</span>
                    <button 
                      type="button" 
                      class="hover:text-red-600 opacity-60 group-hover:opacity-100 cursor-pointer ml-0.5" 
                      title="Supprimer"
                      @click="removePrime(p.id)"
                    >
                      &times;
                    </button>
                  </span>

                  <!-- Bouton + Prime -->
                  <button 
                    type="button" 
                    class="inline-flex items-center gap-0.5 px-2 py-0.5 rounded text-[11px] font-semibold text-purple-700 hover:bg-purple-100 border border-dashed border-purple-300 transition-colors cursor-pointer"
                    @click="openPrimeModal(row)"
                  >
                    <UIcon name="i-lucide-plus" class="w-3 h-3" />
                    Prime
                  </button>
                </div>
              </td>

              <!-- Statut Bulletin -->
              <td class="px-4 py-3.5 text-right">
                <div v-if="row.has_bulletin" class="flex flex-col items-end">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-green-100 text-green-800 border border-green-200">
                    Calculé
                  </span>
                  <span class="text-xs font-black text-slate-900 mt-0.5">
                    {{ formatFCFA(row.net_a_payer) }}
                  </span>
                </div>
                <div v-else>
                  <span class="text-[11px] text-slate-400 italic">En attente de calcul</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ═══ Modal : Ajout Heures Supplémentaires ═══ -->
    <UModal v-model:open="hsModalOpen" title="Déclarer des Heures Supplémentaires">
      <template #body>
        <div class="space-y-4">
          <div class="bg-slate-50 p-3 rounded-lg border text-xs text-slate-600">
            Salarié : <strong>{{ selectedContract?.nom }} {{ selectedContract?.prenom }}</strong> ({{ selectedContract?.matricule }})
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Type de majoration :</label>
            <select v-model="hsForm.code" class="w-full bg-white border border-slate-300 rounded px-3 py-1.5 text-xs font-semibold">
              <option value="HS15">HS15 (Heures de jour de 41e à 48e h • +15%)</option>
              <option value="HS25">HS25 (Majoration standard • +25%)</option>
              <option value="HS50">HS50 (Au-delà de 48h ou nuit • +50%)</option>
              <option value="HS75">HS75 (Dimanches & jours fériés de jour • +75%)</option>
              <option value="HS100">HS100 (Dimanches & jours fériés de nuit • +100%)</option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Nombre d'heures :</label>
            <input 
              v-model.number="hsForm.nombre" 
              type="number" 
              step="0.5" 
              min="0.5" 
              class="w-full bg-white border border-slate-300 rounded px-3 py-1.5 text-xs font-semibold"
            />
          </div>
        </div>
      </template>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton color="neutral" variant="ghost" @click="hsModalOpen = false">Annuler</UButton>
          <UButton color="primary" class="bg-green-600 hover:bg-green-700 text-white font-bold" @click="submitHs">
            Enregistrer
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- ═══ Modal : Ajout Absence / Congé ═══ -->
    <UModal v-model:open="absenceModalOpen" title="Déclarer une Absence ou un Congé">
      <template #body>
        <div class="space-y-4">
          <div class="bg-slate-50 p-3 rounded-lg border text-xs text-slate-600">
            Salarié : <strong>{{ selectedContract?.nom }} {{ selectedContract?.prenom }}</strong>
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Motif / Type :</label>
            <select v-model="absenceForm.code" class="w-full bg-white border border-slate-300 rounded px-3 py-1.5 text-xs font-semibold">
              <option value="CP">Congés Payés (CP)</option>
              <option value="MAL">Maladie ordinaire (MAL)</option>
              <option value="AT">Accident du Travail (AT)</option>
              <option value="MAT">Maternité (MAT)</option>
              <option value="CSS">Congé Sans Solde (CSS)</option>
              <option value="ABS">Absence injustifiée (ABS)</option>
              <option value="PERM">Permission exceptionnelle</option>
            </select>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">Date début :</label>
              <input v-model="absenceForm.date_debut" type="date" class="w-full bg-white border border-slate-300 rounded px-2.5 py-1 text-xs" />
            </div>
            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">Date fin :</label>
              <input v-model="absenceForm.date_fin" type="date" class="w-full bg-white border border-slate-300 rounded px-2.5 py-1 text-xs" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">Nombre de jours :</label>
              <input v-model.number="absenceForm.nbr_jour_by_user" type="number" step="0.5" min="0" class="w-full bg-white border border-slate-300 rounded px-2.5 py-1 text-xs" />
            </div>
            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">Nombre d'heures (optionnel) :</label>
              <input v-model.number="absenceForm.nbr_heure_by_user" type="number" step="0.5" min="0" class="w-full bg-white border border-slate-300 rounded px-2.5 py-1 text-xs" />
            </div>
          </div>
        </div>
      </template>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton color="neutral" variant="ghost" @click="absenceModalOpen = false">Annuler</UButton>
          <UButton color="primary" class="bg-red-600 hover:bg-red-700 text-white font-bold" @click="submitAbsence">
            Enregistrer
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- ═══ Modal : Ajout Prime ═══ -->
    <UModal v-model:open="primeModalOpen" title="Déclarer une Prime ou Indemnité">
      <template #body>
        <div class="space-y-4">
          <div class="bg-slate-50 p-3 rounded-lg border text-xs text-slate-600">
            Salarié : <strong>{{ selectedContract?.nom }} {{ selectedContract?.prenom }}</strong>
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Type de Prime :</label>
            <select v-model="primeForm.code" class="w-full bg-white border border-slate-300 rounded px-3 py-1.5 text-xs font-semibold">
              <option value="PRIME_RENDEMENT">Prime de rendement / performance</option>
              <option value="PRIME_TRANSPORT">Indemnité de transport exceptionnelle</option>
              <option value="PRIME_PANIER">Prime de panier / repas</option>
              <option value="PRIME_EXC">Prime exceptionnelle</option>
              <option value="GRATIFICATION">Gratification / 13e mois</option>
              <option value="AVANCE_ACOMPTE">Acompte sur salaire (Déduction)</option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Libellé sur le bulletin :</label>
            <input v-model="primeForm.libelle" type="text" class="w-full bg-white border border-slate-300 rounded px-3 py-1.5 text-xs" />
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Montant (FCFA) :</label>
            <input v-model.number="primeForm.montant" type="number" step="1000" min="0" class="w-full bg-white border border-slate-300 rounded px-3 py-1.5 text-xs font-bold" />
          </div>
        </div>
      </template>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton color="neutral" variant="ghost" @click="primeModalOpen = false">Annuler</UButton>
          <UButton color="primary" class="bg-purple-600 hover:bg-purple-700 text-white font-bold" @click="submitPrime">
            Enregistrer
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- ═══ Modal : Transmission au Cabinet ═══ -->
    <UModal v-model:open="transmitModalOpen" title="Transmettre les variables au cabinet">
      <template #body>
        <div class="space-y-4">
          <div class="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 flex items-start gap-2">
            <UIcon name="i-lucide-alert-circle" class="w-5 h-5 shrink-0 text-amber-600 mt-0.5" />
            <div>
              Vous êtes sur le point de transmettre officiellement les éléments variables de <strong>{{ currentPeriodLabel }}</strong> à votre gestionnaire de paie.
              Le statut passera à <strong>"Transmis"</strong> et votre cabinet pourra lancer le calcul des bulletins.
            </div>
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Notes ou instructions pour le gestionnaire (optionnel) :</label>
            <textarea 
              v-model="transmitNotes" 
              rows="3" 
              placeholder="Ex: Merci de vérifier les heures sup de l'équipe technique, primes de fin de trimestre incluses..."
              class="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs"
            ></textarea>
          </div>
        </div>
      </template>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton color="neutral" variant="ghost" @click="transmitModalOpen = false">Annuler</UButton>
          <UButton 
            color="primary" 
            :loading="transmitting"
            class="bg-green-600 hover:bg-green-700 text-white font-bold" 
            @click="submitTransmission"
          >
            Confirmer la Transmission
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- ═══ Modal : Import Excel ═══ -->
    <UModal v-model:open="excelImportModalOpen" title="Importer la matrice Excel des variables">
      <template #body>
        <div class="space-y-4">
          <p class="text-xs text-slate-600 leading-relaxed">
            Importez le fichier Excel préalablement rempli (format officiel QPXL1501). Les variables seront automatiquement injectées dans la base de données.
          </p>

          <div class="border-2 border-dashed border-slate-300 hover:border-green-500 rounded-xl p-6 text-center transition-colors">
            <UIcon name="i-lucide-file-spreadsheet" class="w-10 h-10 mx-auto text-green-600 mb-2" />
            <label class="cursor-pointer">
              <span class="text-xs font-bold text-green-700 hover:underline">Sélectionner un fichier Excel (.xlsx, .xls)</span>
              <input type="file" accept=".xlsx,.xls" class="hidden" @change="handleImportExcel" />
            </label>
            <p class="text-[11px] text-slate-400 mt-1">Période : {{ currentPeriodLabel }}</p>
          </div>
        </div>
      </template>
      <template #footer>
        <div class="flex justify-end">
          <UButton color="neutral" variant="ghost" @click="excelImportModalOpen = false">Fermer</UButton>
        </div>
      </template>
    </UModal>
  </div>
</template>
