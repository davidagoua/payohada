<script setup>
const { user } = useSupabase()
const { get } = useApi()
const toast = useToast()

const loading = ref(true)
const reclamations = ref([])
const searchQuery = ref('')
const selectedFilter = ref('all') // 'all', 'en_attente', 'traite', 'rejete'

const fetchReclamations = async () => {
  loading.value = true
  try {
    reclamations.value = await get('/reclamations')
  } catch (e) {
    console.error("Erreur chargement réclamations client:", e)
    toast.add({ title: "Erreur", description: "Impossible de charger les réclamations.", color: "danger" })
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchReclamations()
})

const filteredReclamations = computed(() => {
  let list = reclamations.value
  if (selectedFilter.value !== 'all') {
    list = list.filter(r => r.statut === selectedFilter.value)
  }
  if (!searchQuery.value) return list
  const q = searchQuery.value.toLowerCase()
  return list.filter(r => 
    r.sujet.toLowerCase().includes(q) ||
    r.description.toLowerCase().includes(q) ||
    (r.salarie_nom && r.salarie_nom.toLowerCase().includes(q))
  )
})

const getStatusBadge = (statut) => {
  switch (statut) {
    case 'traite':
      return { label: 'Traitée', color: 'success' }
    case 'rejete':
      return { label: 'Rejetée', color: 'danger' }
    default:
      return { label: 'En attente', color: 'warning' }
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- En-tête -->
    <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <div class="flex items-center gap-2">
          <NuxtLink to="/client" class="text-xs text-slate-500 hover:text-green-600 font-semibold flex items-center gap-1">
            <UIcon name="i-lucide-arrow-left" class="w-3.5 h-3.5" />
            Tableau de bord
          </NuxtLink>
        </div>
        <h1 class="text-xl font-bold text-slate-900 mt-1">
          Suivi des Réclamations des Salariés
        </h1>
        <p class="text-xs text-slate-500 mt-0.5">
          Suivez les demandes et contestations déposées par les salariés de votre entreprise et les réponses apportées par le cabinet.
        </p>
      </div>

      <!-- Filtre statut -->
      <div class="flex items-center gap-2 bg-slate-50 p-1 rounded-lg border border-slate-200">
        <button 
          v-for="filter in [
            { key: 'all', label: 'Toutes' },
            { key: 'en_attente', label: 'En attente' },
            { key: 'traite', label: 'Traitées' },
            { key: 'rejete', label: 'Rejetées' }
          ]"
          :key="filter.key"
          type="button"
          class="px-2.5 py-1 text-xs font-bold rounded transition-colors cursor-pointer"
          :class="[
            selectedFilter === filter.key 
              ? 'bg-white text-green-700 shadow-2xs border border-slate-200' 
              : 'text-slate-600 hover:text-slate-900'
          ]"
          @click="selectedFilter = filter.key"
        >
          {{ filter.label }}
        </button>
      </div>
    </div>

    <!-- Liste des réclamations -->
    <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
      <div class="p-4 border-b border-slate-200">
        <div class="relative w-full max-w-sm">
          <UIcon name="i-lucide-search" class="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="Rechercher une réclamation..."
            class="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-800"
          />
        </div>
      </div>

      <div v-if="loading" class="p-12 text-center text-slate-400">
        <UIcon name="i-lucide-loader-2" class="w-8 h-8 mx-auto animate-spin mb-2" />
        <p class="text-xs">Chargement des réclamations...</p>
      </div>

      <div v-else-if="filteredReclamations.length === 0" class="p-12 text-center text-slate-500">
        <UIcon name="i-lucide-message-square-off" class="w-10 h-10 mx-auto text-slate-300 mb-2" />
        <p class="text-sm font-bold text-slate-800">Aucune réclamation trouvée</p>
        <p class="text-xs text-slate-500 mt-1">Vos salariés n'ont soumis aucune réclamation pour le moment.</p>
      </div>

      <div v-else class="divide-y divide-slate-150">
        <div v-for="r in filteredReclamations" :key="r.id" class="p-5 hover:bg-slate-50/50 transition-colors">
          <div class="flex items-start justify-between gap-4">
            <div>
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-900 text-sm">{{ r.sujet }}</span>
                <UBadge :color="getStatusBadge(r.statut).color" variant="subtle" size="xs">
                  {{ getStatusBadge(r.statut).label }}
                </UBadge>
              </div>
              <p class="text-xs text-slate-500 mt-0.5">
                Soumis par <strong>{{ r.salarie_nom }} {{ r.salarie_prenom }}</strong>
                <span v-if="r.created_at"> • le {{ new Date(r.created_at).toLocaleDateString('fr-FR') }}</span>
              </p>
            </div>
          </div>

          <div class="mt-3 bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs text-slate-700 leading-relaxed">
            {{ r.description }}
          </div>

          <!-- Commentaire du gestionnaire -->
          <div v-if="r.commentaire_gestionnaire" class="mt-3 bg-green-50/70 p-3 rounded-lg border border-green-200 text-xs">
            <span class="font-bold text-green-900 flex items-center gap-1 mb-1">
              <UIcon name="i-lucide-message-circle" class="w-4 h-4 text-green-700" />
              Réponse du cabinet :
            </span>
            <p class="text-slate-700 leading-relaxed">{{ r.commentaire_gestionnaire }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
