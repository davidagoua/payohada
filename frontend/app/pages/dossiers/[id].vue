<script setup>
const route = useRoute()
const router = useRouter()
const { get, put, post, delete: apiDelete } = useApi()
const toast = useToast()

const dossierId = route.params.id
const dossier = ref(null)
const etablissements = ref([])
const selectedEtabs = ref([])
const loading = ref(true)
const activeTab = ref('etabs')

const allEtabsSelected = computed({
  get: () => etablissements.value.length > 0 && selectedEtabs.value.length === etablissements.value.length,
  set: (val) => {
    if (val) {
      selectedEtabs.value = etablissements.value.map(e => e.id)
    } else {
      selectedEtabs.value = []
    }
  }
})

const handleBulkDeleteEtabs = async () => {
  if (selectedEtabs.value.length === 0) return
  if (!confirm(`Voulez-vous vraiment supprimer les ${selectedEtabs.value.length} établissements sélectionnés ainsi que toutes leurs données associées ?`)) return
  
  loading.value = true
  try {
    let successCount = 0
    for (const etabId of selectedEtabs.value) {
      try {
        await apiDelete(`/etablissements/${etabId}`)
        successCount++
      } catch (e) {
        console.error(`Erreur de suppression de l'établissement ${etabId}:`, e)
      }
    }
    toast.add({
      title: 'Suppression terminée',
      description: `${successCount} établissement(s) supprimé(s) avec succès.`,
      color: 'success'
    })
    selectedEtabs.value = []
    await fetchDossierDetails()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

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

    
    <!-- SAP Fiori Style Horizontal Tabs -->
    <div class="border-b-2 border-slate-200">
      <nav class="flex space-x-8" aria-label="Tabs">
        
        <button 
          @click="activeTab = 'etabs'"
          :class="[
            activeTab === 'etabs' 
              ? 'border-green-600 text-green-700 font-bold bg-green-50/20' 
              : 'border-transparent text-slate-500 hover:text-slate-750 hover:bg-slate-50',
            'whitespace-nowrap py-4 px-3 border-b-2 font-bold text-xs uppercase tracking-wider transition-all'
          ]"
        >
          Établissements ({{ etablissements.length }})
        </button>
        <button 
          @click="activeTab = 'net'"
          :class="[
            activeTab === 'net' 
              ? 'border-green-600 text-green-700 font-bold bg-green-50/20' 
              : 'border-transparent text-slate-500 hover:text-slate-750 hover:bg-slate-50',
            'whitespace-nowrap py-4 px-3 border-b-2 font-bold text-xs uppercase tracking-wider transition-all'
          ]"
        >
          NetEntreprise (DSN)
        </button>
        <button 
          @click="activeTab = 'infos'"
          :class="[
            activeTab === 'infos' 
              ? 'border-green-600 text-green-700 font-bold bg-green-50/20' 
              : 'border-transparent text-slate-500 hover:text-slate-750 hover:bg-slate-50',
            'whitespace-nowrap py-4 px-3 border-b-2 font-bold text-xs uppercase tracking-wider transition-all'
          ]"
        >
          Informations Générales
        </button>

      </nav>
    </div>

    <!-- Tab 1: Informations -->
    <div v-show="activeTab === 'infos'" class="bg-white border-2 border-slate-200 p-6 shadow-flat border-t-4 border-t-slate-500">
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
      <div class="bg-white border-2 border-slate-200 p-6 shadow-flat border-t-4 border-t-slate-500">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">Établissements Rattachés</h3>
            <p class="text-xs text-slate-500">Liste des filiales, sièges ou entités physiques déclarées pour DSN.</p>
          </div>
          <button 
            @click="router.push(`/dossiers/${dossierId}/etablissements/new`)"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-1.5 shadow-flat cursor-pointer"
          >
            <UIcon name="i-lucide-plus" class="w-3.5 h-3.5" />
            Créer un établissement
          </button>
        </div>

        <!-- Bulk Actions Bar -->
        <div v-if="selectedEtabs.length > 0" class="bg-slate-100 border border-slate-350 p-3 mb-4 flex items-center justify-between text-xs transition-all animate-fade-in">
          <div class="font-bold text-slate-700">
            {{ selectedEtabs.length }} établissement(s) sélectionné(s)
          </div>
          <div class="flex items-center space-x-2">
            <button 
              @click="handleBulkDeleteEtabs"
              class="p-1.5 bg-red-650 hover:bg-red-755 text-white transition-colors shadow-flat cursor-pointer flex items-center justify-center"
              title="Supprimer la sélection"
            >
              <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Table list or Empty state -->
        <div v-if="etablissements.length === 0" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun établissement créé pour le moment.
        </div>
        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left w-10">
                  <input type="checkbox" v-model="allEtabsSelected" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </th>
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
                <td class="px-4 py-4" @click.stop>
                  <input type="checkbox" :value="etab.id" v-model="selectedEtabs" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </td>
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
    <div v-show="activeTab === 'net'" class="bg-white border-2 border-slate-200 p-6 shadow-flat border-t-4 border-t-slate-500">
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
