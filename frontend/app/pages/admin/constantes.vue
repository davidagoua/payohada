<script setup>
const { get, post, put, delete: apiDelete } = useApi()
const toast = useToast()

definePageMeta({
  layout: 'default'
})

const constantes = ref([])
const loading = ref(false)
const countryFilter = ref('CI')

const showModal = ref(false)
const isEditing = ref(false)
const currentId = ref(null)

const form = ref({
  code: '',
  description: '',
  montant: 0.0,
  unite: '',
  pays: 'CI',
  est_actif: true
})

const fetchConstantes = async () => {
  loading.value = true
  try {
    const res = await get(`/constantes?pays=${countryFilter.value}`)
    constantes.value = res || []
  } catch (e) {
    console.error('Error fetching constantes:', e)
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  isEditing.value = false
  currentId.value = null
  form.value = {
    code: '',
    description: '',
    montant: 0.0,
    unite: 'FCFA',
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
      await put(`/constantes/${currentId.value}`, form.value)
      toast.add({ title: 'Succès', description: 'Constante mise à jour avec succès.', color: 'success' })
    } else {
      await post('/constantes', form.value)
      toast.add({ title: 'Succès', description: 'Constante créée avec succès.', color: 'success' })
    }
    showModal.value = false
    fetchConstantes()
  } catch (e) {
    console.error('Error submitting form:', e)
  }
}

const handleDelete = async (id) => {
  if (!confirm('Êtes-vous sûr de vouloir supprimer cette constante ?')) return
  try {
    await apiDelete(`/constantes/${id}`)
    toast.add({ title: 'Succès', description: 'Constante supprimée avec succès.', color: 'success' })
    fetchConstantes()
  } catch (e) {
    console.error('Error deleting constante:', e)
  }
}

onMounted(() => {
  fetchConstantes()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header Page -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-50 text-green-700 rounded-lg flex items-center justify-center font-bold text-xl border border-green-200">
          <UIcon name="i-lucide-sliders" class="w-6 h-6" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-900 leading-tight">Constantes de Paie</h1>
          <p class="text-xs text-slate-500 mt-1">Configurez les taux et les plafonds de paie utilisés dans les calculs de cotisations.</p>
        </div>
      </div>
      
      <button 
        @click="openCreateModal"
        class="w-full md:w-auto px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2"
      >
        <UIcon name="i-lucide-plus" class="w-4 h-4" />
        <span>Nouvelle Constante</span>
      </button>
    </div>

    <!-- Filters Section -->
    <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
      <div class="flex items-center space-x-2">
        <label class="text-xs font-bold text-slate-500 uppercase tracking-wider">Filtrer par Pays :</label>
        <select 
          v-model="countryFilter" 
          @change="fetchConstantes"
          class="block w-40 px-3 py-1.5 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          <option value="CI">Côte d'Ivoire (CI)</option>
          <option value="SN">Sénégal (SN)</option>
          <option value="BF">Burkina Faso (BF)</option>
          <option value="ML">Mali (ML)</option>
        </select>
      </div>
      
      <div class="text-xs text-slate-450 italic">
        Toutes les constantes listées ci-dessous s'appliquent aux cotisations et calculs associés.
      </div>
    </div>

    <!-- Content Table -->
    <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      <div v-if="loading" class="p-16 text-center space-y-4 flex flex-col items-center justify-center">
        <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
        <span class="text-sm font-semibold text-slate-650">Chargement des constantes...</span>
      </div>
      
      <div v-else-if="constantes.length === 0" class="p-16 text-center text-slate-500 italic text-sm">
        Aucune constante configurée pour ce pays. Cliquez sur "Nouvelle Constante" pour commencer.
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
          <thead class="bg-slate-50 text-slate-600 font-bold text-xs uppercase tracking-wider">
            <tr>
              <th scope="col" class="px-6 py-3.5 text-left">Code</th>
              <th scope="col" class="px-6 py-3.5 text-left">Description</th>
              <th scope="col" class="px-6 py-3.5 text-right">Valeur / Montant</th>
              <th scope="col" class="px-6 py-3.5 text-center">Unité</th>
              <th scope="col" class="px-6 py-3.5 text-center">Statut</th>
              <th scope="col" class="px-6 py-3.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-150 text-slate-700">
            <tr v-for="item in constantes" :key="item.id" class="hover:bg-slate-50 transition-colors">
              <td class="px-6 py-4 font-mono font-bold text-slate-900 text-xs">{{ item.code }}</td>
              <td class="px-6 py-4 text-xs font-medium">{{ item.description }}</td>
              <td class="px-6 py-4 text-right font-mono font-semibold">{{ item.montant.toLocaleString('fr-FR') }}</td>
              <td class="px-6 py-4 text-center text-slate-500 text-xs">{{ item.unite || '-' }}</td>
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
            {{ isEditing ? 'Modifier la Constante' : 'Créer une Constante' }}
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
                placeholder="ex: SMIG"
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

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Description</label>
            <input 
              v-model="form.description" 
              type="text" 
              required 
              placeholder="ex: Salaire Minimum Interprofessionnel Garanti"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500" 
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Valeur / Montant</label>
              <input 
                v-model.number="form.montant" 
                type="number" 
                step="0.01"
                required 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-green-500" 
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Unité</label>
              <input 
                v-model="form.unite" 
                type="text" 
                placeholder="ex: FCFA, %, heures"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500" 
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
            <label for="est_actif" class="text-xs font-semibold text-slate-700 select-none">Cette constante est active</label>
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
