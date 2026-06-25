<script setup>
const { get, post, put, delete: apiDelete } = useApi()
const toast = useToast()

definePageMeta({
  layout: 'default'
})

const planItems = ref([])
const loading = ref(false)
const countryFilter = ref('CI')

const showModal = ref(false)
const isEditing = ref(false)
const currentId = ref(null)

const form = ref({
  type: 'B',
  code: '',
  libelle: '',
  mode_calcul: 'Sémi-auto',
  sens: 'Gain',
  masque_si_nul: false,
  imprimable: true,
  compte_debit: '',
  compte_credit: '',
  pays: 'CI',
  est_actif: true
})

const fetchPlanItems = async () => {
  loading.value = true
  try {
    const res = await get(`/plan-paie?pays=${countryFilter.value}`)
    planItems.value = res || []
  } catch (e) {
    console.error('Error fetching plan items:', e)
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  isEditing.value = false
  currentId.value = null
  form.value = {
    type: 'B',
    code: '',
    libelle: '',
    mode_calcul: 'Sémi-auto',
    sens: 'Gain',
    masque_si_nul: false,
    imprimable: true,
    compte_debit: '',
    compte_credit: '',
    pays: countryFilter.value || 'CI',
    est_actif: true
  }
  showModal.value = true
}

const openEditModal = (item) => {
  isEditing.value = true
  currentId.value = item.id
  form.value = { ...item }
  showModal.value = true
}

const handleSubmit = async () => {
  try {
    if (isEditing.value) {
      await put(`/plan-paie/${currentId.value}`, form.value)
      toast.add({ title: 'Succès', description: 'Poste de paie mis à jour avec succès.', color: 'success' })
    } else {
      await post('/plan-paie', form.value)
      toast.add({ title: 'Succès', description: 'Poste de paie créé avec succès.', color: 'success' })
    }
    showModal.value = false
    fetchPlanItems()
  } catch (e) {
    console.error('Error submitting form:', e)
  }
}

const handleDelete = async (id) => {
  if (!confirm('Êtes-vous sûr de vouloir supprimer ce poste de paie ?')) return
  try {
    await apiDelete(`/plan-paie/${id}`)
    toast.add({ title: 'Succès', description: 'Poste de paie supprimé avec succès.', color: 'success' })
    fetchPlanItems()
  } catch (e) {
    console.error('Error deleting plan item:', e)
  }
}

const getPosteTypeLabel = (type) => {
  const types = {
    'B': 'Brut',
    'I': 'Impôt/Cotisation',
    'NS': 'Non-Salarial',
    'C': 'Patronal',
    'A': 'Avantage'
  }
  return types[type] || type
}

onMounted(() => {
  fetchPlanItems()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header Page -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-50 text-green-700 rounded-lg flex items-center justify-center font-bold text-xl border border-green-200">
          <UIcon name="i-lucide-book-open" class="w-6 h-6" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-900 leading-tight">Plan Comptable de Paie</h1>
          <p class="text-xs text-slate-500 mt-1">Gérez le plan des rubriques, leurs règles et leur imputation comptable.</p>
        </div>
      </div>
      
      <button 
        @click="openCreateModal"
        class="w-full md:w-auto px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2"
      >
        <UIcon name="i-lucide-plus" class="w-4 h-4" />
        <span>Nouveau Poste de Paie</span>
      </button>
    </div>

    <!-- Filters Section -->
    <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
      <div class="flex items-center space-x-2">
        <label class="text-xs font-bold text-slate-500 uppercase tracking-wider">Filtrer par Pays :</label>
        <select 
          v-model="countryFilter" 
          @change="fetchPlanItems"
          class="block w-40 px-3 py-1.5 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          <option value="CI">Côte d'Ivoire (CI)</option>
          <option value="SN">Sénégal (SN)</option>
          <option value="BF">Burkina Faso (BF)</option>
          <option value="ML">Mali (ML)</option>
        </select>
      </div>
      
      <div class="text-xs text-slate-450 italic">
        Le paramétrage du plan de paie détermine l'ordre, l'imprimabilité et la comptabilisation des bulletins de salaire.
      </div>
    </div>

    <!-- Content Table -->
    <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      <div v-if="loading" class="p-16 text-center space-y-4 flex flex-col items-center justify-center">
        <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
        <span class="text-sm font-semibold text-slate-650">Chargement du plan de paie...</span>
      </div>
      
      <div v-else-if="planItems.length === 0" class="p-16 text-center text-slate-500 italic text-sm">
        Aucun poste de paie configuré pour ce pays. Cliquez sur "Nouveau Poste" pour commencer.
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
          <thead class="bg-slate-50 text-slate-600 font-bold text-xs uppercase tracking-wider">
            <tr>
              <th scope="col" class="px-6 py-3.5 text-left">Code</th>
              <th scope="col" class="px-6 py-3.5 text-left">Type</th>
              <th scope="col" class="px-6 py-3.5 text-left">Libellé</th>
              <th scope="col" class="px-6 py-3.5 text-left">Calcul</th>
              <th scope="col" class="px-6 py-3.5 text-center">Sens</th>
              <th scope="col" class="px-6 py-3.5 text-center">Débit / Crédit</th>
              <th scope="col" class="px-6 py-3.5 text-center">Statut</th>
              <th scope="col" class="px-6 py-3.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-150 text-slate-700">
            <tr v-for="item in planItems" :key="item.id" class="hover:bg-slate-50 transition-colors">
              <td class="px-6 py-4 font-mono font-bold text-slate-900 text-xs">{{ item.code }}</td>
              <td class="px-6 py-4">
                <span class="px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-650 text-[10px] font-semibold">
                  {{ getPosteTypeLabel(item.type) }}
                </span>
              </td>
              <td class="px-6 py-4 text-xs font-semibold">{{ item.libelle }}</td>
              <td class="px-6 py-4 text-xs text-slate-500">{{ item.mode_calcul }}</td>
              <td class="px-6 py-4 text-center">
                <span 
                  :class="item.sens === 'Gain' ? 'text-green-700 font-semibold' : 'text-red-600 font-semibold'"
                  class="text-xs"
                >
                  {{ item.sens }}
                </span>
              </td>
              <td class="px-6 py-4 text-center font-mono text-xs text-slate-500">
                {{ item.compte_debit || '-' }} / {{ item.compte_credit || '-' }}
              </td>
              <td class="px-6 py-4 text-center">
                <span 
                  :class="item.est_actif ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'"
                  class="px-2 py-0.5 rounded-full text-[10px] font-bold border"
                >
                  {{ item.est_actif ? 'Actif' : 'Inactif' }}
                </span>
              </td>
              <td class="px-6 py-4 text-right text-xs font-medium space-x-2">
                <button 
                  @click="openEditModal(item)"
                  class="text-green-600 hover:text-green-800 hover:bg-green-50 p-1.5 rounded transition-colors"
                >
                  <UIcon name="i-lucide-pencil" class="w-4 h-4" />
                </button>
                <button 
                  @click="handleDelete(item.id)"
                  class="text-red-500 hover:text-red-750 hover:bg-red-50 p-1.5 rounded transition-colors"
                >
                  <UIcon name="i-lucide-trash" class="w-4 h-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal Form (Tailwind UI Custom Modal) -->
    <div v-if="showModal" class="fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full overflow-hidden animate-fade-in-up">
        
        <!-- Modal Header -->
        <div class="px-6 py-4 bg-slate-50 border-b border-slate-150 flex justify-between items-center">
          <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider">
            {{ isEditing ? 'Modifier le Poste de Paie' : 'Créer un Poste de Paie' }}
          </h3>
          <button @click="showModal = false" class="text-slate-400 hover:text-slate-600">
            <UIcon name="i-lucide-x" class="w-5 h-5" />
          </button>
        </div>

        <!-- Form fields -->
        <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Unique</label>
              <input 
                v-model="form.code" 
                type="text" 
                required 
                placeholder="ex: 1001"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-green-500" 
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Pays de référence</label>
              <select 
                v-model="form.pays" 
                required
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                <option value="CI">Côte d'Ivoire (CI)</option>
                <option value="SN">Sénégal (SN)</option>
                <option value="BF">Burkina Faso (BF)</option>
                <option value="ML">Mali (ML)</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Type de Poste</label>
              <select 
                v-model="form.type" 
                required
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                <option value="B">Brut (B)</option>
                <option value="I">Impôt/Cotisation (I)</option>
                <option value="NS">Non-Salarial (NS)</option>
                <option value="C">Patronal (C)</option>
                <option value="A">Avantage (A)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Sens</label>
              <select 
                v-model="form.sens" 
                required
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                <option value="Gain">Gain</option>
                <option value="Retenue">Retenue</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Libellé</label>
            <input 
              v-model="form.libelle" 
              type="text" 
              required 
              placeholder="ex: Salaire de base"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500" 
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Mode de Calcul</label>
              <select 
                v-model="form.mode_calcul" 
                required
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                <option value="Auto">Auto</option>
                <option value="Sémi-auto">Sémi-auto</option>
                <option value="Manuel">Manuel</option>
              </select>
            </div>
            <div class="flex items-center space-x-4 mt-6">
              <label class="flex items-center space-x-1.5 text-xs font-semibold text-slate-700 select-none">
                <input v-model="form.masque_si_nul" type="checkbox" class="h-4 w-4 text-green-600 focus:ring-green-500 border-slate-300 rounded" />
                <span>Masquer si nul</span>
              </label>
              <label class="flex items-center space-x-1.5 text-xs font-semibold text-slate-700 select-none">
                <input v-model="form.imprimable" type="checkbox" class="h-4 w-4 text-green-600 focus:ring-green-500 border-slate-300 rounded" />
                <span>Imprimable</span>
              </label>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Compte Débit</label>
              <input 
                v-model="form.compte_debit" 
                type="text" 
                placeholder="ex: 661200"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-green-500" 
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Compte Crédit</label>
              <input 
                v-model="form.compte_credit" 
                type="text" 
                placeholder="ex: 447210"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-green-500" 
              />
            </div>
          </div>

          <div class="flex items-center space-x-2 pt-2">
            <input 
              v-model="form.est_actif" 
              id="est_actif"
              type="checkbox" 
              class="h-4 w-4 text-green-600 focus:ring-green-500 border-slate-300 rounded" 
            />
            <label for="est_actif" class="text-xs font-semibold text-slate-700 select-none">Ce poste est actif</label>
          </div>

          <!-- Actions -->
          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-150">
            <button 
              type="button" 
              @click="showModal = false"
              class="px-4 py-2 border border-slate-200 rounded-lg text-slate-700 hover:bg-slate-50 text-sm font-semibold"
            >
              Annuler
            </button>
            <button 
              type="submit" 
              class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-semibold shadow-sm"
            >
              Sauvegarder
            </button>
          </div>
        </form>

      </div>
    </div>
  </div>
</template>
