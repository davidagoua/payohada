<script setup>
const route = useRoute()
const router = useRouter()
const { get, put, post, delete: apiDelete } = useApi()
const toast = useToast()

const dossierId = route.params.dossierId
const etabId = route.params.id

const etab = ref(null)
const salaries = ref([])
const caisses = ref([])
const loading = ref(true)
const activeTab = ref(route.query.tab || 'sals')

// Selection states for bulk actions
const selectedCaisses = ref([])
const selectedSalaries = ref([])
const selectedContracts = ref([])
const selectedBulletins = ref([])

const allCaissesSelected = computed({
  get: () => caisses.value.length > 0 && selectedCaisses.value.length === caisses.value.length,
  set: (val) => {
    if (val) {
      selectedCaisses.value = caisses.value.map(c => c.id)
    } else {
      selectedCaisses.value = []
    }
  }
})

const allSalariesSelected = computed({
  get: () => salaries.value.length > 0 && selectedSalaries.value.length === salaries.value.length,
  set: (val) => {
    if (val) {
      selectedSalaries.value = salaries.value.map(s => s.id)
    } else {
      selectedSalaries.value = []
    }
  }
})

const allContractsSelected = computed({
  get: () => contracts.value.length > 0 && selectedContracts.value.length === contracts.value.length,
  set: (val) => {
    if (val) {
      selectedContracts.value = contracts.value.map(c => c.id)
    } else {
      selectedContracts.value = []
    }
  }
})

const allBulletinsSelected = computed({
  get: () => contracts.value.length > 0 && selectedBulletins.value.length === contracts.value.length,
  set: (val) => {
    if (val) {
      selectedBulletins.value = contracts.value.map(c => c.id)
    } else {
      selectedBulletins.value = []
    }
  }
})

const handleBulkDeleteCaisses = async () => {
  if (selectedCaisses.value.length === 0) return
  if (!confirm(`Voulez-vous vraiment détacher les ${selectedCaisses.value.length} caisses de cotisation sélectionnées ?`)) return
  loading.value = true
  try {
    let successCount = 0
    for (const caisseId of selectedCaisses.value) {
      try {
        await apiDelete(`/caisses/${caisseId}`)
        successCount++
      } catch (e) {
        console.error(`Error deleting caisse ${caisseId}:`, e)
      }
    }
    toast.add({
      title: 'Action terminée',
      description: `${successCount} caisse(s) détachée(s) avec succès.`,
      color: 'success'
    })
    selectedCaisses.value = []
    await fetchEtabDetails()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

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

const handleCalculateSelected = async () => {
  const pending = selectedBulletins.value.filter(cId => !bulletinsMap.value[cId])
  if (pending.length === 0) {
    toast.add({
      title: 'Info',
      description: 'Tous les bulletins de la sélection sont déjà générés.',
      color: 'warning'
    })
    return
  }

  if (!confirm(`Générer les bulletins de paie pour les ${pending.length} salarié(s) sélectionnés en attente ?`)) return

  bulkProcessing.value = true
  bulkProgress.value = 0
  bulkTotal.value = pending.length

  let successCount = 0
  for (let i = 0; i < pending.length; i++) {
    const cId = pending[i]
    try {
      const payload = {
        contrat_id: cId,
        mois: Number(selectedMois.value),
        annee: Number(selectedAnnee.value),
        acompte: 0.0,
        commentaire: "Calcul groupé de la sélection"
      }
      await post('/bulletins/calculer', payload)
      successCount++
    } catch (e) {
      console.error(`Error calculating for contract ${cId}:`, e)
    }
    bulkProgress.value = i + 1
  }

  bulkProcessing.value = false
  toast.add({
    title: 'Génération terminée',
    description: `${successCount} bulletin(s) de salaire calculé(s) avec succès.`,
    color: 'success'
  })
  selectedBulletins.value = []
  await fetchBulletins()
}

const handleValidateSelected = async () => {
  const drafts = selectedBulletins.value
    .map(cId => bulletinsMap.value[cId])
    .filter(b => b && b.statut !== 'valide')

  if (drafts.length === 0) {
    toast.add({
      title: 'Info',
      description: 'Aucun bulletin en brouillon sélectionné à valider.',
      color: 'warning'
    })
    return
  }

  if (!confirm(`Valider définitivement les ${drafts.length} bulletin(s) sélectionnés en brouillon ?`)) return

  bulkProcessing.value = true
  bulkProgress.value = 0
  bulkTotal.value = drafts.length

  let successCount = 0
  for (let i = 0; i < drafts.length; i++) {
    const b = drafts[i]
    try {
      await put(`/bulletins/${b.id}/valider`)
      successCount++
    } catch (e) {
      console.error(`Error validating bulletin ${b.id}:`, e)
    }
    bulkProgress.value = i + 1
  }

  bulkProcessing.value = false
  toast.add({
    title: 'Validation terminée',
    description: `${successCount} bulletin(s) validé(s) définitivement.`,
    color: 'success'
  })
  selectedBulletins.value = []
  await fetchBulletins()
}

const handleDeleteSelectedBulletins = async () => {
  const drafts = selectedBulletins.value
    .map(cId => bulletinsMap.value[cId])
    .filter(b => b && b.statut !== 'valide')

  if (drafts.length === 0) {
    toast.add({
      title: 'Info',
      description: 'Aucun bulletin en brouillon sélectionné à supprimer.',
      color: 'warning'
    })
    return
  }

  if (!confirm(`Supprimer définitivement les ${drafts.length} bulletin(s) sélectionnés ?`)) return

  bulkProcessing.value = true
  bulkProgress.value = 0
  bulkTotal.value = drafts.length

  let successCount = 0
  for (let i = 0; i < drafts.length; i++) {
    const b = drafts[i]
    try {
      await apiDelete(`/bulletins/${b.id}`)
      successCount++
    } catch (e) {
      console.error(`Error deleting bulletin ${b.id}:`, e)
    }
    bulkProgress.value = i + 1
  }

  bulkProcessing.value = false
  toast.add({
    title: 'Suppression terminée',
    description: `${successCount} bulletin(s) de salaire supprimé(s).`,
    color: 'success'
  })
  selectedBulletins.value = []
  await fetchBulletins()
}

// Global State for breadcrumbs
const currentDossier = useState('current-dossier')
const currentEtablissement = useState('current-etablissement')

// Etablissement Form Fields
const etabCode = ref('')
const etabNom = ref('')
const etabPrincipal = ref(false)

// CNPS Fields
const cnpsMatricule = ref('')
const cnpsCodeActivite = ref('')
const cnpsCodeAgence = ref('')
const cnpsCodeEtablissement = ref('')
const cnpsAgenceRattachement = ref('')
const cnpsPeriodicitePaiement = ref('Mensuelle')
const cmuPeriodicitePaiement = ref('Mensuelle')

// DGI Fields
const dgiCompteContribuable = ref('')
const dgiCentreImpots = ref('')
const dgiPeriodiciteDeclaration = ref('Mensuelle')
const dgiRegimeFiscal = ref('Régime général')

// Address Form Fields
const addrVoie = ref('')
const addrVoie2 = ref('')
const addrComp = ref('')
const addrCode = ref('')
const addrVille = ref('')
const addrPays = ref('')

// Bank Form Fields
const bankVirement = ref(false)
const bankIban = ref('')
const bankBic = ref('')

// Cotisation Caisse Modal & Fields
const caisseModalOpen = ref(false)
const caisseNom = ref('')
const caisseType = ref('urssaf')
const caisseDsn = ref('')
const caisseAffiliation = ref('')
const caisseIban = ref('')
const caisseBic = ref('')

// Contrats & Bulletins state
const contracts = ref([])
const bulletinsMap = ref({})

// Period filter state for bulletins
const selectedMois = ref(new Date().getMonth() + 1)
const selectedAnnee = ref(new Date().getFullYear())

// Bulk processing states for bulletins
const bulkProcessing = ref(false)
const bulkProgress = ref(0)
const bulkTotal = ref(0)

const fetchBulletins = async () => {
  try {
    const bList = await get(`/dossiers/${dossierId}/bulletins`, { 
      query: { 
        mois: selectedMois.value, 
        annee: selectedAnnee.value 
      } 
    })
    const map = {}
    if (bList) {
      bList.forEach(b => {
        map[b.contrat_id] = b
      })
    }
    bulletinsMap.value = map
  } catch (e) {
    console.error("Error loading bulletins:", e)
  }
}

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

    // Populate Main
    etabCode.value = data.code || ''
    etabNom.value = data.raison_sociale || ''
    etabPrincipal.value = data.etablissement_principal || false

    // Populate CNPS
    cnpsMatricule.value = data.cnps_matricule || ''
    cnpsCodeActivite.value = data.cnps_code_activite || ''
    cnpsCodeAgence.value = data.cnps_code_agence || ''
    cnpsCodeEtablissement.value = data.cnps_code_etablissement || ''
    cnpsAgenceRattachement.value = data.cnps_agence_rattachement || ''
    cnpsPeriodicitePaiement.value = data.cnps_periodicite_paiement || 'Mensuelle'
    cmuPeriodicitePaiement.value = data.cmu_periodicite_paiement || 'Mensuelle'

    // Populate DGI
    dgiCompteContribuable.value = data.dgi_compte_contribuable || ''
    dgiCentreImpots.value = data.dgi_centre_impots || ''
    dgiPeriodiciteDeclaration.value = data.dgi_periodicite_declaration || 'Mensuelle'
    dgiRegimeFiscal.value = data.dgi_regime_fiscal || 'Régime général'

    // Populate Address
    if (data.adresse) {
      addrVoie.value = data.adresse.adresse_postale || ''
      addrVoie2.value = data.adresse.adresse_postale2 || ''
      addrComp.value = data.adresse.complement_adresse || ''
      addrCode.value = data.adresse.code_postal || ''
      addrVille.value = data.adresse.ville || ''
      addrPays.value = data.adresse.pays || ''
    }

    // Populate Bank
    if (data.banque) {
      bankVirement.value = data.banque.virement || false
      bankIban.value = data.banque.iban || ''
      bankBic.value = data.banque.code_bic || ''
    }

    // Fetch Employees
    const sals = await get(`/etablissements/${etabId}/salaries`)
    salaries.value = sals || []

    // Fetch Caisses
    const cs = await get(`/etablissements/${etabId}/caisses`)
    caisses.value = cs || []

    // Fetch Dossier Contracts and filter locally
    const allContracts = await get(`/dossiers/${dossierId}/contrats`)
    contracts.value = (allContracts || []).filter(c => c.etablissement_id === Number(etabId))

    // Fetch Bulletins
    await fetchBulletins()

  } catch (e) {
    console.error(e)
    router.push(`/dossiers/${dossierId}`)
  } finally {
    loading.value = false
  }
}

const handleUpdateEtab = async () => {
  try {
    const payload = {
      raison_sociale: etabNom.value,
      code: etabCode.value,
      siret: null,
      ape: null,
      ccn: null,
      etablissement_principal: etabPrincipal.value,
      adresse: {
        adresse_postale: addrVoie.value || null,
        adresse_postale2: addrVoie2.value || null,
        complement_adresse: addrComp.value || null,
        code_postal: addrCode.value || null,
        ville: addrVille.value || null,
        pays: addrPays.value || null
      },
      banque: {
        virement: bankVirement.value,
        iban: bankIban.value || null,
        code_bic: bankBic.value || null
      },
      cnps_matricule: cnpsMatricule.value || null,
      cnps_code_activite: cnpsCodeActivite.value || null,
      cnps_code_agence: cnpsCodeAgence.value || null,
      cnps_code_etablissement: cnpsCodeEtablissement.value || null,
      cnps_agence_rattachement: cnpsAgenceRattachement.value || null,
      cnps_periodicite_paiement: cnpsPeriodicitePaiement.value || null,
      cmu_periodicite_paiement: cmuPeriodicitePaiement.value || null,
      dgi_compte_contribuable: dgiCompteContribuable.value || null,
      dgi_centre_impots: dgiCentreImpots.value || null,
      dgi_periodicite_declaration: dgiPeriodiciteDeclaration.value || null,
      dgi_regime_fiscal: dgiRegimeFiscal.value || null
    }

    const res = await put(`/etablissements/${etabId}`, payload)
    if (res) {
      toast.add({
        title: 'Succès',
        description: 'Établissement mis à jour avec succès.',
        color: 'success'
      })
      await fetchEtabDetails()
    }
  } catch (e) {
    console.error(e)
  }
}

const handleCreateCaisse = async () => {
  if (!caisseNom.value) {
    toast.add({
      title: 'Validation',
      description: 'Le nom de la caisse de cotisation est obligatoire.',
      color: 'warning'
    })
    return
  }

  try {
    const payload = {
      nom_caisse: caisseNom.value,
      type_cotisation: caisseType.value,
      code_dsn: caisseDsn.value || null,
      numero_affiliation: caisseAffiliation.value || null,
      iban: caisseIban.value || null,
      bic: caisseBic.value || null
    }

    const res = await post(`/etablissements/${etabId}/caisses`, payload)
    if (res) {
      toast.add({
        title: 'Caisse ajoutée',
        description: 'La caisse de cotisation a été créée avec succès.',
        color: 'success'
      })
      caisseModalOpen.value = false
      // Reset Form
      caisseNom.value = ''
      caisseType.value = 'urssaf'
      caisseDsn.value = ''
      caisseAffiliation.value = ''
      caisseIban.value = ''
      caisseBic.value = ''
      
      await fetchEtabDetails()
    }
  } catch (e) {
    console.error(e)
  }
}

const handleDeleteCaisse = async (caisseId) => {
  if (!confirm('Voulez-vous supprimer cette caisse de cotisation ?')) return
  try {
    await apiDelete(`/caisses/${caisseId}`)
    toast.add({
      title: 'Caisse supprimée',
      description: 'La caisse a été détachée de l\'établissement.',
      color: 'success'
    })
    await fetchEtabDetails()
  } catch (e) {
    console.error(e)
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

const handleCalculateSingle = async (contratId) => {
  try {
    const payload = {
      contrat_id: contratId,
      mois: Number(selectedMois.value),
      annee: Number(selectedAnnee.value),
      acompte: 0.0,
      commentaire: "Généré depuis la gestion des bulletins de l'établissement"
    }
    const res = await post('/bulletins/calculer', payload)
    if (res) {
      toast.add({
        title: 'Bulletin calculé',
        description: `Le bulletin a été généré avec succès.`,
        color: 'success'
      })
      await fetchBulletins()
    }
  } catch (e) {
    console.error(e)
  }
}

const handleValidateSingle = async (bulletinId) => {
  try {
    const res = await put(`/bulletins/${bulletinId}/valider`)
    if (res) {
      toast.add({
        title: 'Bulletin Validé',
        description: 'Le bulletin a été validé définitivement.',
        color: 'success'
      })
      await fetchBulletins()
    }
  } catch (e) {
    console.error(e)
  }
}

const handleDeleteSingle = async (bulletinId) => {
  if (!confirm('Supprimer définitivement ce bulletin de paie ?')) return
  try {
    await apiDelete(`/bulletins/${bulletinId}`)
    toast.add({
      title: 'Bulletin Supprimé',
      description: 'Le bulletin de salaire a été supprimé.',
      color: 'success'
    })
    await fetchBulletins()
  } catch (e) {
    console.error(e)
  }
}

const handleCalculateAll = async () => {
  const pending = contracts.value.filter(c => !bulletinsMap.value[c.id])
  if (pending.length === 0) {
    toast.add({
      title: 'Info',
      description: 'Tous les bulletins de cet établissement sont déjà générés pour cette période.',
      color: 'warning'
    })
    return
  }

  if (!confirm(`Générer les bulletins de paie pour les ${pending.length} salarié(s) en attente dans cet établissement ?`)) return

  bulkProcessing.value = true
  bulkProgress.value = 0
  bulkTotal.value = pending.length

  let successCount = 0
  for (let i = 0; i < pending.length; i++) {
    const c = pending[i]
    try {
      const payload = {
        contrat_id: c.id,
        mois: Number(selectedMois.value),
        annee: Number(selectedAnnee.value),
        acompte: 0.0,
        commentaire: "Calcul groupé automatique"
      }
      await post('/bulletins/calculer', payload)
      successCount++
    } catch (e) {
      console.error(`Error calculating for contract ${c.id}:`, e)
    }
    bulkProgress.value = i + 1
  }

  bulkProcessing.value = false
  toast.add({
    title: 'Génération terminée',
    description: `${successCount} bulletin(s) de salaire calculé(s) avec succès.`,
    color: 'success'
  })
  await fetchBulletins()
}

const handleValidateAll = async () => {
  const drafts = Object.values(bulletinsMap.value).filter(b => {
    return contracts.value.some(c => c.id === b.contrat_id) && b.statut !== 'valide'
  })
  if (drafts.length === 0) {
    toast.add({
      title: 'Info',
      description: 'Aucun bulletin en brouillon à valider pour cet établissement.',
      color: 'warning'
    })
    return
  }

  if (!confirm(`Valider définitivement les ${drafts.length} bulletin(s) en brouillon dans cet établissement ?`)) return

  bulkProcessing.value = true
  bulkProgress.value = 0
  bulkTotal.value = drafts.length

  let successCount = 0
  for (let i = 0; i < drafts.length; i++) {
    const b = drafts[i]
    try {
      await put(`/bulletins/${b.id}/valider`)
      successCount++
    } catch (e) {
      console.error(`Error validating bulletin ${b.id}:`, e)
    }
    bulkProgress.value = i + 1
  }

  bulkProcessing.value = false
  toast.add({
    title: 'Validation terminée',
    description: `${successCount} bulletin(s) validé(s) définitivement.`,
    color: 'success'
  })
  await fetchBulletins()
}

const stats = computed(() => {
  const generatedBulletins = Object.values(bulletinsMap.value).filter(b => {
    return contracts.value.some(c => c.id === b.contrat_id)
  })
  let masseBrut = 0
  let masseNet = 0
  
  generatedBulletins.forEach(b => {
    masseBrut += b.salaire_brut || 0
    masseNet += b.net_a_payer || 0
  })

  return {
    totalEmployees: contracts.value.length,
    generatedCount: generatedBulletins.length,
    pendingCount: contracts.value.length - generatedBulletins.length,
    masseBrut,
    masseNet
  }
})

const formatXOF = (value) => {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'XOF',
    maximumFractionDigits: 0
  }).format(value).replace('XOF', 'FCFA')
}

const getPeriodLabel = (mois, annee) => {
  const months = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
  ]
  return `${months[mois - 1]} ${annee}`
}

watch(() => route.query.tab, (newTab) => {
  if (newTab) {
    activeTab.value = newTab
  } else {
    activeTab.value = 'sals'
  }
})

watch([selectedMois, selectedAnnee], async () => {
  await fetchBulletins()
})

onMounted(() => {
  fetchEtabDetails()
})
</script>

<template>
  <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement de l'établissement...</span>
  </div>

  <div v-else-if="etab" class="space-y-6">


    <!-- Tab 1: Info, Address & Bank + Caisses de cotisation -->
    <div v-show="activeTab === 'infos'" class="space-y-6">
      <form @submit.prevent="handleUpdateEtab" class="space-y-6">
        
        <!-- Main Form -->
        <div class="bg-white border-2 border-slate-200 rounded-none p-6 shadow-flat space-y-4 border-t-4 border-t-slate-500">
          <h3 class="text-sm font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Profil Établissement</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Établissement</label>
              <input v-model="etabCode" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Raison Sociale</label>
              <input v-model="etabNom" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="flex items-center space-x-2 pt-2">
            <input id="is-principal" v-model="etabPrincipal" type="checkbox" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
            <label for="is-principal" class="text-sm font-bold text-slate-700 uppercase tracking-wider">Établissement Principal du dossier</label>
          </div>
        </div>

        <!-- Address Sub-form -->
        <div class="bg-white border-2 border-slate-200 rounded-none p-6 shadow-flat space-y-4 border-t-4 border-t-slate-500">
          <h3 class="text-sm font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Adresse de l'Établissement</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="md:col-span-2">
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Voie / Rue</label>
              <input v-model="addrVoie" type="text" placeholder="Ex: 15 Rue de la Paix" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Complément d'adresse</label>
              <input v-model="addrVoie2" type="text" placeholder="Bâtiment, escalier..." class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Postal</label>
              <input v-model="addrCode" type="text" placeholder="75001" class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Ville</label>
              <input v-model="addrVille" type="text" placeholder="Paris" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Pays</label>
              <input v-model="addrPays" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>
        </div>

        <!-- Bank Sub-form -->
        <div class="bg-white border-2 border-slate-200 rounded-none p-6 shadow-flat space-y-4 border-t-4 border-t-slate-500">
          <h3 class="text-sm font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Informations Bancaires de l'Établissement</h3>
          
          <div class="flex items-center space-x-2 pb-2">
            <input id="bank-virement" v-model="bankVirement" type="checkbox" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
            <label for="bank-virement" class="text-sm font-bold text-slate-700 uppercase tracking-wider">Autoriser le virement SEPA</label>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">IBAN</label>
              <input v-model="bankIban" type="text" placeholder="FR76..." class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code BIC (Swift)</label>
              <input v-model="bankBic" type="text" placeholder="Ex: UBAFRPP..." class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>
        </div>

        <!-- CNPS Sub-form -->
        <div class="bg-white border-2 border-slate-200 rounded-none p-6 shadow-flat space-y-4 border-t-4 border-t-slate-500">
          <h3 class="text-sm font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Caisse Nationale de prévoyance sociale - CNPS</h3>
          
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Matricule employeur</label>
              <input v-model="cnpsMatricule" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code activité</label>
              <input v-model="cnpsCodeActivite" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code agence</label>
              <input v-model="cnpsCodeAgence" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code établissement</label>
              <input v-model="cnpsCodeEtablissement" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div>
            <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Agence de rattachement</label>
            <input v-model="cnpsAgenceRattachement" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Périodicité de paiement - CNPS</label>
              <select v-model="cnpsPeriodicitePaiement" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white select">
                <option value="Mensuelle">Mensuelle</option>
                <option value="Trimestrielle">Trimestrielle</option>
                <option value="Annuelle">Annuelle</option>
              </select>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Périodicité de paiement - CMU</label>
              <select v-model="cmuPeriodicitePaiement" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white select">
                <option value="Mensuelle">Mensuelle</option>
                <option value="Trimestrielle">Trimestrielle</option>
                <option value="Annuelle">Annuelle</option>
              </select>
            </div>
          </div>
        </div>

        <!-- DGI Sub-form -->
        <div class="bg-white border-2 border-slate-200 rounded-none p-6 shadow-flat space-y-4 border-t-4 border-t-slate-500">
          <h3 class="text-sm font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Direction générale des impôts - DGI</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">N° de Compte contribuable</label>
              <input v-model="dgiCompteContribuable" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Centre des impôts</label>
              <input v-model="dgiCentreImpots" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Périodicité des déclarations</label>
              <select v-model="dgiPeriodiciteDeclaration" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white select">
                <option value="Mensuelle">Mensuelle</option>
                <option value="Trimestrielle">Trimestrielle</option>
                <option value="Annuelle">Annuelle</option>
              </select>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Régime fiscal par défaut</label>
              <select v-model="dgiRegimeFiscal" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white select">
                <option value="Régime général">Régime général</option>
                <option value="Régime simplifié">Régime simplifié</option>
                <option value="Impôt synthétique">Impôt synthétique</option>
              </select>
            </div>
          </div>
        </div>

        <div class="flex justify-end">
          <button type="submit" class="px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white font-bold rounded-none shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
            Enregistrer toutes les modifications
          </button>
        </div>
      </form>

      <!-- Caisses de Cotisation Section (Fused at the bottom of General Info) -->
      <div class="bg-white border-2 border-slate-200 rounded-none p-6 shadow-flat border-t-4 border-t-slate-500">
        <div class="flex justify-between items-center border-b border-slate-200 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900 uppercase tracking-wider">Caisses de Cotisation</h3>
            <p class="text-xs text-slate-500">Caisses de cotisations sociales rattachées à cet établissement (CNPS, Retraite...).</p>
          </div>
          <button 
            @click="caisseModalOpen = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-bold rounded-none text-xs transition-colors flex items-center gap-1.5 shadow-flat uppercase tracking-wider cursor-pointer"
          >
            <UIcon name="i-lucide-plus" class="w-3.5 h-3.5" />
            Ajouter une Caisse
          </button>
        </div>

        <!-- Bulk Actions Bar -->
        <div v-if="selectedCaisses.length > 0" class="bg-slate-100 border border-slate-300 p-3 mb-4 flex items-center justify-between text-xs transition-all">
          <div class="font-bold text-slate-700">
            {{ selectedCaisses.length }} caisse(s) sélectionnée(s)
          </div>
          <button 
            @click="handleBulkDeleteCaisses"
            class="p-1.5 bg-red-650 hover:bg-red-755 text-white transition-colors shadow-flat cursor-pointer flex items-center justify-center"
            title="Détacher la sélection"
          >
            <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
          </button>
        </div>

        <!-- Caisses Table -->
        <div v-if="caisses.length === 0" class="text-center py-12 text-slate-500 italic text-sm">
          Aucune caisse rattachée pour le moment.
        </div>
        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left w-10">
                  <input type="checkbox" v-model="allCaissesSelected" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </th>
                <th scope="col" class="px-6 py-3 text-left">Type</th>
                <th scope="col" class="px-6 py-3 text-left">Nom de la Caisse</th>
                <th scope="col" class="px-6 py-3 text-left">Code Organisme</th>
                <th scope="col" class="px-6 py-3 text-left">N° Affiliation</th>
                <th scope="col" class="px-6 py-3 text-left">IBAN / BIC</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="c in caisses" :key="c.id" class="hover:bg-slate-50">
                <td class="px-4 py-4" @click.stop>
                  <input type="checkbox" :value="c.id" v-model="selectedCaisses" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </td>
                <td class="px-6 py-4">
                  <span class="px-2 py-0.5 rounded-none text-xs font-bold bg-green-50 text-green-700 border border-green-200 uppercase">
                    {{ c.type_cotisation }}
                  </span>
                </td>
                <td class="px-6 py-4 font-semibold text-slate-700">{{ c.nom_caisse }}</td>
                <td class="px-6 py-4 font-mono text-slate-500">{{ c.code_dsn || '-' }}</td>
                <td class="px-6 py-4 font-mono text-slate-500">{{ c.numero_affiliation || '-' }}</td>
                <td class="px-6 py-4 text-xs text-slate-500 font-mono">
                  <p v-if="c.iban">IBAN : {{ c.iban }}</p>
                  <p v-if="c.bic">BIC : {{ c.bic }}</p>
                  <span v-if="!c.iban && !c.bic">-</span>
                </td>
                <td class="px-6 py-4 text-right">
                  <button 
                    @click="handleDeleteCaisse(c.id)"
                    class="text-red-650 hover:text-red-750 cursor-pointer flex items-center justify-end w-full"
                    title="Détacher la caisse"
                  >
                    <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Tab 2: Salariés -->
    <div v-show="activeTab === 'sals'" class="space-y-6">
      <div class="bg-white border-2 border-slate-200 rounded-none p-6 shadow-flat border-t-4 border-t-slate-500">
        
        <div class="flex justify-between items-center border-b border-slate-200 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900 uppercase tracking-wider">Salariés de l'Établissement</h3>
            <p class="text-xs text-slate-500">Liste des fiches civiles des salariés déclarés dans cet établissement.</p>
          </div>
          <button 
            @click="router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/new`)"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-bold rounded-none text-xs transition-colors flex items-center gap-1.5 shadow-flat uppercase tracking-wider cursor-pointer"
          >
            <UIcon name="i-lucide-user-plus" class="w-3.5 h-3.5" />
            Ajouter un Salarié
          </button>
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
        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left w-10">
                  <input type="checkbox" v-model="allSalariesSelected" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
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
                v-for="sal in salaries" 
                :key="sal.id" 
                @click="router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${sal.id}`)"
                class="hover:bg-slate-50/55 cursor-pointer group"
              >
                <td class="px-4 py-4" @click.stop>
                  <input type="checkbox" :value="sal.id" v-model="selectedSalaries" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </td>
                <td class="px-6 py-4 font-mono font-semibold text-slate-900">{{ sal.matricule }}</td>
                <td class="px-6 py-4 font-medium text-slate-700 group-hover:text-green-700 transition-colors">
                  {{ sal.nom.toUpperCase() }} {{ sal.prenom }}
                </td>
                <td class="px-6 py-4 font-mono text-slate-500">{{ sal.numero_securite_sociale || '-' }}</td>
                <td class="px-6 py-4 text-slate-500">{{ sal.email || '-' }}</td>
                <td class="px-6 py-4 text-slate-500 font-mono">{{ sal.telephone || '-' }}</td>
                <td class="px-6 py-4">
                  <span 
                    :class="[
                      sal.is_active ? 'bg-green-50 text-green-700 border-green-200' : 'bg-slate-100 text-slate-500 border-slate-200',
                      'px-2 py-0.5 rounded-none text-xs font-semibold border'
                    ]"
                  >
                    {{ sal.is_active ? 'Actif' : 'Inactif' }}
                  </span>
                </td>
                <td class="px-6 py-4 text-right">
                  <span class="text-green-600 group-hover:underline text-xs font-bold uppercase tracking-wider flex items-center justify-end gap-1">
                    Fiche Salarié
                    <UIcon name="i-lucide-chevron-right" class="w-4 h-4" />
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>
    </div>

    <!-- Tab 3: Contrats -->
    <div v-show="activeTab === 'contrats'" class="space-y-6">
      <div class="bg-white border-2 border-slate-200 rounded-none p-6 shadow-flat border-t-4 border-t-slate-500">
        
        <div class="flex justify-between items-center border-b border-slate-200 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900 uppercase tracking-wider">Contrats de l'Établissement</h3>
            <p class="text-xs text-slate-500">Historique des contrats de travail rattachés à cet établissement.</p>
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
        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left w-10">
                  <input type="checkbox" v-model="allContractsSelected" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
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
                v-for="c in contracts" 
                :key="c.id" 
                @click="router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${c.salarie_id}/contrats/${c.id}`)"
                class="hover:bg-slate-50 cursor-pointer group"
              >
                <td class="px-4 py-4" @click.stop>
                  <input type="checkbox" :value="c.id" v-model="selectedContracts" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </td>
                <td class="px-6 py-4 font-mono font-semibold text-slate-900">{{ c.numero_contrat }}</td>
                <td class="px-6 py-4 font-medium text-slate-700 group-hover:text-green-700 transition-colors">
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
                      'px-2 py-0.5 rounded-none text-[10px] uppercase font-bold border'
                    ]"
                  >
                    {{ c.statut }}
                  </span>
                </td>
                <td class="px-6 py-4 text-right">
                  <span class="text-green-600 group-hover:underline text-xs font-bold uppercase tracking-wider flex items-center justify-end gap-1">
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
      <!-- Title & Mass Actions Header -->
     

      <!-- Period Filter Bar -->
      <div class="bg-white border-2 border-slate-200 p-4 shadow-flat flex flex-col md:flex-row justify-between items-center gap-4">
        <div class="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
          <span class="text-xs font-bold uppercase tracking-wider text-slate-400 shrink-0">Période de Paie :</span>
          <div class="flex space-x-3 w-full sm:w-auto">
            <select v-model="selectedMois" class="block w-full sm:w-40 px-3 py-2 border border-slate-350 rounded-none text-sm bg-white select">
              <option v-for="m in 12" :key="m" :value="m">{{ getPeriodLabel(m, 2026).split(' ')[0] }}</option>
            </select>
            <input 
              v-model="selectedAnnee" 
              type="number" 
              placeholder="Année" 
              class="block w-full sm:w-28 px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" 
            />
          </div>
        </div>
        <div v-if="contracts.length > 0" class="flex flex-wrap gap-3 w-full md:w-auto justify-end">
          <button 
            @click="handleValidateAll"
            :disabled="bulkProcessing || stats.generatedCount === 0"
            class="px-4 py-2 border-2 border-slate-200 text-xs font-bold uppercase tracking-wider hover:bg-slate-50 text-slate-700 transition-all flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-flat-hover shadow-flat-active"
          >
            <UIcon name="i-lucide-check-circle-2" class="w-4 h-4 text-green-600" />
            Valider la période
          </button>
          <button 
            @click="handleCalculateAll"
            :disabled="bulkProcessing || stats.pendingCount === 0"
            class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-xs font-bold uppercase tracking-wider shadow-flat transition-all flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-flat-hover shadow-flat-active"
          >
            <UIcon name="i-lucide-calculator" class="w-4 h-4" />
            Calculer les bulletins
          </button>
        </div>
      </div>

      <!-- Bulk action progress -->
      <div v-if="bulkProcessing" class="bg-white border-2 border-slate-200 p-4 shadow-flat space-y-2">
        <div class="flex justify-between text-xs font-semibold text-slate-700">
          <span>Traitement groupé des fiches de paye de l'établissement...</span>
          <span>{{ bulkProgress }} / {{ bulkTotal }} ({{ Math.round((bulkProgress / bulkTotal) * 100) }}%)</span>
        </div>
        <div class="w-full bg-slate-100 h-2 overflow-hidden">
          <div class="bg-green-600 h-full transition-all duration-300" :style="{ width: `${(bulkProgress / bulkTotal) * 100}%` }"></div>
        </div>
      </div>

      <!-- Statistics cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-white border-2 border-slate-200 p-5 shadow-flat space-y-2 border-t-4 border-t-slate-500">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Effectif Établissement</span>
            <div class="w-7 h-7 bg-slate-100 text-slate-600 rounded-none flex items-center justify-center">
              <UIcon name="i-lucide-users" class="w-4 h-4" />
            </div>
          </div>
          <p class="text-2xl font-bold text-slate-900">{{ stats.totalEmployees }} salariés</p>
          <div class="text-[10px] text-slate-450 font-sans">Avec contrat actif rattaché</div>
        </div>

        <div class="bg-white border-2 border-slate-200 p-5 shadow-flat space-y-2 border-t-4 border-t-green-600">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Bulletins Calculés</span>
            <div class="w-7 h-7 bg-green-50 text-green-700 rounded-none flex items-center justify-center">
              <UIcon name="i-lucide-check-circle-2" class="w-4 h-4" />
            </div>
          </div>
          <p class="text-2xl font-bold text-slate-900">{{ stats.generatedCount }} / {{ stats.totalEmployees }}</p>
          <div class="text-[10px] text-slate-450 flex items-center gap-1">
            <span v-if="stats.pendingCount > 0" class="text-yellow-600 font-semibold flex items-center gap-0.5">
              <span class="w-1.5 h-1.5 rounded-full bg-yellow-500 inline-block animate-pulse"></span>
              {{ stats.pendingCount }} en attente
            </span>
            <span v-else class="text-green-600 font-semibold flex items-center gap-0.5">
              Tous générés
            </span>
          </div>
        </div>

        <div class="bg-white border-2 border-slate-200 p-5 shadow-flat space-y-2 border-t-4 border-t-blue-500">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Masse Brut</span>
            <div class="w-7 h-7 bg-blue-50 text-blue-700 rounded-none flex items-center justify-center">
              <UIcon name="i-lucide-coins" class="w-4 h-4" />
            </div>
          </div>
          <p class="text-2xl font-bold text-slate-900 font-mono tracking-tight">{{ formatXOF(stats.masseBrut) }}</p>
          <div class="text-[10px] text-slate-450 font-sans">Brut total sur la période</div>
        </div>

        <div class="bg-white border-2 border-slate-200 p-5 shadow-flat space-y-2 border-t-4 border-t-emerald-600">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Masse Nette</span>
            <div class="w-7 h-7 bg-emerald-50 text-emerald-700 rounded-none flex items-center justify-center">
              <UIcon name="i-lucide-banknote" class="w-4 h-4" />
            </div>
          </div>
          <p class="text-2xl font-bold text-green-700 font-mono tracking-tight">{{ formatXOF(stats.masseNet) }}</p>
          <div class="text-[10px] text-slate-450 font-sans">Net total sur la période</div>
        </div>
      </div>

      <!-- Bulk Actions Bar for Bulletins -->
      <div v-if="selectedBulletins.length > 0" class="bg-slate-100 border border-slate-350 p-4 flex flex-col sm:flex-row justify-between items-center gap-3 text-xs transition-all mb-4">
        <div class="font-bold text-slate-700">
          {{ selectedBulletins.length }} bulletin(s) sélectionné(s)
        </div>
        <div class="flex flex-wrap gap-2 justify-end w-full sm:w-auto">
          <button 
            @click="handleCalculateSelected"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-bold uppercase tracking-wider transition-colors shadow-flat cursor-pointer"
          >
            <UIcon name="i-lucide-calculator" class="w-3.5 h-3.5 inline mr-1" />
            Calculer
          </button>
          <button 
            @click="handleValidateSelected"
            class="px-3 py-1.5 bg-yellow-500 hover:bg-yellow-600 text-slate-900 font-bold uppercase tracking-wider transition-colors shadow-flat cursor-pointer"
          >
            <UIcon name="i-lucide-check-circle" class="w-3.5 h-3.5 inline mr-1" />
            Valider
          </button>
          <button 
            @click="handleDeleteSelectedBulletins"
            class="p-1.5 bg-red-650 hover:bg-red-755 text-white transition-colors shadow-flat cursor-pointer flex items-center justify-center"
            title="Supprimer"
          >
            <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Bulletins Table Card -->
      <div class="bg-white border-2 border-slate-200 shadow-flat overflow-hidden border-t-4 border-t-slate-500">
        <div v-if="contracts.length === 0" class="text-center py-16 px-4 bg-white space-y-3">
          <div class="w-10 h-10 bg-slate-100 text-slate-400 rounded-none flex items-center justify-center mx-auto">
            <UIcon name="i-lucide-user-x" class="w-5 h-5" />
          </div>
          <h4 class="font-bold text-slate-800">Aucun salarié avec contrat actif</h4>
          <p class="text-xs text-slate-500 max-w-sm mx-auto">
            Pour générer des bulletins de paie, vous devez d'abord associer des salariés avec des contrats de travail actifs dans cet établissement.
          </p>
        </div>

        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left w-10">
                  <input type="checkbox" v-model="allBulletinsSelected" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </th>
                <th scope="col" class="px-6 py-3 text-left">Employé</th>
                <th scope="col" class="px-6 py-3 text-left">Poste / Contrat</th>
                <th scope="col" class="px-6 py-3 text-left">Statut Bulletin</th>
                <th scope="col" class="px-6 py-3 text-right">Salaire Brut</th>
                <th scope="col" class="px-6 py-3 text-right">Net à Payer</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="c in contracts" :key="c.id" class="hover:bg-slate-50/50 transition-colors">
                <td class="px-4 py-4" @click.stop>
                  <input type="checkbox" :value="c.id" v-model="selectedBulletins" class="rounded-none border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </td>
                <!-- Employee -->
                <td class="px-6 py-4">
                  <div class="flex items-center space-x-3">
                    <div class="w-8 h-8 bg-green-50 text-green-700 rounded-none flex items-center justify-center font-bold text-xs border border-green-200">
                      {{ c.matricule_salarie.substring(c.matricule_salarie.lastIndexOf('-') + 1) || 'EMP' }}
                    </div>
                    <div>
                      <span class="block font-bold text-slate-900 leading-tight">
                        {{ getSalarieName(c.salarie_id) }}
                      </span>
                      <span class="text-xs text-slate-500 font-mono">
                        {{ c.matricule_salarie }}
                      </span>
                    </div>
                  </div>
                </td>

                <!-- Job / Contract -->
                <td class="px-6 py-4">
                  <span class="block font-medium text-slate-800 leading-tight">
                    {{ c.emploi || 'Poste non renseigné' }}
                  </span>
                  <span class="text-[10px] font-mono text-slate-450">
                    Contrat N° {{ c.numero_contrat }}
                  </span>
                </td>

                <!-- Status -->
                <td class="px-6 py-4">
                  <span 
                    v-if="bulletinsMap[c.id]"
                    :class="[
                      bulletinsMap[c.id].statut === 'valide' 
                        ? 'bg-green-50 text-green-700 border-green-200' 
                        : 'bg-yellow-50 text-yellow-700 border-yellow-200',
                      'px-2.5 py-0.5 rounded-none text-[10px] uppercase font-bold border inline-block tracking-wider'
                    ]"
                  >
                    {{ bulletinsMap[c.id].statut }}
                  </span>
                  <span 
                    v-else 
                    class="bg-slate-100 text-slate-400 border-slate-200 px-2.5 py-0.5 rounded-none text-[10px] uppercase font-bold border inline-block tracking-wider"
                  >
                    Non calculé
                  </span>
                </td>

                <!-- Salaire Brut -->
                <td class="px-6 py-4 text-right font-mono text-slate-650 font-medium">
                  {{ bulletinsMap[c.id] ? formatXOF(bulletinsMap[c.id].salaire_brut) : '-' }}
                </td>

                <!-- Net à payer -->
                <td class="px-6 py-4 text-right font-mono font-bold text-slate-900">
                  {{ bulletinsMap[c.id] ? formatXOF(bulletinsMap[c.id].net_a_payer) : '-' }}
                </td>

                <!-- Actions -->
                <td class="px-6 py-4 text-right">
                  <div class="flex justify-end items-center space-x-2">
                    <template v-if="bulletinsMap[c.id]">
                      <!-- View Link -->
                      <NuxtLink 
                        :to="`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${c.salarie_id}/contrats/${c.id}/bulletins/${bulletinsMap[c.id].id}`"
                        class="px-2.5 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-none text-xs font-bold transition-colors flex items-center gap-1 uppercase tracking-wider"
                      >
                        <UIcon name="i-lucide-eye" class="w-3.5 h-3.5" />
                        Voir
                      </NuxtLink>

                      <!-- Recalculate -->
                      <button 
                        v-if="bulletinsMap[c.id].statut !== 'valide'"
                        @click="handleCalculateSingle(c.id)"
                        class="px-2.5 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 transition-colors rounded-none text-xs font-bold flex items-center gap-1 uppercase tracking-wider cursor-pointer"
                        title="Recalculer le bulletin"
                      >
                        <UIcon name="i-lucide-refresh-cw" class="w-3.5 h-3.5 text-green-600" />
                        Recalculer
                      </button>

                      <!-- Validate -->
                      <button 
                        v-if="bulletinsMap[c.id].statut !== 'valide'"
                        @click="handleValidateSingle(bulletinsMap[c.id].id)"
                        class="px-2.5 py-1.5 border border-yellow-250 bg-yellow-50 hover:bg-yellow-100 text-yellow-750 transition-colors rounded-none text-xs font-bold flex items-center gap-1 uppercase tracking-wider cursor-pointer"
                        title="Valider définitivement"
                      >
                        <UIcon name="i-lucide-check-circle" class="w-3.5 h-3.5 text-yellow-600" />
                        Valider
                      </button>

                      <!-- Delete -->
                      <button 
                        v-if="bulletinsMap[c.id].statut !== 'valide'"
                        @click="handleDeleteSingle(bulletinsMap[c.id].id)"
                        class="px-2.5 py-1.5 border border-red-200 bg-red-50 hover:bg-red-100 text-red-650 transition-colors rounded-none cursor-pointer flex items-center justify-center"
                        title="Supprimer"
                      >
                        <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
                      </button>
                    </template>

                    <button 
                      v-else
                      @click="handleCalculateSingle(c.id)"
                      class="px-2.5 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-none text-xs font-bold transition-colors flex items-center gap-1 shadow-flat uppercase tracking-wider cursor-pointer"
                    >
                      <UIcon name="i-lucide-calculator" class="w-3.5 h-3.5" />
                      Calculer
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Modal: Add Caisse -->
    <UModal v-model:open="caisseModalOpen" title="Rattacher une Caisse de Cotisation">
      <template #content>
        <div class="p-6 space-y-4 bg-white border border-slate-200">
          <h2 class="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Nouvelle Caisse</h2>
          
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Type de cotisation</label>
              <select v-model="caisseType" class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-none text-sm bg-white select">
                <option value="urssaf">CNPS (Sécurité Sociale)</option>
                <option value="retraite_complementaire">Retraite Complémentaire</option>
                <option value="prevoyance">Prévoyance / Mutuelle</option>
                <option value="autre">Autre</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom de la Caisse <span class="text-red-500">*</span></label>
              <input v-model="caisseNom" type="text" placeholder="Ex: URSSAF IDF" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Organisme</label>
              <input v-model="caisseDsn" type="text" placeholder="Ex: CNPS-01" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Numéro d'Affiliation</label>
              <input v-model="caisseAffiliation" type="text" placeholder="Ex: AFF12345" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4 border-t border-slate-200 pt-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">IBAN de Règlement</label>
              <input v-model="caisseIban" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">BIC</label>
              <input v-model="caisseBic" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button type="button" @click="caisseModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-none hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
              Annuler
            </button>
            <button type="button" @click="handleCreateCaisse" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-none shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
              Rattacher la caisse
            </button>
          </div>
        </div>
      </template>
    </UModal>

  </div>
</template>

<style scoped>
.select {
  appearance: none;
  background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236B7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='m6 8 4 4 4-4'/%3E%3C/svg%3E");
  background-position: right 0.5rem center;
  background-repeat: no-repeat;
  background-size: 1.25em 1.25em;
  padding-right: 2.5rem;
}
</style>
