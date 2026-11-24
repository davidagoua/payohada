<script setup>
const route = useRoute()
const router = useRouter()
const { get, post, delete: apiDelete } = useApi()
const toast = useToast()

const dossierId = route.params.dossierId
const etabId = route.params.id

const etab = ref(null)
const salaries = ref([])
const caisses = ref([])
const loading = ref(true)
const activeTab = ref(route.query.tab || 'sals')


// Selection states for bulk actions
const selectedSalaries = ref([])
const selectedContracts = ref([])

// Recherche locale dans les listes (nom, prénom, matricule, n° de contrat).
const rechercheSalarie = ref('')
const rechercheContrat = ref('')

const salariesFiltres = computed(() => {
  const terme = normaliserRecherche(rechercheSalarie.value).trim()
  if (!terme) return salaries.value
  return salaries.value.filter((salarie) =>
    [salarie.nom, salarie.prenom, salarie.matricule]
      .some((valeur) => normaliserRecherche(valeur).includes(terme))
  )
})

const contratsFiltres = computed(() => {
  const terme = normaliserRecherche(rechercheContrat.value).trim()
  if (!terme) return contracts.value
  return contracts.value.filter((contrat) =>
    [getSalarieName(contrat.salarie_id), contrat.matricule_salarie, contrat.numero_contrat, contrat.emploi]
      .some((valeur) => normaliserRecherche(valeur).includes(terme))
  )
})

const allSalariesSelected = computed({
  get: () => salariesFiltres.value.length > 0
    && salariesFiltres.value.every((salarie) => selectedSalaries.value.includes(salarie.id)),
  set: (val) => {
    if (val) {
      selectedSalaries.value = [...new Set([...selectedSalaries.value, ...salariesFiltres.value.map(s => s.id)])]
    } else {
      const ids = new Set(salariesFiltres.value.map(s => s.id))
      selectedSalaries.value = selectedSalaries.value.filter(id => !ids.has(id))
    }
  }
})

const allContractsSelected = computed({
  get: () => contratsFiltres.value.length > 0
    && contratsFiltres.value.every((contrat) => selectedContracts.value.includes(contrat.id)),
  set: (val) => {
    if (val) {
      selectedContracts.value = [...new Set([...selectedContracts.value, ...contratsFiltres.value.map(c => c.id)])]
    } else {
      const ids = new Set(contratsFiltres.value.map(c => c.id))
      selectedContracts.value = selectedContracts.value.filter(id => !ids.has(id))
    }
  }
})

const handleBulkDeleteSalaries = async () => {
  if (selectedSalaries.value.length === 0) return
  if (!confirm(`Voulez-vous vraiment supprimer définitivement les ${selectedSalaries.value.length} salariés sélectionnés ? Cette action supprimera également tous les contrats et bulletins associés.`)) return
  loading.value = true
  try {
    let successCount = 0
    for (const salId of selectedSalaries.value) {
      try {
        await apiDelete(`/salaries/${salId}`)
        successCount++
      } catch (e) {
        console.error(`Error deleting salarie ${salId}:`, e)
      }
    }
    toast.add({
      title: 'Action terminée',
      description: `${successCount} salarié(s) supprimé(s) avec succès.`,
      color: 'success'
    })
    selectedSalaries.value = []
    await fetchEtabDetails()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

/**
 * Envoie au salarié ses identifiants, depuis la liste.
 *
 * Le mot de passe n'étant stocké que haché, l'envoi en génère un nouveau :
 * l'ancien cesse de fonctionner, ce que le message rappelle.
 */
const envoiIdentifiantsId = ref(null)

const envoyerIdentifiants = async (salarie) => {
  envoiIdentifiantsId.value = salarie.id
  try {
    const resultat = await post(`/salaries/${salarie.id}/envoyer-acces`)
    const provisoire = resultat?.mot_de_passe_provisoire || ''
    if (resultat?.email_envoye) {
      toast.add({
        title: 'Identifiants envoyés',
        description: `Un nouveau mot de passe provisoire a été envoyé à ${salarie.email}. L'ancien n'est plus valable.`,
        color: 'success'
      })
    } else {
      toast.add({
        title: 'Envoi impossible',
        description: `Mot de passe provisoire : ${provisoire} — transmettez-le au salarié${resultat?.email_message ? ` (${resultat.email_message})` : ''}.`,
        color: 'warning',
        duration: 20000
      })
    }
  } catch (e) {
    console.error('Envoi des identifiants impossible :', e)
    toast.add({
      title: 'Envoi impossible',
      description: e.data?.detail || 'Une erreur est survenue.',
      color: 'danger'
    })
  } finally {
    envoiIdentifiantsId.value = null
  }
}

const handleBulkDeleteContracts = async () => {
  if (selectedContracts.value.length === 0) return
  if (!confirm(`Voulez-vous vraiment supprimer définitivement les ${selectedContracts.value.length} contrats sélectionnés ? Les bulletins associés seront supprimés.`)) return
  loading.value = true
  try {
    let successCount = 0
    for (const cId of selectedContracts.value) {
      try {
        await apiDelete(`/contrats/${cId}`)
        successCount++
      } catch (e) {
        console.error(`Error deleting contract ${cId}:`, e)
      }
    }
    toast.add({
      title: 'Action terminée',
      description: `${successCount} contrat(s) supprimé(s) avec succès.`,
      color: 'success'
    })
    selectedContracts.value = []
    await fetchEtabDetails()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

// Global State for breadcrumbs
const currentDossier = useState('current-dossier')
const currentEtablissement = useState('current-etablissement')

// Contrats de l'établissement
const contracts = ref([])

const fetchEtabDetails = async () => {
  loading.value = true
  try {
    // Ensure parent dossier context is loaded
    if (!currentDossier.value) {
      const parentDossier = await get(`/dossiers/${dossierId}`)
      currentDossier.value = parentDossier
    }

    const data = await get(`/etablissements/${etabId}`)
    etab.value = data
    currentEtablissement.value = data


    // Fetch Employees
    const sals = await get(`/etablissements/${etabId}/salaries`)
    salaries.value = sals || []

    // Fetch Caisses
    const cs = await get(`/etablissements/${etabId}/caisses`)
    caisses.value = cs || []

    // Fetch Dossier Contracts and filter locally
    const allContracts = await get(`/dossiers/${dossierId}/contrats`)
    contracts.value = (allContracts || []).filter(c => c.etablissement_id === Number(etabId))

  } catch (e) {
    console.error(e)
    router.push(`/dossiers/${dossierId}`)
  } finally {
    loading.value = false
  }
}

const handleDeleteEtab = async () => {
  if (!confirm('Supprimer cet établissement ? Toutes les fiches salariés et contrats associés seront supprimés.')) return
  try {
    await apiDelete(`/etablissements/${etabId}`)
    toast.add({
      title: 'Supprimé',
      description: 'L\'établissement a été supprimé.',
      color: 'success'
    })
    router.push(`/dossiers/${dossierId}`)
  } catch (e) {
    console.error(e)
  }
}

const getSalarieName = (salarieId) => {
  const s = salaries.value.find(emp => emp.id === salarieId)
  return s ? `${s.nom.toUpperCase()} ${s.prenom}` : 'Inconnu'
}

watch(() => route.query.tab, (newTab) => {
  if (newTab) {
    activeTab.value = newTab
  } else {
    activeTab.value = 'sals'
  }
})

onMounted(fetchEtabDetails)
</script>

<template>
  <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4">
    <Icon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement de l'établissement...</span>
  </div>
  <div v-else-if="etab" class="space-y-6">


    <!-- Tab 1: Info, Address & Bank + Caisses de cotisation -->
    <div v-show="activeTab === 'infos'" class="space-y-6">
      <EtablissementInfos :etab="etab" :caisses="caisses" @refresh="fetchEtabDetails" />
    </div>

    <!-- Tab 2: Salariés -->
    <div v-show="activeTab === 'sals'" class="space-y-6">
      <div class="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-flat border-t-4 border-t-navy-900">

        <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 border-b border-slate-200 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-navy-900 uppercase tracking-wider">Salariés de l'Établissement</h3>
            <p class="text-xs text-slate-500">Liste des fiches civiles des salariés déclarés dans cet établissement.</p>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center gap-2 w-full sm:w-auto">
            <div class="relative w-full sm:w-72">
              <Icon name="i-lucide-search" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
              <InputText
                v-model="rechercheSalarie"
                type="search"
                placeholder="Rechercher par nom ou matricule…"
                class="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
            <button
              @click="router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/new`)"
              class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg text-xs transition-colors flex items-center justify-center gap-1.5 shadow-flat uppercase tracking-wider cursor-pointer whitespace-nowrap"
            >
              <Icon name="i-lucide-user-plus" class="w-3.5 h-3.5" />
              Ajouter un Salarié
            </button>
          </div>
        </div>

        <!-- Bulk Actions Bar -->
        <div v-if="selectedSalaries.length > 0" class="bg-slate-100 border border-slate-300 p-3 mb-4 flex items-center justify-between text-xs transition-all">
          <div class="font-bold text-slate-700">
            {{ selectedSalaries.length }} salarié(s) sélectionné(s)
          </div>
          <button
            @click="handleBulkDeleteSalaries"
            class="p-1.5 bg-red-650 hover:bg-red-755 text-white transition-colors shadow-flat cursor-pointer flex items-center justify-center"
            title="Supprimer la sélection"
          >
            <Icon name="i-lucide-trash-2" class="w-4 h-4" />
          </button>
        </div>

        <!-- Employees Table -->
        <div v-if="salaries.length === 0" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun salarié enregistré dans cet établissement.
        </div>
        <div v-else-if="salariesFiltres.length === 0" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun salarié ne correspond à « {{ rechercheSalarie }} ».
        </div>
        <div v-else class="overflow-x-auto">
          <DataTable
            :pt="{ thead: { class: 'bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]' }, tbody: { class: 'bg-white' } }"
            class="min-w-full divide-y divide-slate-200 text-sm"
            :value="salariesFiltres"
            data-key="id"
            @row-click="({ data: sal }) => router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${sal.id}`)"
            :row-class="() => 'cursor-pointer group'"
            row-hover
          >
            <Column header-class="px-4 py-3 text-left w-10" body-class="px-4 py-4">
              <template #header>
                <Checkbox v-model="allSalariesSelected" binary />
              </template>
              <template #body="{ data: sal }">
                <div @click.stop>
                  <Checkbox :value="sal.id" v-model="selectedSalaries" />
                </div>
              </template>
            </Column>
            <Column header="Matricule" header-class="px-6 py-3 text-left" body-class="px-6 py-4 font-mono font-semibold text-slate-900">
              <template #body="{ data: sal }">
                {{ sal.matricule }}
              </template>
            </Column>
            <Column header="Nom & Prénom" header-class="px-6 py-3 text-left" body-class="px-6 py-4 font-medium text-slate-700 group-hover:text-navy-700 transition-colors">
              <template #body="{ data: sal }">
                {{ sal.nom.toUpperCase() }} {{ sal.prenom }}
              </template>
            </Column>
            <Column header="N° Sécurité Sociale (NIR)" header-class="px-6 py-3 text-left" body-class="px-6 py-4 font-mono text-slate-500">
              <template #body="{ data: sal }">
                {{ sal.numero_securite_sociale || '-' }}
              </template>
            </Column>
            <Column header="Email" header-class="px-6 py-3 text-left" body-class="px-6 py-4 text-slate-500">
              <template #body="{ data: sal }">
                {{ sal.email || '-' }}
              </template>
            </Column>
            <Column header="Téléphone" header-class="px-6 py-3 text-left" body-class="px-6 py-4 text-slate-500 font-mono">
              <template #body="{ data: sal }">
                {{ sal.telephone || '-' }}
              </template>
            </Column>
            <Column header="Statut" header-class="px-6 py-3 text-left" body-class="px-6 py-4">
              <template #body="{ data: sal }">
                <span
                  :class="[
                    sal.is_active ? 'bg-green-50 text-green-700 border-green-200' : 'bg-slate-100 text-slate-500 border-slate-200',
                    'px-2 py-0.5 rounded-lg text-xs font-semibold border'
                  ]"
                >
                  {{ sal.is_active ? 'Actif' : 'Inactif' }}
                </span>
              </template>
            </Column>
            <Column header-class="relative px-6 py-3" body-class="px-6 py-4 text-right">
              <template #header>
                <span class="sr-only">Actions</span>
              </template>
              <template #body="{ data: sal }">
                <div class="flex items-center justify-end gap-3">
                  <button
                    type="button"
                    :disabled="!sal.email || envoiIdentifiantsId === sal.id"
                    :title="sal.email
                      ? 'Génère un nouveau mot de passe provisoire et l\'envoie par email'
                      : 'Renseignez un email sur la fiche pour pouvoir envoyer les identifiants'"
                    class="p-1 text-slate-400 hover:text-green-700 disabled:text-slate-200 disabled:cursor-not-allowed transition-colors"
                    @click.stop="envoyerIdentifiants(sal)"
                  >
                    <Icon
                      :name="envoiIdentifiantsId === sal.id ? 'i-lucide-loader-2' : 'i-lucide-mail'"
                      class="w-4 h-4"
                      :class="{ 'animate-spin': envoiIdentifiantsId === sal.id }"
                    />
                  </button>
                  <span class="text-navy-700 group-hover:underline text-xs font-bold uppercase tracking-wider flex items-center gap-1">
                    Fiche Salarié
                    <Icon name="i-lucide-chevron-right" class="w-4 h-4" />
                  </span>
                </div>
              </template>
            </Column>
          </DataTable>
        </div>

      </div>
    </div>

    <!-- Tab 3: Contrats -->
    <div v-show="activeTab === 'contrats'" class="space-y-6">
      <div class="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-flat border-t-4 border-t-navy-900">

        <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 border-b border-slate-200 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-navy-900 uppercase tracking-wider">Contrats de l'Établissement</h3>
            <p class="text-xs text-slate-500">Historique des contrats de travail rattachés à cet établissement.</p>
          </div>
          <div class="flex items-center gap-3 w-full sm:w-auto">
            <div class="relative w-full sm:w-72">
              <Icon name="i-lucide-search" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
              <InputText
                v-model="rechercheContrat"
                type="search"
                placeholder="Rechercher par nom ou matricule…"
                class="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
            <span v-if="rechercheContrat" class="text-xs text-slate-500 whitespace-nowrap">
              {{ contratsFiltres.length }} / {{ contracts.length }}
            </span>
          </div>
        </div>

        <!-- Bulk Actions Bar -->
        <div v-if="selectedContracts.length > 0" class="bg-slate-100 border border-slate-300 p-3 mb-4 flex items-center justify-between text-xs transition-all">
          <div class="font-bold text-slate-700">
            {{ selectedContracts.length }} contrat(s) sélectionné(s)
          </div>
          <button
            @click="handleBulkDeleteContracts"
            class="p-1.5 bg-red-650 hover:bg-red-755 text-white transition-colors shadow-flat cursor-pointer flex items-center justify-center"
            title="Supprimer la sélection"
          >
            <Icon name="i-lucide-trash-2" class="w-4 h-4" />
          </button>
        </div>

        <!-- Contracts Table -->
        <div v-if="contracts.length === 0" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun contrat enregistré dans cet établissement.
        </div>
        <div v-else-if="contratsFiltres.length === 0" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun contrat ne correspond à « {{ rechercheContrat }} ».
        </div>
        <div v-else class="overflow-x-auto">
          <DataTable
            :pt="{ thead: { class: 'bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]' }, tbody: { class: 'bg-white' } }"
            class="min-w-full divide-y divide-slate-200 text-sm"
            :value="contratsFiltres"
            data-key="id"
            @row-click="({ data: c }) => router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${c.salarie_id}/contrats/${c.id}`)"
            :row-class="() => 'cursor-pointer group'"
            row-hover
          >
            <Column header-class="px-4 py-3 text-left w-10" body-class="px-4 py-4">
              <template #header>
                <Checkbox v-model="allContractsSelected" binary />
              </template>
              <template #body="{ data: c }">
                <div @click.stop>
                  <Checkbox :value="c.id" v-model="selectedContracts" />
                </div>
              </template>
            </Column>
            <Column header="N° Contrat" header-class="px-6 py-3 text-left" body-class="px-6 py-4 font-mono font-semibold text-slate-900">
              <template #body="{ data: c }">
                {{ c.numero_contrat }}
              </template>
            </Column>
            <Column header="Salarié" header-class="px-6 py-3 text-left" body-class="px-6 py-4 font-medium text-slate-700 group-hover:text-navy-700 transition-colors">
              <template #body="{ data: c }">
                {{ getSalarieName(c.salarie_id) }}
              </template>
            </Column>
            <Column header="Poste / Emploi" header-class="px-6 py-3 text-left" body-class="px-6 py-4 font-medium text-slate-700">
              <template #body="{ data: c }">
                {{ c.emploi || 'Non renseigné' }}
              </template>
            </Column>
            <Column header="Type Contrat" header-class="px-6 py-3 text-left" body-class="px-6 py-4 text-slate-650 font-semibold">
              <template #body="{ data: c }">
                {{ c.type_contrat_travail === 10 ? 'CDI' : c.type_contrat_travail === 29 ? 'CDD' : 'Autre (code ' + c.type_contrat_travail + ')' }}
              </template>
            </Column>
            <Column header="Date Début" header-class="px-6 py-3 text-left" body-class="px-6 py-4 font-mono text-slate-500">
              <template #body="{ data: c }">
                {{ c.date_debut_contrat || '-' }}
              </template>
            </Column>
            <Column header="Statut" header-class="px-6 py-3 text-left" body-class="px-6 py-4">
              <template #body="{ data: c }">
                <span
                  :class="[
                    c.statut === 'actif' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-slate-150 text-slate-500 border-slate-200',
                    'px-2 py-0.5 rounded-lg text-[10px] uppercase font-bold border'
                  ]"
                >
                  {{ c.statut }}
                </span>
              </template>
            </Column>
            <Column header-class="relative px-6 py-3" body-class="px-6 py-4 text-right">
              <template #header>
                <span class="sr-only">Actions</span>
              </template>
              <template #body>
                <span class="text-navy-700 group-hover:underline text-xs font-bold uppercase tracking-wider flex items-center justify-end gap-1">
                  Gérer le Contrat
                  <Icon name="i-lucide-chevron-right" class="w-4 h-4" />
                </span>
              </template>
            </Column>
          </DataTable>
        </div>

      </div>
    </div>

    <!-- Tab 4: Bulletins de Salaire -->
    <div v-show="activeTab === 'bulletins'" class="space-y-6">
      <EtablissementBulletins
        :dossier-id="dossierId"
        :etab-id="etabId"
        :contracts="contracts"
        :salaries="salaries"
      />
    </div>

    <!-- Tab 5: Boîte à outils (simulateurs, sans enregistrement) -->
    <div v-if="activeTab === 'outils'" class="space-y-6">
      <EtablissementBoiteOutils :contracts="contracts" :salaries="salaries" />
    </div>

    <!-- Tab 6: DSN (déclarations) -->
    <div v-if="activeTab === 'dsn'" class="space-y-6">
      <EtablissementDsn />
    </div>
  </div>
</template>
