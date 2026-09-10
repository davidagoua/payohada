<script setup>
const { user } = useSupabase()
const { get } = useApi()
const toast = useToast()

const loading = ref(true)
const dossier = ref(null)
const salaries = ref([])
const searchQuery = ref('')

const fetchSalaries = async () => {
  loading.value = true
  try {
    const dossiers = await get('/dossiers')
    if (dossiers && dossiers.length > 0) {
      const targetId = user.value?.dossier_id || dossiers[0].id
      dossier.value = dossiers.find(d => d.id === targetId) || dossiers[0]
    }

    if (dossier.value) {
      // Récupérer les établissements du dossier
      const etabs = await get(`/dossiers/${dossier.value.id}/etablissements`)
      let allSalaries = []
      for (const etab of etabs) {
        try {
          const list = await get(`/etablissements/${etab.id}/salaries`)
          allSalaries = allSalaries.concat(list.map(s => ({ ...s, etablissement_nom: etab.raison_sociale })))
        } catch (e) {
          console.error("Erreur chargement salaries etab:", e)
        }
      }
      salaries.value = allSalaries
    }
  } catch (e) {
    console.error("Erreur chargement salaries client:", e)
    toast.add({ title: "Erreur", description: "Impossible de charger la liste des salariés.", color: "danger" })
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchSalaries()
})

const filteredSalaries = computed(() => {
  if (!searchQuery.value) return salaries.value
  const q = searchQuery.value.toLowerCase()
  return salaries.value.filter(s => 
    s.nom.toLowerCase().includes(q) ||
    s.prenom.toLowerCase().includes(q) ||
    (s.matricule && s.matricule.toLowerCase().includes(q)) ||
    (s.email && s.email.toLowerCase().includes(q))
  )
})

const formatFCFA = (amount) => {
  if (amount === undefined || amount === null) return '0 FCFA'
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XOF', minimumFractionDigits: 0 })
    .format(amount)
    .replace('XOF', 'FCFA')
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
          Effectif du Personnel • {{ dossier?.nom_dossier || 'Entreprise' }}
        </h1>
        <p class="text-xs text-slate-500 mt-0.5">
          Annuaire des salariés enregistrés pour votre dossier d'entreprise.
        </p>
      </div>

      <div class="flex items-center gap-3">
        <NuxtLink to="/client/variables">
          <UButton color="primary" size="sm" class="bg-green-600 hover:bg-green-700 text-white font-bold">
            <UIcon name="i-lucide-edit-3" class="w-4 h-4 mr-1.5" />
            Saisir les variables du mois
          </UButton>
        </NuxtLink>
      </div>
    </div>

    <!-- Tableau des salariés -->
    <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
      <div class="p-4 border-b border-slate-200 flex items-center justify-between gap-4">
        <div class="relative w-full max-w-sm">
          <UIcon name="i-lucide-search" class="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="Rechercher par nom, prénom, matricule ou email..."
            class="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-800"
          />
        </div>
        <span class="text-xs font-semibold text-slate-500">
          {{ filteredSalaries.length }} salarié(s)
        </span>
      </div>

      <div v-if="loading" class="p-12 text-center text-slate-400">
        <UIcon name="i-lucide-loader-2" class="w-8 h-8 mx-auto animate-spin mb-2" />
        <p class="text-xs">Chargement de l'effectif...</p>
      </div>

      <div v-else-if="filteredSalaries.length === 0" class="p-12 text-center text-slate-500">
        <UIcon name="i-lucide-users" class="w-10 h-10 mx-auto text-slate-300 mb-2" />
        <p class="text-sm font-bold text-slate-800">Aucun salarié trouvé</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 text-left">
          <thead class="bg-slate-50 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
            <tr>
              <th scope="col" class="px-4 py-3">Salarié</th>
              <th scope="col" class="px-4 py-3">Matricule</th>
              <th scope="col" class="px-4 py-3">Établissement</th>
              <th scope="col" class="px-4 py-3">Contact</th>
              <th scope="col" class="px-4 py-3">Situation</th>
              <th scope="col" class="px-4 py-3 text-center">Statut</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-150 text-xs">
            <tr v-for="s in filteredSalaries" :key="s.id" class="hover:bg-slate-50/70 transition-colors">
              <td class="px-4 py-3.5 font-bold text-slate-900">
                {{ s.nom }} {{ s.prenom }}
              </td>
              <td class="px-4 py-3.5 font-mono text-slate-600">
                {{ s.matricule || `EMP-${s.id}` }}
              </td>
              <td class="px-4 py-3.5 text-slate-600">
                {{ s.etablissement_nom || 'Établissement principal' }}
              </td>
              <td class="px-4 py-3.5 text-slate-600">
                <div>{{ s.email || '-' }}</div>
                <div class="text-[11px] text-slate-400">{{ s.telephone || '' }}</div>
              </td>
              <td class="px-4 py-3.5 text-slate-600">
                {{ s.situation_matrimoniale || 'Célibataire' }} ({{ s.enfants_charge || 0 }} enf.)
              </td>
              <td class="px-4 py-3.5 text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-green-100 text-green-800 border border-green-200">
                  Actif
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
