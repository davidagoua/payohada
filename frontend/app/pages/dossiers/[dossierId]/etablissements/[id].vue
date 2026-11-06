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
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
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
              <UIcon name="i-lucide-search" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
              <input
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
              <UIcon name="i-lucide-user-plus" class="w-3.5 h-3.5" />
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
            <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
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
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left w-10">
                  <input type="checkbox" v-model="allSalariesSelected" class="rounded-lg border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </th>
                <th scope="col" class="px-6 py-3 text-left">Matricule</th>
                <th scope="col" class="px-6 py-3 text-left">Nom & Prénom</th>
                <th scope="col" class="px-6 py-3 text-left">N° Sécurité Sociale (NIR)</th>
                <th scope="col" class="px-6 py-3 text-left">Email</th>
                <th scope="col" class="px-6 py-3 text-left">Téléphone</th>
                <th scope="col" class="px-6 py-3 text-left">Statut</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr
                v-for="sal in salariesFiltres"
                :key="sal.id"
                @click="router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${sal.id}`)"
                class="hover:bg-slate-50/55 cursor-pointer group"
              >
                <td class="px-4 py-4" @click.stop>
                  <input type="checkbox" :value="sal.id" v-model="selectedSalaries" class="rounded-lg border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </td>
                <td class="px-6 py-4 font-mono font-semibold text-slate-900">{{ sal.matricule }}</td>
                <td class="px-6 py-4 font-medium text-slate-700 group-hover:text-navy-700 transition-colors">
                  {{ sal.nom.toUpperCase() }} {{ sal.prenom }}
                </td>
                <td class="px-6 py-4 font-mono text-slate-500">{{ sal.numero_securite_sociale || '-' }}</td>
                <td class="px-6 py-4 text-slate-500">{{ sal.email || '-' }}</td>
                <td class="px-6 py-4 text-slate-500 font-mono">{{ sal.telephone || '-' }}</td>
                <td class="px-6 py-4">
                  <span
                    :class="[
                      sal.is_active ? 'bg-green-50 text-green-700 border-green-200' : 'bg-slate-100 text-slate-500 border-slate-200',
                      'px-2 py-0.5 rounded-lg text-xs font-semibold border'
                    ]"
                  >
                    {{ sal.is_active ? 'Actif' : 'Inactif' }}
                  </span>
                </td>
                <td class="px-6 py-4 text-right">
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
                      <UIcon
                        :name="envoiIdentifiantsId === sal.id ? 'i-lucide-loader-2' : 'i-lucide-mail'"
                        class="w-4 h-4"
                        :class="{ 'animate-spin': envoiIdentifiantsId === sal.id }"
                      />
                    </button>
                    <span class="text-navy-700 group-hover:underline text-xs font-bold uppercase tracking-wider flex items-center gap-1">
                      Fiche Salarié
                      <UIcon name="i-lucide-chevron-right" class="w-4 h-4" />
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
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
              <UIcon name="i-lucide-search" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
              <input
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
            <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
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
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left w-10">
                  <input type="checkbox" v-model="allContractsSelected" class="rounded-lg border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </th>
                <th scope="col" class="px-6 py-3 text-left">N° Contrat</th>
                <th scope="col" class="px-6 py-3 text-left">Salarié</th>
                <th scope="col" class="px-6 py-3 text-left">Poste / Emploi</th>
                <th scope="col" class="px-6 py-3 text-left">Type Contrat</th>
                <th scope="col" class="px-6 py-3 text-left">Date Début</th>
                <th scope="col" class="px-6 py-3 text-left">Statut</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr
                v-for="c in contratsFiltres"
                :key="c.id"
                @click="router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${c.salarie_id}/contrats/${c.id}`)"
                class="hover:bg-slate-50 cursor-pointer group"
              >
                <td class="px-4 py-4" @click.stop>
                  <input type="checkbox" :value="c.id" v-model="selectedContracts" class="rounded-lg border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </td>
                <td class="px-6 py-4 font-mono font-semibold text-slate-900">{{ c.numero_contrat }}</td>
                <td class="px-6 py-4 font-medium text-slate-700 group-hover:text-navy-700 transition-colors">
                  {{ getSalarieName(c.salarie_id) }}
                </td>
                <td class="px-6 py-4 font-medium text-slate-700">
                  {{ c.emploi || 'Non renseigné' }}
                </td>
                <td class="px-6 py-4 text-slate-650 font-semibold">
                  {{ c.type_contrat_travail === 10 ? 'CDI' : c.type_contrat_travail === 29 ? 'CDD' : 'Autre (code ' + c.type_contrat_travail + ')' }}
                </td>

                <td class="px-6 py-4 font-mono text-slate-500">{{ c.date_debut_contrat || '-' }}</td>
                <td class="px-6 py-4">
                  <span
                    :class="[
                      c.statut === 'actif' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-slate-150 text-slate-500 border-slate-200',
                      'px-2 py-0.5 rounded-lg text-[10px] uppercase font-bold border'
                    ]"
                  >
                    {{ c.statut }}
                  </span>
                </td>
                <td class="px-6 py-4 text-right">
                  <span class="text-navy-700 group-hover:underline text-xs font-bold uppercase tracking-wider flex items-center justify-end gap-1">
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

    <!-- Tab 4: Bulletins de Salaire -->
    <div v-show="activeTab === 'bulletins'" class="space-y-6">
      <EtablissementBulletins
        :dossier-id="dossierId"
        :etab-id="etabId"
        :contracts="contracts"
        :salaries="salaries"
      />
    </div>
  </div>
</template>
