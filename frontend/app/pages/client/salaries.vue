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
          <NuxtLink to="/client" class="text-xs text-slate-500 hover:text-navy-700 font-semibold flex items-center gap-1">
            <Icon name="i-lucide-arrow-left" class="w-3.5 h-3.5" />
            Tableau de bord
          </NuxtLink>
        </div>
        <h1 class="text-xl font-bold text-navy-900 mt-1">
          Effectif du Personnel • {{ dossier?.nom_dossier || 'Entreprise' }}
        </h1>
        <p class="text-xs text-slate-500 mt-0.5">
          Annuaire des salariés enregistrés pour votre dossier d'entreprise.
        </p>
      </div>

      <div class="flex items-center gap-3">
        <NuxtLink to="/client/variables">
          <Button
            size="small"
            label="Saisir les variables du mois"
            class="font-bold"
          >
            <template #icon>
              <Icon name="i-lucide-edit-3" class="w-4 h-4" />
            </template>
          </Button>
        </NuxtLink>
      </div>
    </div>

    <!-- Tableau des salariés -->
    <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
      <div class="p-4 border-b border-slate-200 flex items-center justify-between gap-4">
        <div class="relative w-full max-w-sm">
          <Icon name="i-lucide-search" class="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <InputText
            v-model="searchQuery"
            placeholder="Rechercher par nom, prénom, matricule ou email..."
            class="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-800"
          />
        </div>
        <span class="text-xs font-semibold text-slate-500">
          {{ filteredSalaries.length }} salarié(s)
        </span>
      </div>

      <div v-if="loading" class="p-12 text-center text-slate-400">
        <Icon name="i-lucide-loader-2" class="w-8 h-8 mx-auto animate-spin mb-2" />
        <p class="text-xs">Chargement de l'effectif...</p>
      </div>

      <div v-else-if="filteredSalaries.length === 0" class="p-12 text-center text-slate-500">
        <Icon name="i-lucide-users" class="w-10 h-10 mx-auto text-slate-300 mb-2" />
        <p class="text-sm font-bold text-navy-900">Aucun salarié trouvé</p>
      </div>

      <div v-else class="overflow-x-auto">
        <DataTable
          :pt="{ thead: { class: 'bg-slate-50 text-[11px] font-bold text-slate-600 uppercase tracking-wider' }, tbody: { class: 'text-xs' } }"
          class="min-w-full divide-y divide-slate-200 text-left"
          :value="filteredSalaries"
          data-key="id"
          row-hover
        >
          <Column header="Salarié" header-class="px-4 py-3" body-class="px-4 py-3.5 font-bold text-slate-900">
            <template #body="{ data: s }">
              {{ s.nom }} {{ s.prenom }}
            </template>
          </Column>
          <Column header="Matricule" header-class="px-4 py-3" body-class="px-4 py-3.5 font-mono text-slate-600">
            <template #body="{ data: s }">
              {{ s.matricule || `EMP-${s.id}` }}
            </template>
          </Column>
          <Column header="Établissement" header-class="px-4 py-3" body-class="px-4 py-3.5 text-slate-600">
            <template #body="{ data: s }">
              {{ s.etablissement_nom || 'Établissement principal' }}
            </template>
          </Column>
          <Column header="Contact" header-class="px-4 py-3" body-class="px-4 py-3.5 text-slate-600">
            <template #body="{ data: s }">
              <div>{{ s.email || '-' }}</div>
              <div class="text-[11px] text-slate-400">{{ s.telephone || '' }}</div>
            </template>
          </Column>
          <Column header="Situation" header-class="px-4 py-3" body-class="px-4 py-3.5 text-slate-600">
            <template #body="{ data: s }">
              {{ s.situation_matrimoniale || 'Célibataire' }} ({{ s.enfants_charge || 0 }} enf.)
            </template>
          </Column>
          <Column header="Statut" header-class="px-4 py-3 text-center" body-class="px-4 py-3.5 text-center">
            <template #body>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-green-100 text-green-800 border border-green-200">
                Actif
              </span>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>
  </div>
</template>
