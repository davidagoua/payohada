<script setup>
const route = useRoute()
const router = useRouter()
const { get, put, post, delete: apiDelete } = useApi()
const toast = useToast()

const dossierId = route.params.id
const dossier = ref(null)
const etablissements = ref([])
const loading = ref(true)
const activeTab = ref('infos')

// Global State for breadcrumbs
const currentDossier = useState('current-dossier')

// Edit Dossier Form
const editNom = ref('')
const editSiret = ref('')
const editEmail = ref('')
const editPhone = ref('')
const editContact = ref('')
const editQualite = ref(1)
const editAnnee = ref('')
const editPays = ref("Côte d'Ivoire")

// NetEntreprise Form
const neSiret = ref('')
const neNom = ref('')
const nePrenom = ref('')
const neEmail = ref('')
const nePhone = ref('')


const fetchDossierDetails = async () => {
  loading.value = true
  try {
    const data = await get(`/dossiers/${dossierId}`)
    dossier.value = data
    currentDossier.value = data // Update layout context
    
    // Pre-populate Edit Form
    editNom.value = data.nom_dossier || ''
    editSiret.value = data.siret || ''
    editEmail.value = data.adresse_email || ''
    editPhone.value = data.telephone || ''
    editContact.value = data.nom_contact || ''
    editQualite.value = data.qualite || 1
    editAnnee.value = data.annee || ''
    editPays.value = data.pays || "Côte d'Ivoire"

    // Pre-populate NetEntreprise Form
    if (data.net_entreprise) {
      neSiret.value = data.net_entreprise.siret || ''
      neNom.value = data.net_entreprise.nom || ''
      nePrenom.value = data.net_entreprise.prenom || ''
      neEmail.value = data.net_entreprise.email || ''
      nePhone.value = data.net_entreprise.telephone || ''
    } else {
      neSiret.value = data.siret || ''
    }

    // Fetch Etablissements
    const etabsData = await get(`/dossiers/${dossierId}/etablissements`)
    etablissements.value = etabsData || []

  } catch (e) {
    console.error(e)
    router.push('/dossiers')
  } finally {
    loading.value = false
  }
}

const handleUpdateDossier = async () => {
  try {
    const payload = {
      nom_dossier: editNom.value,
      siret: editSiret.value || null,
      adresse_email: editEmail.value || null,
      telephone: editPhone.value || null,
      nom_contact: editContact.value || null,
      pays: editPays.value || "Côte d'Ivoire"
    }

    const updated = await put(`/dossiers/${dossierId}`, payload)
    if (updated) {
      toast.add({
        title: 'Mis à jour',
        description: 'Les informations du dossier ont été enregistrées.',
        color: 'success'
      })
      dossier.value = updated
      currentDossier.value = updated
    }
  } catch (e) {
    console.error(e)
  }
}

const handleSaveNetEntreprise = async () => {
  if (!neSiret.value || !neNom.value || !nePrenom.value || !neEmail.value) {
    toast.add({
      title: 'Validation',
      description: 'Veuillez remplir tous les champs obligatoires pour NetEntreprise.',
      color: 'warning'
    })
    return
  }

  try {
    const payload = {
      siret: neSiret.value,
      nom: neNom.value,
      prenom: nePrenom.value,
      email: neEmail.value,
      telephone: nePhone.value || null
    }

    const res = await post(`/dossiers/${dossierId}/net-entreprise`, payload)
    if (res) {
      toast.add({
        title: 'Enregistré',
        description: 'Configuration NetEntreprise mise à jour.',
        color: 'success'
      })
      await fetchDossierDetails()
    }
  } catch (e) {
    console.error(e)
  }
}


const handleDeleteDossier = async () => {
  if (!confirm('Êtes-vous sûr de vouloir supprimer définitivement ce dossier et toutes ses données (établissements, salariés, contrats) ?')) {
    return
  }

  try {
    await apiDelete(`/dossiers/${dossierId}`)
    toast.add({
      title: 'Supprimé',
      description: 'Le dossier a été supprimé avec succès.',
      color: 'success'
    })
    currentDossier.value = null
    router.push('/dossiers')
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  fetchDossierDetails()
})
</script>

<template>
  <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement du dossier client...</span>
  </div>

  <div v-else-if="dossier" class="space-y-6">
    <!-- Header Object page -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-150 rounded-lg text-green-700 flex items-center justify-center font-bold text-xl">
          {{ dossier.code }}
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-900 leading-tight">{{ dossier.nom_dossier }}</h1>
          <p class="text-xs text-slate-500 font-mono mt-1">SIRET Principal : {{ dossier.siret || 'Non configuré' }}</p>
        </div>
      </div>
      
      <div class="flex space-x-3">
        <button 
          @click="handleDeleteDossier"
          class="px-4 py-2 border border-red-200 text-sm font-semibold rounded-lg hover:bg-red-50 text-red-600 transition-colors flex items-center gap-1.5"
        >
          <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
          Supprimer le Dossier
        </button>
      </div>
    </div>

    <!-- SAP Fiori Style Horizontal Tabs -->
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
          Informations Générales
        </button>
        <button 
          @click="activeTab = 'etabs'"
          :class="[
            activeTab === 'etabs' 
              ? 'border-green-600 text-green-700 font-bold' 
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all'
          ]"
        >
          Établissements ({{ etablissements.length }})
        </button>
        <button 
          @click="activeTab = 'net'"
          :class="[
            activeTab === 'net' 
              ? 'border-green-600 text-green-700 font-bold' 
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all'
          ]"
        >
          NetEntreprise (DSN)
        </button>
      </nav>
    </div>

    <!-- Tab 1: Informations -->
    <div v-show="activeTab === 'infos'" class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <form @submit.prevent="handleUpdateDossier" class="space-y-6">
        <h3 class="text-lg font-bold text-slate-900 border-b border-slate-100 pb-2">Modifier le profil de l'entreprise</h3>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom du Dossier / Entreprise</label>
            <input 
              v-model="editNom" 
              type="text" 
              required
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
            />
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">SIRET Principal</label>
            <input 
              v-model="editSiret" 
              type="text" 
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm font-mono"
            />
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Pays de Référence</label>
            <input 
              v-model="editPays" 
              type="text" 
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
            />
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom du Contact RH</label>
            <input 
              v-model="editContact" 
              type="text" 
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
            />
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Adresse Email</label>
            <input 
              v-model="editEmail" 
              type="email" 
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
            />
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Téléphone</label>
            <input 
              v-model="editPhone" 
              type="text" 
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
            />
          </div>
        </div>

        <div class="flex justify-end pt-4 border-t border-slate-100">
          <button 
            type="submit" 
            class="px-4 py-2 text-sm font-semibold bg-green-600 hover:bg-green-700 text-white rounded-lg shadow transition-colors"
          >
            Enregistrer les modifications
          </button>
        </div>
      </form>
    </div>

    <!-- Tab 2: Établissements -->
    <div v-show="activeTab === 'etabs'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">Établissements Rattachés</h3>
            <p class="text-xs text-slate-500">Liste des filiales, sièges ou entités physiques déclarées pour DSN.</p>
          </div>
          <button 
            @click="router.push(`/dossiers/${dossierId}/etablissements/new`)"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-plus" class="w-3.5 h-3.5" />
            Créer un établissement
          </button>
        </div>

        <!-- Table list or Empty state -->
        <div v-if="etablissements.length === 0" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun établissement créé pour le moment.
        </div>
        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Code</th>
                <th scope="col" class="px-6 py-3 text-left">Raison Sociale</th>
                <th scope="col" class="px-6 py-3 text-left">Matricule CNPS</th>
                <th scope="col" class="px-6 py-3 text-left">N° Contribuable (DGI)</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr 
                v-for="etab in etablissements" 
                :key="etab.id" 
                @click="router.push(`/dossiers/${dossierId}/etablissements/${etab.id}`)"
                class="hover:bg-slate-50 cursor-pointer group"
              >
                <td class="px-6 py-4 font-mono font-semibold text-slate-900">{{ etab.code }}</td>
                <td class="px-6 py-4 font-medium text-slate-700 group-hover:text-green-700 transition-colors">{{ etab.raison_sociale }}</td>
                <td class="px-6 py-4 font-mono text-slate-500">{{ etab.cnps_matricule || '-' }}</td>
                <td class="px-6 py-4 font-mono text-slate-500">{{ etab.dgi_compte_contribuable || '-' }}</td>
                <td class="px-6 py-4 text-right">
                  <span class="text-green-600 group-hover:underline text-xs font-semibold flex items-center justify-end gap-1">
                    Gérer
                    <UIcon name="i-lucide-chevron-right" class="w-4 h-4" />
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Tab 3: NetEntreprise -->
    <div v-show="activeTab === 'net'" class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <form @submit.prevent="handleSaveNetEntreprise" class="space-y-6">
        <div>
          <h3 class="text-lg font-bold text-slate-900">Configuration NetEntreprise</h3>
          <p class="text-xs text-slate-500 mt-1">Ces coordonnées sont utilisées pour signer les dépôts DSN.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 border-t border-slate-100 pt-4">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">SIRET NetEntreprise <span class="text-red-500">*</span></label>
            <input 
              v-model="neSiret" 
              type="text" 
              required
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm font-mono"
            />
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom du déclarant <span class="text-red-500">*</span></label>
            <input 
              v-model="neNom" 
              type="text" 
              required
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
            />
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Prénom <span class="text-red-500">*</span></label>
            <input 
              v-model="nePrenom" 
              type="text" 
              required
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
            />
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Adresse Email <span class="text-red-500">*</span></label>
            <input 
              v-model="neEmail" 
              type="email" 
              required
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
            />
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Téléphone</label>
            <input 
              v-model="nePhone" 
              type="text" 
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
            />
          </div>
        </div>

        <div class="flex justify-end pt-4 border-t border-slate-100">
          <button 
            type="submit" 
            class="px-4 py-2 text-sm font-semibold bg-green-600 hover:bg-green-700 text-white rounded-lg shadow transition-colors"
          >
            Enregistrer NetEntreprise
          </button>
        </div>
      </form>
    </div>


  </div>
</template>
