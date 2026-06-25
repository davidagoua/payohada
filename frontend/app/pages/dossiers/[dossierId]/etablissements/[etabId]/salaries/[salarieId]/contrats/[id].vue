<script setup>
const route = useRoute()
const router = useRouter()
const { get, put, delete: apiDelete } = useApi()
const toast = useToast()

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
const editStatut = ref('actif')
const editUniteTemps = ref('Heures')
const editSursalaire = ref(0.0)
const editIndemniteTransport = ref(0.0)
const editDotationTelephonique = ref(0.0)

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

    // Populate Editable Fields
    editEmploi.value = data.emploi || ''
    editTypeContrat.value = data.type_contrat_travail || 10
    editSalaireMensuel.value = data.salaire_mensuel || 0.0
    editSalaireHoraire.value = data.salaire_horaire || 0.0
    editTypeSalaire.value = data.type_salaire || 'Mensuel'
    editStatut.value = data.statut || 'actif'
    editUniteTemps.value = data.unite_temps || 'Heures'
    editSursalaire.value = data.sursalaire || 0.0
    editIndemniteTransport.value = data.indemnite_transport || 0.0
    editDotationTelephonique.value = data.dotation_telephonique || 0.0

    // Fetch bulletins
    const bList = await get(`/dossiers/${dossierId}/bulletins`, { query: { contrat_id: contratId } })
    bulletins.value = bList || []

  } catch (e) {
    console.error(e)
    router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}`)
  } finally {
    loading.value = false
  }
}

const handleUpdateContrat = async () => {
  try {
    const payload = {
      emploi: editEmploi.value || null,
      type_contrat_travail: Number(editTypeContrat.value),
      salaire_mensuel: Number(editSalaireMensuel.value) || 0.0,
      salaire_horaire: Number(editSalaireHoraire.value) || 0.0,
      type_salaire: editTypeSalaire.value,
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
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Intitulé de l'emploi (Poste)</label>
                <input v-model="editEmploi" type="text" placeholder="Ex: Développeur Senior" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
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

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 border-t border-slate-100 pt-4">
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Salaire Mensuel Brut (FCFA)</label>
                <input v-model="editSalaireMensuel" type="number" step="0.01" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Taux Horaire Brut (FCFA)</label>
                <input v-model="editSalaireHoraire" type="number" step="0.01" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
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
                <input v-model="editSursalaire" type="number" step="0.01" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Indemnité de Transport (FCFA)</label>
                <input v-model="editIndemniteTransport" type="number" step="0.01" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Dotation Téléphonique (FCFA)</label>
                <input v-model="editDotationTelephonique" type="number" step="0.01" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
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
  </div>
</template>
