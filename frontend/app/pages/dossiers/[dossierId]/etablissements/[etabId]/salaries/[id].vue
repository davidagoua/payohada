<script setup>
const route = useRoute()
const router = useRouter()
const { get, put, post, delete: apiDelete } = useApi()
const toast = useToast()

const dossierId = route.params.dossierId
const etabId = route.params.etabId
const salarieId = route.params.id

const sal = ref(null)
const contrats = ref([])
const loading = ref(true)
const activeTab = ref('infos')

// Global State for breadcrumbs
const currentDossier = useState('current-dossier')

// Salarie Edit Form Fields
const salMatricule = ref('')
const salNom = ref('')
const salPrenom = ref('')
const salNomUsage = ref('')
const salCivilite = ref('M.')
const salDateNaissance = ref('')
const salLieuNaissance = ref('')
const salDeptNaissance = ref('')
const salPaysNaissance = ref('')
const salNationalite = ref('')
const salNir = ref('')
const salAdresse = ref('')
const salAdresse2 = ref('')
const salCodePostal = ref('')
const salVille = ref('')
const salPays = ref('France')
const salEmail = ref('')
const salPhone = ref('')
const salIban = ref('')
const salBic = ref('')
const salIsActive = ref(true)
const salExpatrie = ref(false)


const fetchSalarieDetails = async () => {
  loading.value = true
  try {
    // Ensure parent dossier context is loaded
    if (!currentDossier.value) {
      const parentDossier = await get(`/dossiers/${dossierId}`)
      currentDossier.value = parentDossier
    }

    const data = await get(`/salaries/${salarieId}`)
    sal.value = data

    // Populate Fields
    salMatricule.value = data.matricule || ''
    salNom.value = data.nom || ''
    salPrenom.value = data.prenom || ''
    salNomUsage.value = data.nom_usage || ''
    salCivilite.value = data.civilite || 'M.'
    
    if (data.date_naissance) {
      salDateNaissance.value = data.date_naissance.substring(0, 10)
    } else {
      salDateNaissance.value = ''
    }
    
    salLieuNaissance.value = data.lieu_naissance || ''
    salDeptNaissance.value = data.departement_naissance || ''
    salPaysNaissance.value = data.pays_naissance || ''
    salNationalite.value = data.nationalite || ''
    salNir.value = data.numero_securite_sociale || ''
    salAdresse.value = data.adresse || ''
    salAdresse2.value = data.adresse2 || ''
    salCodePostal.value = data.code_postal || ''
    salVille.value = data.ville || ''
    salPays.value = data.pays || 'France'
    salEmail.value = data.email || ''
    salPhone.value = data.telephone || ''
    salIban.value = data.iban || ''
    salBic.value = data.bic || ''
    salIsActive.value = data.is_active ?? true
    salExpatrie.value = data.expatrie ?? false

    // Fetch Contracts
    const cts = await get(`/salaries/${salarieId}/contrats`)
    contrats.value = cts || []

  } catch (e) {
    console.error(e)
    router.push(`/dossiers/${dossierId}/etablissements/${etabId}`)
  } finally {
    loading.value = false
  }
}

const handleUpdateSalarie = async () => {
  if (!salNom.value || !salPrenom.value) {
    toast.add({
      title: 'Validation',
      description: 'Le nom et le prénom du salarié sont obligatoires.',
      color: 'warning'
    })
    return
  }

  try {
    const payload = {
      nom: salNom.value,
      prenom: salPrenom.value,
      nom_usage: salNomUsage.value || null,
      civilite: salCivilite.value,
      date_naissance: salDateNaissance.value ? new Date(salDateNaissance.value).toISOString() : null,
      lieu_naissance: salLieuNaissance.value || null,
      departement_naissance: salDeptNaissance.value || null,
      pays_naissance: salPaysNaissance.value || null,
      nationalite: salNationalite.value || null,
      numero_securite_sociale: salNir.value || null,
      adresse: salAdresse.value || null,
      adresse2: salAdresse2.value || null,
      code_postal: salCodePostal.value || null,
      ville: salVille.value || null,
      pays: salPays.value || 'France',
      email: salEmail.value || null,
      telephone: salPhone.value || null,
      iban: salIban.value || null,
      bic: salBic.value || null,
      is_active: salIsActive.value,
      expatrie: salExpatrie.value
    }

    const res = await put(`/salaries/${salarieId}`, payload)
    if (res) {
      toast.add({
        title: 'Mis à jour',
        description: 'Fiche du salarié enregistrée avec succès.',
        color: 'success'
      })
      await fetchSalarieDetails()
    }
  } catch (e) {
    console.error(e)
  }
}


const handleDeleteSalarie = async () => {
  if (!confirm('Supprimer définitivement ce salarié et tous ses contrats associés ?')) return
  try {
    await apiDelete(`/salaries/${salarieId}`)
    toast.add({
      title: 'Salarié supprimé',
      description: 'La fiche salarié a été supprimée.',
      color: 'success'
    })
    router.push(`/dossiers/${dossierId}/etablissements/${etabId}`)
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  fetchSalarieDetails()
})
</script>

<template>
  <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement du salarié...</span>
  </div>

  <div v-else-if="sal" class="space-y-6">
    <!-- Header Object page -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-50 text-green-700 rounded-full flex items-center justify-center font-bold text-lg border border-green-200">
          {{ sal.prenom[0] }}{{ sal.nom[0] }}
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-900 leading-tight">
            {{ sal.civilite }} {{ sal.prenom }} {{ sal.nom.toUpperCase() }}
          </h1>
          <p class="text-xs text-slate-500 font-mono mt-1">Matricule : {{ sal.matricule }}</p>
        </div>
      </div>
      
      <div class="flex space-x-3">
        <button 
          @click="handleDeleteSalarie"
          class="px-4 py-2 border border-red-200 text-sm font-semibold rounded-lg hover:bg-red-50 text-red-600 transition-colors flex items-center gap-1.5"
        >
          <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
          Supprimer la Fiche
        </button>
      </div>
    </div>

    <!-- SAP Fiori Tabs -->
    <div class="border-b border-slate-200">
      <nav class="flex space-x-8" aria-label="Tabs">
        <button 
          @click="activeTab = 'infos'"
          :class="[
            activeTab === 'infos' 
              ? 'border-green-600 text-green-700 font-bold' 
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all'
          ]"
        >
          Fiche Salarié / État Civil
        </button>
        <button 
          @click="activeTab = 'contrats'"
          :class="[
            activeTab === 'contrats' 
              ? 'border-green-600 text-green-700 font-bold' 
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all'
          ]"
        >
          Contrats de Travail ({{ contrats.length }})
        </button>
      </nav>
    </div>

    <!-- Tab 1: Fiche Salarié -->
    <div v-show="activeTab === 'infos'" class="space-y-6">
      <form @submit.prevent="handleUpdateSalarie" class="space-y-6">
        
        <!-- Civil Profile -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">État Civil & Informations Générales</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Civilité</label>
              <select v-model="salCivilite" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="M.">Monsieur (M.)</option>
                <option value="MME">Madame (Mme)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Matricule Interne</label>
              <input v-model="salMatricule" type="text" disabled class="mt-1 block w-full px-3 py-2 border border-slate-200 bg-slate-50 rounded-lg text-sm font-mono text-slate-500 cursor-not-allowed" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Prénom</label>
              <input v-model="salPrenom" type="text" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom de famille</label>
              <input v-model="salNom" type="text" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom d'Usage (Optionnel)</label>
              <input v-model="salNomUsage" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">N° Sécurité Sociale (NIR)</label>
              <input v-model="salNir" type="text" placeholder="15 chiffres" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nationalité</label>
              <input v-model="salNationalite" type="text" placeholder="Ex: Française" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Régime Expatrié</label>
              <select v-model="salExpatrie" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option :value="false">Non (Local)</option>
                <option :value="true">Oui (Expatrié)</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Date de Naissance</label>
              <input v-model="salDateNaissance" type="date" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Lieu de Naissance</label>
              <input v-model="salLieuNaissance" type="text" placeholder="Ex: Lyon" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Département Naissance</label>
              <input v-model="salDeptNaissance" type="text" placeholder="Ex: 69" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Pays Naissance</label>
              <input v-model="salPaysNaissance" type="text" placeholder="Ex: France" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
        </div>

        <!-- Coordonnees -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Coordonnées de Contact & Adresse</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Email Personnel</label>
              <input v-model="salEmail" type="email" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Téléphone</label>
              <input v-model="salPhone" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="md:col-span-2">
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Adresse postale</label>
              <input v-model="salAdresse" type="text" placeholder="Voie et rue" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Adresse Complémentaire</label>
              <input v-model="salAdresse2" type="text" placeholder="Escalier, appartement..." class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Postal</label>
              <input v-model="salCodePostal" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Ville</label>
              <input v-model="salVille" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Pays</label>
              <input v-model="salPays" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
        </div>

        <!-- Banque -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Informations Bancaires de Versement</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">IBAN du salarié</label>
              <input v-model="salIban" type="text" placeholder="FR76..." class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">BIC du salarié</label>
              <input v-model="salBic" type="text" placeholder="Ex: CEIDFRPP..." class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
          </div>
        </div>

        <div class="flex justify-end space-x-3">
          <div class="flex items-center space-x-2 mr-4">
            <input id="sal-active" v-model="salIsActive" type="checkbox" class="rounded border-slate-300 text-green-600 focus:ring-green-500 h-4 w-4" />
            <label for="sal-active" class="text-sm font-semibold text-slate-700">Fiche active</label>
          </div>
          <button type="submit" class="px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow transition-colors">
            Enregistrer les modifications
          </button>
        </div>
      </form>
    </div>

    <!-- Tab 2: Contrats -->
    <div v-show="activeTab === 'contrats'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">Historique des Contrats</h3>
            <p class="text-xs text-slate-500">Liste des contrats de travail (actifs et échus) de cet employé.</p>
          </div>
          <button 
            @click="router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/new`)"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouveau Contrat
          </button>
        </div>

        <!-- Contracts Table -->
        <div v-if="contrats.length === 0" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun contrat créé pour ce salarié.
        </div>
        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">N° Contrat</th>
                <th scope="col" class="px-6 py-3 text-left">Poste / Emploi</th>
                <th scope="col" class="px-6 py-3 text-left">Type Contrat</th>
                <th scope="col" class="px-6 py-3 text-left">Rémunération</th>
                <th scope="col" class="px-6 py-3 text-left">Date Début</th>
                <th scope="col" class="px-6 py-3 text-left">Statut</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr 
                v-for="c in contrats" 
                :key="c.id" 
                @click="router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/${c.id}`)"
                class="hover:bg-slate-50 cursor-pointer group"
              >
                <td class="px-6 py-4 font-mono font-semibold text-slate-900">{{ c.numero_contrat }}</td>
                <td class="px-6 py-4 font-medium text-slate-700 group-hover:text-green-700 transition-colors">
                  {{ c.emploi || 'Non renseigné' }}
                </td>
                <td class="px-6 py-4 text-slate-600 font-semibold">
                  {{ c.type_contrat_travail === 10 ? 'CDI' : c.type_contrat_travail === 29 ? 'CDD' : 'Autre (code ' + c.type_contrat_travail + ')' }}
                </td>
                <td class="px-6 py-4 font-mono text-slate-600">
                  {{ c.salaire_mensuel }} FCFA / {{ c.type_salaire }}
                </td>
                <td class="px-6 py-4 font-mono text-slate-500">{{ c.date_debut_contrat || '-' }}</td>
                <td class="px-6 py-4">
                  <span 
                    :class="[
                      c.statut === 'actif' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-slate-150 text-slate-500 border-slate-200',
                      'px-2 py-0.5 rounded text-[10px] uppercase font-bold border'
                    ]"
                  >
                    {{ c.statut }}
                  </span>
                </td>
                <td class="px-6 py-4 text-right">
                  <span class="text-green-600 group-hover:underline text-xs font-semibold flex items-center justify-end gap-1">
                    Gérer le Contrat
                    <UIcon name="i-lucide-chevron-right" class="w-4 h-4" />
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>
    </div>


  </div>
</template>
