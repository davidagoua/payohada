<script setup>
const route = useRoute()
const router = useRouter()
const { get, post, extractFieldErrors } = useApi()
const toast = useToast()

const dossierId = route.params.dossierId
const etabId = route.params.etabId
const salarieId = route.params.salarieId

const loadingContext = ref(true)
const currentDossier = useState('current-dossier')
const currentEtab = ref(null)
const currentSalarie = ref(null)

// Form Fields
const cNumero = ref('')
const fieldErrors = ref({})
const cTypeContrat = ref(10) // CDI by default
const cStatutPro = ref(2)    // Non-cadre by default
const cSalaireMensuel = ref(250000)
const cSalaireHoraire = ref(11.85)
const cTypeSalaire = ref('Mensuel')
const cModeCalcul = ref('brut')
const cDateDebut = ref(new Date().toISOString().substring(0, 10))
const cDateFin = ref('')
const cEmploi = ref('')
const cIdcc = ref(1486) // Bureau d'études (Syntec) by default
const cUniteTemps = ref('Heures')
const cSursalaire = ref(0.0)
const cIndemniteTransport = ref(0.0)
const cDotationTelephonique = ref(0.0)

const postes = ref([])
const cPosteSalaireId = ref(null)

const fetchPostes = async () => {
  try {
    if (currentEtab.value && currentEtab.value.secteur_id) {
      postes.value = await get(`/secteurs/${currentEtab.value.secteur_id}/postes`) || []
    } else {
      postes.value = await get('/postes-salaires') || []
    }
  } catch (e) {
    console.error("Error loading postes:", e)
  }
}

watch(cPosteSalaireId, (newId) => {
  if (!newId) return
  const match = postes.value.find(p => p.id === Number(newId))
  if (match) {
    cEmploi.value = `${match.categorie_professionnelle} - ${match.echelon_categorie}`
    if (match.salaire_mensuel_fcfa) {
      cSalaireMensuel.value = match.salaire_mensuel_fcfa
      cTypeSalaire.value = 'Mensuel'
    }
    if (match.taux_horaire_fcfa) {
      cSalaireHoraire.value = Number(match.taux_horaire_fcfa)
      if (!match.salaire_mensuel_fcfa) {
        cTypeSalaire.value = 'Horaire'
      }
    }
    updateSursalaire()
  }
})

const updateSursalaire = () => {
  if (!cPosteSalaireId.value) return
  const match = postes.value.find(p => p.id === Number(cPosteSalaireId.value))
  if (match) {
    if (cTypeSalaire.value === 'Mensuel') {
      const baseSalary = match.salaire_mensuel_fcfa || 0
      cSursalaire.value = Math.max(0, Number(cSalaireMensuel.value || 0) - baseSalary)
    } else {
      const baseSalary = Number(match.taux_horaire_fcfa || 0)
      cSursalaire.value = Math.max(0, Number(cSalaireHoraire.value || 0) - baseSalary)
    }
  }
}

watch([cSalaireMensuel, cSalaireHoraire, cTypeSalaire], () => {
  updateSursalaire()
})

const fetchContextDetails = async () => {
  loadingContext.value = true
  try {
    if (!currentDossier.value) {
      const data = await get(`/dossiers/${dossierId}`)
      currentDossier.value = data
    }
    const etabData = await get(`/etablissements/${etabId}`)
    currentEtab.value = etabData

    const salData = await get(`/salaries/${salarieId}`)
    currentSalarie.value = salData
    await fetchPostes()
  } catch (e) {
    console.error(e)
    router.push(`/dossiers/${dossierId}/etablissements/${etabId}`)
  } finally {
    loadingContext.value = false
  }
}

const handleCreateContract = async () => {
  fieldErrors.value = {}
  if (!cNumero.value || !cTypeContrat.value) {
    toast.add({
      title: 'Validation',
      description: 'Le numéro de contrat et le type sont obligatoires.',
      color: 'warning'
    })
    return
  }

  try {
    const payload = {
      numero_contrat: cNumero.value,
      poste_salaire_id: cPosteSalaireId.value ? Number(cPosteSalaireId.value) : null,
      type_contrat_travail: Number(cTypeContrat.value),
      statut_professionnel: Number(cStatutPro.value),
      salaire_mensuel: Number(cSalaireMensuel.value) || 0.0,
      salaire_horaire: Number(cSalaireHoraire.value) || 0.0,
      type_salaire: cTypeSalaire.value,
      mode_calcul: cModeCalcul.value,
      date_debut_contrat: cDateDebut.value || null,
      date_fin_previsionnelle_contrat: cDateFin.value || null,
      emploi: cEmploi.value || null,
      idcc: cIdcc.value ? Number(cIdcc.value) : null,
      unite_temps: cUniteTemTemps.value || cUniteTemps.value, // Wait, let's keep cUniteTemps
      sursalaire: Number(cSursalaire.value) || 0.0,
      indemnite_transport: Number(cIndemniteTransport.value) || 0.0,
      dotation_telephonique: Number(cDotationTelephonique.value) || 0.0,
      salarie_id: Number(salarieId),
      etablissement_id: Number(etabId)
    }
    // Note: let's use exact key from original payload
    payload.unite_temps = cUniteTemps.value

    const res = await post('/contrats', payload)
    if (res) {
      toast.add({
        title: 'Contrat créé',
        description: `Le contrat ${res.numero_contrat} a été créé avec succès.`,
        color: 'success'
      })
      router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}`)
    }
  } catch (e) {
    console.error(e)
    if (e.status === 422) {
      fieldErrors.value = extractFieldErrors(e)
    }
  }
}

onMounted(() => {
  fetchContextDetails()
})
</script>

<template>
  <div v-if="loadingContext" class="flex flex-col items-center justify-center py-20 space-y-4">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement du contexte...</span>
  </div>

  <div v-else class="max-w-2xl mx-auto space-y-6">
    <!-- Header Page -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-50 text-green-700 rounded-lg flex items-center justify-center font-bold text-xl border border-green-200">
          <UIcon name="i-lucide-file-text" class="w-6 h-6" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-900 leading-tight">Nouveau Contrat de Travail</h1>
          <p class="text-xs text-slate-500 mt-1">
            Employé : {{ currentSalarie?.prenom }} {{ currentSalarie?.nom?.toUpperCase() }} | Dossier : {{ currentDossier?.nom_dossier }}
          </p>
        </div>
      </div>
    </div>

    <!-- Main Form -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <form @submit.prevent="handleCreateContract" class="space-y-6">
        <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Paramètres du Contrat</h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Numéro de Contrat <span class="text-red-500">*</span></label>
            <input 
              v-model="cNumero" 
              type="text" 
              required
              placeholder="Ex: CD-DUPONT-01" 
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono focus:outline-none transition-colors',
                fieldErrors.numero_contrat ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.numero_contrat" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.numero_contrat }}</p>
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Poste (Grille Salariale)</label>
            <select 
              v-model="cPosteSalaireId"
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
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Poste / Emploi</label>
            <input 
              v-model="cEmploi" 
              type="text" 
              placeholder="Ex: Développeur Web" 
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm focus:outline-none transition-colors',
                fieldErrors.emploi ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.emploi" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.emploi }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Type de Contrat <span class="text-red-500">*</span></label>
            <select v-model="cTypeContrat" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500">
              <option :value="10">CDI (10)</option>
              <option :value="29">CDD (29)</option>
              <option :value="18">Contrat Apprentissage (18)</option>
              <option :value="28">Professionnalisation (28)</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Statut Cadre / Non-Cadre <span class="text-red-500">*</span></label>
            <select v-model="cStatutPro" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500">
              <option :value="1">Cadre (1)</option>
              <option :value="2">Non-Cadre (2)</option>
              <option :value="3">Ouvrier / Employé (3)</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Date de Début <span class="text-red-500">*</span></label>
            <input 
              v-model="cDateDebut" 
              type="date" 
              required 
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono focus:outline-none transition-colors',
                fieldErrors.date_debut_contrat ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.date_debut_contrat" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.date_debut_contrat }}</p>
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Date Fin (si CDD)</label>
            <input 
              v-model="cDateFin" 
              type="date" 
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono focus:outline-none transition-colors',
                fieldErrors.date_fin_previsionnelle_contrat ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.date_fin_previsionnelle_contrat" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.date_fin_previsionnelle_contrat }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 border-t border-slate-100 pt-4">
          <div class="md:col-span-1">
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">
              Salaire {{ cModeCalcul === 'net' ? 'Net' : 'Brut' }} (FCFA)
            </label>
            <div class="mt-1">
              <input
                v-if="cTypeSalaire === 'Mensuel'"
                v-model="cSalaireMensuel"
                type="number"
                step="0.01"
                placeholder="Mensuel"
                :class="[
                  'block w-full px-3 py-2 border rounded-lg text-sm font-mono focus:outline-none transition-colors',
                  fieldErrors.salaire_mensuel ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="cTypeSalaire === 'Mensuel' && fieldErrors.salaire_mensuel" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.salaire_mensuel }}</p>

              <input
                v-if="cTypeSalaire === 'Horaire'"
                v-model="cSalaireHoraire"
                type="number"
                step="0.01"
                placeholder="Horaire"
                :class="[
                  'block w-full px-3 py-2 border rounded-lg text-sm font-mono focus:outline-none transition-colors',
                  fieldErrors.salaire_horaire ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="cTypeSalaire === 'Horaire' && fieldErrors.salaire_horaire" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.salaire_horaire }}</p>
            </div>
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Type Salaire</label>
            <select v-model="cTypeSalaire" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500">
              <option value="Mensuel">Mensuel</option>
              <option value="Horaire">Horaire</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nature du salaire</label>
            <select v-model="cModeCalcul" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500">
              <option value="brut">Brut</option>
              <option value="net">Net</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 border-t border-slate-100 pt-4">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Unité de Temps</label>
            <select v-model="cUniteTemps" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500">
              <option value="Heures">Heures</option>
              <option value="Jours">Jours</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Sursalaire (FCFA)</label>
            <input 
              v-model="cSursalaire" 
              type="number" 
              step="0.01" 
              placeholder="0.00" 
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono focus:outline-none transition-colors',
                fieldErrors.sursalaire ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.sursalaire" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.sursalaire }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Indemnité de Transport (FCFA)</label>
            <input 
              v-model="cIndemniteTransport" 
              type="number" 
              step="0.01" 
              placeholder="0.00" 
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono focus:outline-none transition-colors',
                fieldErrors.indemnite_transport ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.indemnite_transport" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.indemnite_transport }}</p>
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Dotation Téléphonique (FCFA)</label>
            <input 
              v-model="cDotationTelephonique" 
              type="number" 
              step="0.01" 
              placeholder="0.00" 
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono focus:outline-none transition-colors',
                fieldErrors.dotation_telephonique ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.dotation_telephonique" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.dotation_telephonique }}</p>
          </div>
        </div>
        <div>
          <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">CCN (IDCC Convention Collective)</label>
          <input 
            v-model="cIdcc" 
            type="number" 
            placeholder="Ex: 1486" 
            :class="[
              'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono focus:outline-none transition-colors',
              fieldErrors.idcc ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
            ]"
          />
          <p v-if="fieldErrors.idcc" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.idcc }}</p>
        </div>

        <div class="flex justify-end space-x-3 pt-4 border-t border-slate-100">
          <NuxtLink 
            :to="`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}`" 
            class="px-4 py-2 border border-slate-200 text-sm font-semibold rounded-lg hover:bg-slate-50 text-slate-700 transition-colors"
          >
            Annuler
          </NuxtLink>
          <button 
            type="submit" 
            class="px-4 py-2 text-sm font-semibold bg-green-600 hover:bg-green-700 text-white rounded-lg shadow transition-colors"
          >
            Créer le contrat
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
