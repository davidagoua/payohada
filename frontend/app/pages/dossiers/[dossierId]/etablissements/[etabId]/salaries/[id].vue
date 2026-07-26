<script setup>
const route = useRoute()
const router = useRouter()
const { get, put, post, delete: apiDelete, extractFieldErrors } = useApi()
const toast = useToast()
const fieldErrors = ref({})

const dossierId = route.params.dossierId
const etabId = route.params.etabId
const salarieId = route.params.id

const sal = ref(null)
const contrats = ref([])
const loading = ref(true)
const activeTab = ref('infos')

// Reactive lists for new HR tabs
const entretiens = ref([])
const visites = ref([])
const formations = ref([])
const absences = ref([])
const prets = ref([])
const contratsHr = ref([])
const services = ref([])
const archivages = ref([])
const dossierDepartements = ref([])

// Form visibility toggles
const showEntretienForm = ref(false)
const showVisiteForm = ref(false)
const showFormationForm = ref(false)
const showAbsenceForm = ref(false)
const showPretForm = ref(false)
const showContratHrForm = ref(false)
const showServiceForm = ref(false)
const showArchivageForm = ref(false)

// Edit state indicators
const editingEntretien = ref(null)
const editingVisite = ref(null)
const editingFormation = ref(null)
const editingAbsence = ref(null)
const editingPret = ref(null)
const editingContratHr = ref(null)
const editingService = ref(null)
const editingArchivage = ref(null)

// Form models
const formEntretien = ref({ date_entretien: '', nom_evaluateur: '', note_globale: null, commentaires: '' })
const formVisite = ref({ date_visite: '', type_visite: 'Embauche', aptitude: 'Apte', prochaine_visite: '' })
const formFormation = ref({ intitule_formation: '', organisme: '', date_debut: '', date_fin: '', statut_formation: 'Demandée' })
const formAbsence = ref({ type_absence: 'Congés payés', date_debut_absence: '', date_fin_absence: '', justificatif_fourni: false })
const formPret = ref({ montant_pret: 0, date_deblocage: '', montant_mensualite: 0, reste_a_rembourser: 0 })
const formContratHr = ref({ type_contrat: 'CDI', date_embauche: '', date_fin_contrat: '', fin_periode_essai: '' })
const formService = ref({ departement: '', poste_occupe: '', manager: '', dotation_materiel: '' })
const formArchivage = ref({ type_document: '', fichier_joint: '', date_ajout: '' })

// File upload state
const selectedFile = ref(null)
const config = useRuntimeConfig()
const apiBase = config.public.apiBase || 'http://localhost:8000'

const onFileSelected = (event) => {
  selectedFile.value = event.target.files[0]
}

// Computed tabs list
const tabs = computed(() => [
  { id: 'infos', label: 'État Civil / Fiche' },
  { id: 'contrats', label: `Contrats (${contrats.value.length})` },
  { id: 'entretiens', label: `Entretiens (${entretiens.value.length})` },
  { id: 'sante', label: `Visites Médicales (${visites.value.length})` },
  { id: 'formations', label: `Formations (${formations.value.length})` },
  { id: 'absences', label: `Absences (${absences.value.length})` },
  { id: 'prets', label: `Prêts (${prets.value.length})` },
  { id: 'contrats_hr', label: `Contrats HR (${contratsHr.value.length})` },
  { id: 'services', label: `Services (${services.value.length})` },
  { id: 'archivage', label: `Archivage (${archivages.value.length})` }
])

// Global State for breadcrumbs
const currentDossier = useState('current-dossier')

// Salarie Edit Form Fields
const salMatricule = ref('')
const salNom = ref('')
const salPrenom = ref('')
const salNomUsage = ref('')
const salCivilite = ref('M.')
const salDateNaissance = ref('')
const salLieuNaissance = ref('')
const salDeptNaissance = ref('')
const salPaysNaissance = ref('')
const salNationalite = ref('')
const salNir = ref('')
const salAdresse = ref('')
const salAdresse2 = ref('')
const salCodePostal = ref('')
const salVille = ref('')
const salPays = ref('Côte d\'Ivoire')
const salEmail = ref('')
const salPhone = ref('')
const salIban = ref('')
const salBic = ref('')
const salIsActive = ref(true)
const salExpatrie = ref(false)
const salSituationMatrimoniale = ref('Célibataire')
const salEnfantsCharge = ref(0)


const fetchSalarieDetails = async () => {
  loading.value = true
  try {
    // Ensure parent dossier context is loaded
    if (!currentDossier.value) {
      const parentDossier = await get(`/dossiers/${dossierId}`)
      currentDossier.value = parentDossier
    }

    const data = await get(`/salaries/${salarieId}`)
    sal.value = data

    // Populate Fields
    salMatricule.value = data.matricule || ''
    salNom.value = data.nom || ''
    salPrenom.value = data.prenom || ''
    salNomUsage.value = data.nom_usage || ''
    salCivilite.value = data.civilite || 'M.'
    
    if (data.date_naissance) {
      salDateNaissance.value = data.date_naissance.substring(0, 10)
    } else {
      salDateNaissance.value = ''
    }
    
    salLieuNaissance.value = data.lieu_naissance || ''
    salDeptNaissance.value = data.departement_naissance || ''
    salPaysNaissance.value = data.pays_naissance || ''
    salNationalite.value = data.nationalite || ''
    salNir.value = data.numero_securite_sociale || ''
    salAdresse.value = data.adresse || ''
    salAdresse2.value = data.adresse2 || ''
    salCodePostal.value = data.code_postal || ''
    salVille.value = data.ville || ''
    salPays.value = data.pays || "Côte d'Ivoire"
    salEmail.value = data.email || ''
    salPhone.value = data.telephone || ''
    salIban.value = data.iban || ''
    salBic.value = data.bic || ''
    salIsActive.value = data.is_active ?? true
    salExpatrie.value = data.expatrie ?? false
    salSituationMatrimoniale.value = data.situation_matrimoniale || 'Célibataire'
    salEnfantsCharge.value = data.enfants_charge ?? 0

    // Fetch Contracts
    const cts = await get(`/salaries/${salarieId}/contrats`)
    contrats.value = cts || []

    // Fetch new HR details
    try {
      const [entList, visList, formList, absList, pretList, cHrList, servList, archList, deptsList] = await Promise.all([
        get(`/salaries/${salarieId}/entretiens`),
        get(`/salaries/${salarieId}/visites-medicales`),
        get(`/salaries/${salarieId}/formations`),
        get(`/salaries/${salarieId}/absences-hr`),
        get(`/salaries/${salarieId}/prets`),
        get(`/salaries/${salarieId}/contrats-info`),
        get(`/salaries/${salarieId}/services`),
        get(`/salaries/${salarieId}/archivages`),
        get(`/dossiers/${dossierId}/departements`)
      ])
      entretiens.value = entList || []
      visites.value = visList || []
      formations.value = formList || []
      absences.value = absList || []
      prets.value = pretList || []
      contratsHr.value = cHrList || []
      services.value = servList || []
      archivages.value = archList || []
      dossierDepartements.value = deptsList || []
    } catch (err) {
      console.error("Erreur lors de la récupération des infos RH complémentaires:", err)
    }

  } catch (e) {
    console.error(e)
    router.push(`/dossiers/${dossierId}/etablissements/${etabId}`)
  } finally {
    loading.value = false
  }
}

const handleUpdateSalarie = async () => {
  fieldErrors.value = {}
  if (!salNom.value || !salPrenom.value) {
    toast.add({
      title: 'Validation',
      description: 'Le nom et le prénom du salarié sont obligatoires.',
      color: 'warning'
    })
    return
  }

  try {
    const payload = {
      nom: salNom.value,
      prenom: salPrenom.value,
      nom_usage: salNomUsage.value || null,
      civilite: salCivilite.value,
      date_naissance: salDateNaissance.value ? new Date(salDateNaissance.value).toISOString() : null,
      lieu_naissance: salLieuNaissance.value || null,
      departement_naissance: salDeptNaissance.value || null,
      pays_naissance: salPaysNaissance.value || null,
      nationalite: salNationalite.value || null,
      numero_securite_sociale: salNir.value || null,
      adresse: salAdresse.value || null,
      adresse2: salAdresse2.value || null,
      code_postal: salCodePostal.value || null,
      ville: salVille.value || null,
      pays: salPays.value || "Côte d'Ivoire",
      email: salEmail.value || null,
      telephone: salPhone.value || null,
      iban: salIban.value || null,
      bic: salBic.value || null,
      is_active: salIsActive.value,
      expatrie: salExpatrie.value,
      situation_matrimoniale: salSituationMatrimoniale.value,
      enfants_charge: salEnfantsCharge.value
    }

    const res = await put(`/salaries/${salarieId}`, payload)
    if (res) {
      toast.add({
        title: 'Mis à jour',
        description: 'Fiche du salarié enregistrée avec succès.',
        color: 'success'
      })
      await fetchSalarieDetails()
    }
  } catch (e) {
    console.error(e)
    if (e.status === 422) {
      fieldErrors.value = extractFieldErrors(e)
    }
  }
}


const handleDeleteSalarie = async () => {
  if (!confirm('Supprimer définitivement ce salarié et tous ses contrats associés ?')) return
  try {
    await apiDelete(`/salaries/${salarieId}`)
    toast.add({
      title: 'Salarié supprimé',
      description: 'La fiche salarié a été supprimée.',
      color: 'success'
    })
    router.push(`/dossiers/${dossierId}/etablissements/${etabId}`)
  } catch (e) {
    console.error(e)
  }
}

// CRUD Handlers for new tabs
const saveEntretien = async () => {
  try {
    const payload = { ...formEntretien.value }
    if (editingEntretien.value) {
      await put(`/salaries/entretiens/${editingEntretien.value.id}`, payload)
      toast.add({ title: 'Succès', description: 'Entretien mis à jour avec succès.', color: 'success' })
    } else {
      await post(`/salaries/${salarieId}/entretiens`, payload)
      toast.add({ title: 'Succès', description: 'Entretien enregistré avec succès.', color: 'success' })
    }
    showEntretienForm.value = false
    editingEntretien.value = null
    formEntretien.value = { date_entretien: '', nom_evaluateur: '', note_globale: null, commentaires: '' }
    entretiens.value = await get(`/salaries/${salarieId}/entretiens`)
  } catch (e) {
    console.error(e)
  }
}
const editEntretien = (item) => {
  editingEntretien.value = item
  formEntretien.value = {
    date_entretien: item.date_entretien ? item.date_entretien.substring(0, 10) : '',
    nom_evaluateur: item.nom_evaluateur,
    note_globale: item.note_globale,
    commentaires: item.commentaires
  }
  showEntretienForm.value = true
}
const deleteEntretien = async (id) => {
  if (!confirm('Supprimer cet entretien définitivement ?')) return
  try {
    await apiDelete(`/salaries/entretiens/${id}`)
    toast.add({ title: 'Succès', description: 'Entretien supprimé.', color: 'success' })
    entretiens.value = await get(`/salaries/${salarieId}/entretiens`)
  } catch (e) {
    console.error(e)
  }
}
const cancelEntretien = () => {
  showEntretienForm.value = false
  editingEntretien.value = null
  formEntretien.value = { date_entretien: '', nom_evaluateur: '', note_globale: null, commentaires: '' }
}

// Visites
const saveVisite = async () => {
  try {
    const payload = { ...formVisite.value }
    if (editingVisite.value) {
      await put(`/salaries/visites-medicales/${editingVisite.value.id}`, payload)
      toast.add({ title: 'Succès', description: 'Visite médicale mise à jour.', color: 'success' })
    } else {
      await post(`/salaries/${salarieId}/visites-medicales`, payload)
      toast.add({ title: 'Succès', description: 'Visite médicale enregistrée.', color: 'success' })
    }
    showVisiteForm.value = false
    editingVisite.value = null
    formVisite.value = { date_visite: '', type_visite: 'Embauche', aptitude: 'Apte', prochaine_visite: '' }
    visites.value = await get(`/salaries/${salarieId}/visites-medicales`)
  } catch (e) {
    console.error(e)
  }
}
const editVisite = (item) => {
  editingVisite.value = item
  formVisite.value = {
    date_visite: item.date_visite ? item.date_visite.substring(0, 10) : '',
    type_visite: item.type_visite,
    aptitude: item.aptitude,
    prochaine_visite: item.prochaine_visite ? item.prochaine_visite.substring(0, 10) : ''
  }
  showVisiteForm.value = true
}
const deleteVisite = async (id) => {
  if (!confirm('Supprimer cette visite médicale ?')) return
  try {
    await apiDelete(`/salaries/visites-medicales/${id}`)
    toast.add({ title: 'Succès', description: 'Visite médicale supprimée.', color: 'success' })
    visites.value = await get(`/salaries/${salarieId}/visites-medicales`)
  } catch (e) {
    console.error(e)
  }
}
const cancelVisite = () => {
  showVisiteForm.value = false
  editingVisite.value = null
  formVisite.value = { date_visite: '', type_visite: 'Embauche', aptitude: 'Apte', prochaine_visite: '' }
}

// Formations
const saveFormation = async () => {
  try {
    const payload = { ...formFormation.value }
    if (editingFormation.value) {
      await put(`/salaries/formations/${editingFormation.value.id}`, payload)
      toast.add({ title: 'Succès', description: 'Formation mise à jour.', color: 'success' })
    } else {
      await post(`/salaries/${salarieId}/formations`, payload)
      toast.add({ title: 'Succès', description: 'Formation enregistrée.', color: 'success' })
    }
    showFormationForm.value = false
    editingFormation.value = null
    formFormation.value = { intitule_formation: '', organisme: '', date_debut: '', date_fin: '', statut_formation: 'Demandée' }
    formations.value = await get(`/salaries/${salarieId}/formations`)
  } catch (e) {
    console.error(e)
  }
}
const editFormation = (item) => {
  editingFormation.value = item
  formFormation.value = {
    intitule_formation: item.intitule_formation,
    organisme: item.organisme,
    date_debut: item.date_debut ? item.date_debut.substring(0, 10) : '',
    date_fin: item.date_fin ? item.date_fin.substring(0, 10) : '',
    statut_formation: item.statut_formation
  }
  showFormationForm.value = true
}
const deleteFormation = async (id) => {
  if (!confirm('Supprimer cette formation ?')) return
  try {
    await apiDelete(`/salaries/formations/${id}`)
    toast.add({ title: 'Succès', description: 'Formation supprimée.', color: 'success' })
    formations.value = await get(`/salaries/${salarieId}/formations`)
  } catch (e) {
    console.error(e)
  }
}
const cancelFormation = () => {
  showFormationForm.value = false
  editingFormation.value = null
  formFormation.value = { intitule_formation: '', organisme: '', date_debut: '', date_fin: '', statut_formation: 'Demandée' }
}

// Absences
const saveAbsence = async () => {
  try {
    const payload = { ...formAbsence.value }
    if (editingAbsence.value) {
      await put(`/salaries/absences-hr/${editingAbsence.value.id}`, payload)
      toast.add({ title: 'Succès', description: 'Absence mise à jour.', color: 'success' })
    } else {
      await post(`/salaries/${salarieId}/absences-hr`, payload)
      toast.add({ title: 'Succès', description: 'Absence enregistrée.', color: 'success' })
    }
    showAbsenceForm.value = false
    editingAbsence.value = null
    formAbsence.value = { type_absence: 'Congés payés', date_debut_absence: '', date_fin_absence: '', justificatif_fourni: false }
    absences.value = await get(`/salaries/${salarieId}/absences-hr`)
  } catch (e) {
    console.error(e)
  }
}
const editAbsence = (item) => {
  editingAbsence.value = item
  formAbsence.value = {
    type_absence: item.type_absence,
    date_debut_absence: item.date_debut_absence ? item.date_debut_absence.substring(0, 10) : '',
    date_fin_absence: item.date_fin_absence ? item.date_fin_absence.substring(0, 10) : '',
    justificatif_fourni: item.justificatif_fourni
  }
  showAbsenceForm.value = true
}
const deleteAbsence = async (id) => {
  if (!confirm('Supprimer cette absence ?')) return
  try {
    await apiDelete(`/salaries/absences-hr/${id}`)
    toast.add({ title: 'Succès', description: 'Absence supprimée.', color: 'success' })
    absences.value = await get(`/salaries/${salarieId}/absences-hr`)
  } catch (e) {
    console.error(e)
  }
}
const cancelAbsence = () => {
  showAbsenceForm.value = false
  editingAbsence.value = null
  formAbsence.value = { type_absence: 'Congés payés', date_debut_absence: '', date_fin_absence: '', justificatif_fourni: false }
}

// Prêts
const savePret = async () => {
  try {
    const payload = { ...formPret.value }
    if (editingPret.value) {
      await put(`/salaries/prets/${editingPret.value.id}`, payload)
      toast.add({ title: 'Succès', description: 'Prêt mis à jour.', color: 'success' })
    } else {
      await post(`/salaries/${salarieId}/prets`, payload)
      toast.add({ title: 'Succès', description: 'Prêt enregistré.', color: 'success' })
    }
    showPretForm.value = false
    editingPret.value = null
    formPret.value = { montant_pret: 0, date_deblocage: '', montant_mensualite: 0, reste_a_rembourser: 0 }
    prets.value = await get(`/salaries/${salarieId}/prets`)
  } catch (e) {
    console.error(e)
  }
}
const editPret = (item) => {
  editingPret.value = item
  formPret.value = {
    montant_pret: item.montant_pret,
    date_deblocage: item.date_deblocage ? item.date_deblocage.substring(0, 10) : '',
    montant_mensualite: item.montant_mensualite,
    reste_a_rembourser: item.reste_a_rembourser
  }
  showPretForm.value = true
}
const deletePret = async (id) => {
  if (!confirm('Supprimer ce prêt ?')) return
  try {
    await apiDelete(`/salaries/prets/${id}`)
    toast.add({ title: 'Succès', description: 'Prêt supprimé.', color: 'success' })
    prets.value = await get(`/salaries/${salarieId}/prets`)
  } catch (e) {
    console.error(e)
  }
}
const cancelPret = () => {
  showPretForm.value = false
  editingPret.value = null
  formPret.value = { montant_pret: 0, date_deblocage: '', montant_mensualite: 0, reste_a_rembourser: 0 }
}

// Contrats HR
const saveContratHr = async () => {
  try {
    const payload = { ...formContratHr.value }
    if (editingContratHr.value) {
      await put(`/salaries/contrats-info/${editingContratHr.value.id}`, payload)
      toast.add({ title: 'Succès', description: 'Infos contrat mises à jour.', color: 'success' })
    } else {
      await post(`/salaries/${salarieId}/contrats-info`, payload)
      toast.add({ title: 'Succès', description: 'Infos contrat enregistrées.', color: 'success' })
    }
    showContratHrForm.value = false
    editingContratHr.value = null
    formContratHr.value = { type_contrat: 'CDI', date_embauche: '', date_fin_contrat: '', fin_periode_essai: '' }
    contratsHr.value = await get(`/salaries/${salarieId}/contrats-info`)
  } catch (e) {
    console.error(e)
  }
}
const editContratHr = (item) => {
  editingContratHr.value = item
  formContratHr.value = {
    type_contrat: item.type_contrat,
    date_embauche: item.date_embauche ? item.date_embauche.substring(0, 10) : '',
    date_fin_contrat: item.date_fin_contrat ? item.date_fin_contrat.substring(0, 10) : '',
    fin_periode_essai: item.fin_periode_essai ? item.fin_periode_essai.substring(0, 10) : ''
  }
  showContratHrForm.value = true
}
const deleteContratHr = async (id) => {
  if (!confirm('Supprimer ce contrat RH ?')) return
  try {
    await apiDelete(`/salaries/contrats-info/${id}`)
    toast.add({ title: 'Succès', description: 'Contrat RH supprimé.', color: 'success' })
    contratsHr.value = await get(`/salaries/${salarieId}/contrats-info`)
  } catch (e) {
    console.error(e)
  }
}
const cancelContratHr = () => {
  showContratHrForm.value = false
  editingContratHr.value = null
  formContratHr.value = { type_contrat: 'CDI', date_embauche: '', date_fin_contrat: '', fin_periode_essai: '' }
}

// Services
const saveService = async () => {
  try {
    const payload = { ...formService.value }
    if (editingService.value) {
      await put(`/salaries/services/${editingService.value.id}`, payload)
      toast.add({ title: 'Succès', description: 'Infos service mises à jour.', color: 'success' })
    } else {
      await post(`/salaries/${salarieId}/services`, payload)
      toast.add({ title: 'Succès', description: 'Infos service enregistrées.', color: 'success' })
    }
    showServiceForm.value = false
    editingService.value = null
    formService.value = { departement: '', poste_occupe: '', manager: '', dotation_materiel: '' }
    services.value = await get(`/salaries/${salarieId}/services`)
  } catch (e) {
    console.error(e)
  }
}
const editService = (item) => {
  editingService.value = item
  formService.value = {
    departement: item.departement,
    poste_occupe: item.poste_occupe,
    manager: item.manager,
    dotation_materiel: item.dotation_materiel
  }
  showServiceForm.value = true
}
const deleteService = async (id) => {
  if (!confirm('Supprimer cette affectation de service ?')) return
  try {
    await apiDelete(`/salaries/services/${id}`)
    toast.add({ title: 'Succès', description: 'Affectation supprimée.', color: 'success' })
    services.value = await get(`/salaries/${salarieId}/services`)
  } catch (e) {
    console.error(e)
  }
}
const cancelService = () => {
  showServiceForm.value = false
  editingService.value = null
  formService.value = { departement: '', poste_occupe: '', manager: '', dotation_materiel: '' }
}

// Archivage
const saveArchivage = async () => {
  try {
    let fileUrl = formArchivage.value.fichier_joint
    if (selectedFile.value) {
      // Upload file first
      const formData = new FormData()
      formData.append('file', selectedFile.value)
      const uploadRes = await post(`/salaries/${salarieId}/upload-document`, formData)
      fileUrl = uploadRes.url
    }
    
    const payload = {
      type_document: formArchivage.value.type_document,
      date_ajout: formArchivage.value.date_ajout,
      fichier_joint: fileUrl
    }
    
    if (editingArchivage.value) {
      await put(`/salaries/archivages/${editingArchivage.value.id}`, payload)
      toast.add({ title: 'Succès', description: 'Document archivé mis à jour.', color: 'success' })
    } else {
      await post(`/salaries/${salarieId}/archivages`, payload)
      toast.add({ title: 'Succès', description: 'Document archivé avec succès.', color: 'success' })
    }
    showArchivageForm.value = false
    editingArchivage.value = null
    selectedFile.value = null
    formArchivage.value = { type_document: '', fichier_joint: '', date_ajout: '' }
    archivages.value = await get(`/salaries/${salarieId}/archivages`)
  } catch (e) {
    console.error(e)
  }
}
const editArchivage = (item) => {
  editingArchivage.value = item
  formArchivage.value = {
    type_document: item.type_document,
    fichier_joint: item.fichier_joint,
    date_ajout: item.date_ajout ? item.date_ajout.substring(0, 10) : ''
  }
  selectedFile.value = null
  showArchivageForm.value = true
}
const deleteArchivage = async (id) => {
  if (!confirm('Supprimer ce document archivé ?')) return
  try {
    await apiDelete(`/salaries/archivages/${id}`)
    toast.add({ title: 'Succès', description: 'Document supprimé.', color: 'success' })
    archivages.value = await get(`/salaries/${salarieId}/archivages`)
  } catch (e) {
    console.error(e)
  }
}
const cancelArchivage = () => {
  showArchivageForm.value = false
  editingArchivage.value = null
  selectedFile.value = null
  formArchivage.value = { type_document: '', fichier_joint: '', date_ajout: '' }
}

onMounted(() => {
  fetchSalarieDetails()
})
</script>

<template>
  <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement du salarié...</span>
  </div>

  <div v-else-if="sal" class="space-y-6">
    <!-- Header Object page -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-50 text-green-700 rounded-full flex items-center justify-center font-bold text-lg border border-green-200">
          {{ sal.prenom[0] }}{{ sal.nom[0] }}
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-900 leading-tight">
            {{ sal.civilite }} {{ sal.prenom }} {{ sal.nom.toUpperCase() }}
          </h1>
          <p class="text-xs text-slate-500 font-mono mt-1">Matricule : {{ sal.matricule }}</p>
        </div>
      </div>
      
      <div class="flex space-x-3">
        <button 
          @click="handleDeleteSalarie"
          class="px-4 py-2 border border-red-200 text-sm font-semibold rounded-lg hover:bg-red-50 text-red-600 transition-colors flex items-center gap-1.5"
        >
          <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
          Supprimer la Fiche
        </button>
      </div>
    </div>

    <!-- SAP Fiori Tabs -->
    <div class="border-b border-slate-200">
      <nav class="flex space-x-6 overflow-x-auto whitespace-nowrap pb-1 scrollbar-thin" aria-label="Tabs">
        <button 
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            activeTab === tab.id 
              ? 'border-green-600 text-green-700 font-bold' 
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all'
          ]"
        >
          {{ tab.label }}
        </button>
      </nav>
    </div>

    <!-- Tab 1: Fiche Salarié -->
    <div v-show="activeTab === 'infos'" class="space-y-6">
      <form @submit.prevent="handleUpdateSalarie" class="space-y-6">
        
        <!-- Civil Profile -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">État Civil & Informations Générales</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Civilité</label>
              <select v-model="salCivilite" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="M.">Monsieur (M.)</option>
                <option value="MME">Madame (Mme)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Matricule Interne</label>
              <input v-model="salMatricule" type="text" disabled class="mt-1 block w-full px-3 py-2 border border-slate-200 bg-slate-50 rounded-lg text-sm font-mono text-slate-500 cursor-not-allowed" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Prénom</label>
              <input 
                v-model="salPrenom" 
                type="text" 
                required 
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm transition-colors',
                  fieldErrors.prenom ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.prenom" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.prenom }}</p>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom de famille</label>
              <input 
                v-model="salNom" 
                type="text" 
                required 
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm transition-colors',
                  fieldErrors.nom ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.nom" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.nom }}</p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom d'Usage (Optionnel)</label>
              <input v-model="salNomUsage" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">N° Sécurité Sociale (NIR)</label>
              <input 
                v-model="salNir" 
                type="text" 
                placeholder="15 chiffres" 
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono transition-colors',
                  fieldErrors.numero_securite_sociale ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.numero_securite_sociale" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.numero_securite_sociale }}</p>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nationalité</label>
              <input v-model="salNationalite" type="text" placeholder="Ex: Ivoirienne" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Régime Expatrié</label>
              <select v-model="salExpatrie" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option :value="false">Non (Local)</option>
                <option :value="true">Oui (Expatrié)</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Date de Naissance</label>
              <input v-model="salDateNaissance" type="date" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Lieu de Naissance</label>
              <input v-model="salLieuNaissance" type="text" placeholder="Ex: Abidjan" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Pays Naissance</label>
              <input v-model="salPaysNaissance" type="text" placeholder="Ex: Côte d'Ivoire" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Situation Matrimoniale</label>
              <select v-model="salSituationMatrimoniale" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="Célibataire">Célibataire</option>
                <option value="Marié">Marié(e)</option>
                <option value="Divorcé">Divorcé(e)</option>
                <option value="Veuf">Veuf(ve)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Enfants à charge</label>
              <input 
                v-model.number="salEnfantsCharge" 
                type="number" 
                min="0"
                max="20"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
              />
            </div>
          </div>
        </div>

        <!-- Coordonnees -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Coordonnées de Contact & Adresse</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Email Personnel</label>
              <input 
                v-model="salEmail" 
                type="email" 
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm transition-colors',
                  fieldErrors.email ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.email" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.email }}</p>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Téléphone</label>
              <input 
                v-model="salPhone" 
                type="text" 
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm transition-colors',
                  fieldErrors.telephone ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.telephone" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.telephone }}</p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="md:col-span-2">
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Adresse postale</label>
              <input v-model="salAdresse" type="text" placeholder="Voie et rue" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Adresse Complémentaire</label>
              <input v-model="salAdresse2" type="text" placeholder="Escalier, appartement..." class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Postal</label>
              <input v-model="salCodePostal" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Ville</label>
              <input v-model="salVille" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Pays</label>
              <input v-model="salPays" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
        </div>

        <!-- Banque -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Informations Bancaires de Versement</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">IBAN du salarié</label>
              <input 
                v-model="salIban" 
                type="text" 
                placeholder="FR76..." 
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono transition-colors',
                  fieldErrors.iban ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.iban" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.iban }}</p>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">BIC du salarié</label>
              <input 
                v-model="salBic" 
                type="text" 
                placeholder="Ex: CEIDFRPP..." 
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono transition-colors',
                  fieldErrors.bic ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.bic" class="mt-1 text-xs text-red-655 font-medium">{{ fieldErrors.bic }}</p>
            </div>
          </div>
        </div>

        <div class="flex justify-end space-x-3">
          <div class="flex items-center space-x-2 mr-4">
            <input id="sal-active" v-model="salIsActive" type="checkbox" class="rounded border-slate-300 text-green-600 focus:ring-green-500 h-4 w-4" />
            <label for="sal-active" class="text-sm font-semibold text-slate-700">Fiche active</label>
          </div>
          <button type="submit" class="px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow transition-colors">
            Enregistrer les modifications
          </button>
        </div>
      </form>
    </div>

    <!-- Tab 2: Contrats -->
    <div v-show="activeTab === 'contrats'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">Historique des Contrats</h3>
            <p class="text-xs text-slate-500">Liste des contrats de travail (actifs et échus) de cet employé.</p>
          </div>
          <button 
            @click="router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/new`)"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouveau Contrat
          </button>
        </div>

        <!-- Contracts Table -->
        <div v-if="contrats.length === 0" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun contrat créé pour ce salarié.
        </div>
        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">N° Contrat</th>
                <th scope="col" class="px-6 py-3 text-left">Poste / Emploi</th>
                <th scope="col" class="px-6 py-3 text-left">Type Contrat</th>
                <th scope="col" class="px-6 py-3 text-left">Rémunération</th>
                <th scope="col" class="px-6 py-3 text-left">Date Début</th>
                <th scope="col" class="px-6 py-3 text-left">Statut</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr 
                v-for="c in contrats" 
                :key="c.id" 
                @click="router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/${c.id}`)"
                class="hover:bg-slate-50 cursor-pointer group"
              >
                <td class="px-6 py-4 font-mono font-semibold text-slate-900">{{ c.numero_contrat }}</td>
                <td class="px-6 py-4 font-medium text-slate-700 group-hover:text-green-700 transition-colors">
                  {{ c.emploi || 'Non renseigné' }}
                </td>
                <td class="px-6 py-4 text-slate-600 font-semibold">
                  {{ c.type_contrat_travail === 10 ? 'CDI' : c.type_contrat_travail === 29 ? 'CDD' : 'Autre (code ' + c.type_contrat_travail + ')' }}
                </td>
                <td class="px-6 py-4 font-mono text-slate-600">
                  {{ c.salaire_mensuel }} FCFA / {{ c.type_salaire }}
                  <span
                    :class="[
                      c.mode_calcul === 'net' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-amber-50 text-amber-700 border-amber-200',
                      'ml-1 px-1.5 py-0.5 rounded text-[9px] uppercase font-bold border'
                    ]"
                  >{{ c.mode_calcul === 'net' ? 'Net' : 'Brut' }}</span>
                </td>
                <td class="px-6 py-4 font-mono text-slate-500">{{ c.date_debut_contrat || '-' }}</td>
                <td class="px-6 py-4">
                  <span 
                    :class="[
                      c.statut === 'actif' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-slate-150 text-slate-500 border-slate-200',
                      'px-2 py-0.5 rounded text-[10px] uppercase font-bold border'
                    ]"
                  >
                    {{ c.statut }}
                  </span>
                </td>
                <td class="px-6 py-4 text-right">
                  <span class="text-green-600 group-hover:underline text-xs font-semibold flex items-center justify-end gap-1">
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


    <!-- Tab 3: Entretiens -->
    <div v-show="activeTab === 'entretiens'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">Entretiens Annuels d'Évaluation</h3>
            <p class="text-xs text-slate-500">Historique des entretiens d'évaluation du salarié.</p>
          </div>
          <button 
            v-if="!showEntretienForm"
            @click="showEntretienForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouvel Entretien
          </button>
        </div>

        <!-- Form -->
        <form v-if="showEntretienForm" @submit.prevent="saveEntretien" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-slate-700">{{ editingEntretien ? 'Modifier l\'entretien' : 'Saisir un nouvel entretien' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de l'entretien</label>
              <input type="date" v-model="formEntretien.date_entretien" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Nom de l'évaluateur</label>
              <input type="text" v-model="formEntretien.nom_evaluateur" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Note globale (sur 20)</label>
              <input type="number" step="0.1" min="0" max="20" v-model.number="formEntretien.note_globale" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase">Commentaires et objectifs</label>
            <textarea v-model="formEntretien.commentaires" rows="3" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"></textarea>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelEntretien" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="entretiens.length === 0 && !showEntretienForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun entretien enregistré.
        </div>
        <div v-else-if="!showEntretienForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Date</th>
                <th scope="col" class="px-6 py-3 text-left">Évaluateur</th>
                <th scope="col" class="px-6 py-3 text-left">Note Globale</th>
                <th scope="col" class="px-6 py-3 text-left">Commentaires</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in entretiens" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-mono">{{ item.date_entretien }}</td>
                <td class="px-6 py-4 font-medium text-slate-800">{{ item.nom_evaluateur }}</td>
                <td class="px-6 py-4 font-mono font-semibold">{{ item.note_globale !== null ? item.note_globale + '/20' : '-' }}</td>
                <td class="px-6 py-4 text-slate-650 max-w-xs truncate">{{ item.commentaires || '-' }}</td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editEntretien(item)" class="text-green-600 hover:text-green-800 text-xs font-semibold">Modifier</button>
                  <button @click="deleteEntretien(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


    <!-- Tab 4: Santé (Visite Médicale) -->
    <div v-show="activeTab === 'sante'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">Visites Médicales</h3>
            <p class="text-xs text-slate-500">Suivi médical et avis d'aptitude du salarié.</p>
          </div>
          <button 
            v-if="!showVisiteForm"
            @click="showVisiteForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouvelle Visite
          </button>
        </div>

        <!-- Form -->
        <form v-if="showVisiteForm" @submit.prevent="saveVisite" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-slate-700">{{ editingVisite ? 'Modifier la visite' : 'Saisir une nouvelle visite' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de la visite</label>
              <input type="date" v-model="formVisite.date_visite" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Type de visite</label>
              <select v-model="formVisite.type_visite" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="Embauche">Embauche</option>
                <option value="Reprise">Reprise</option>
                <option value="Périodique">Périodique</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Avis d'aptitude</label>
              <select v-model="formVisite.aptitude" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="Apte">Apte</option>
                <option value="Inapte">Inapte</option>
                <option value="Apte avec réserves">Apte avec réserves</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date prochaine visite</label>
              <input type="date" v-model="formVisite.prochaine_visite" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelVisite" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="visites.length === 0 && !showVisiteForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucune visite médicale enregistrée.
        </div>
        <div v-else-if="!showVisiteForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Date Visite</th>
                <th scope="col" class="px-6 py-3 text-left">Type de Visite</th>
                <th scope="col" class="px-6 py-3 text-left">Avis d'Aptitude</th>
                <th scope="col" class="px-6 py-3 text-left">Prochaine Visite</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in visites" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-mono">{{ item.date_visite }}</td>
                <td class="px-6 py-4 font-medium text-slate-800">{{ item.type_visite }}</td>
                <td class="px-6 py-4">
                  <span 
                    :class="[
                      item.aptitude === 'Apte' ? 'bg-green-50 text-green-700 border-green-200' : item.aptitude === 'Inapte' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-amber-50 text-amber-700 border-amber-200',
                      'px-2 py-0.5 rounded text-[10px] uppercase font-bold border'
                    ]"
                  >
                    {{ item.aptitude }}
                  </span>
                </td>
                <td class="px-6 py-4 font-mono text-slate-600">{{ item.prochaine_visite || '-' }}</td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editVisite(item)" class="text-green-600 hover:text-green-800 text-xs font-semibold">Modifier</button>
                  <button @click="deleteVisite(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


    <!-- Tab 5: Formations -->
    <div v-show="activeTab === 'formations'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">Suivi des Formations</h3>
            <p class="text-xs text-slate-500">Formations demandées, en cours ou terminées.</p>
          </div>
          <button 
            v-if="!showFormationForm"
            @click="showFormationForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouvelle Formation
          </button>
        </div>

        <!-- Form -->
        <form v-if="showFormationForm" @submit.prevent="saveFormation" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-slate-700">{{ editingFormation ? 'Modifier la formation' : 'Saisir une nouvelle formation' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Intitulé de la formation</label>
              <input type="text" v-model="formFormation.intitule_formation" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Organisme de formation</label>
              <input type="text" v-model="formFormation.organisme" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de début</label>
              <input type="date" v-model="formFormation.date_debut" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de fin</label>
              <input type="date" v-model="formFormation.date_fin" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Statut</label>
              <select v-model="formFormation.statut_formation" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="Demandée">Demandée</option>
                <option value="En cours">En cours</option>
                <option value="Terminée">Terminée</option>
              </select>
            </div>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelFormation" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="formations.length === 0 && !showFormationForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucune formation enregistrée.
        </div>
        <div v-else-if="!showFormationForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Intitulé</th>
                <th scope="col" class="px-6 py-3 text-left">Organisme</th>
                <th scope="col" class="px-6 py-3 text-left">Période</th>
                <th scope="col" class="px-6 py-3 text-left">Statut</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in formations" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-medium text-slate-800">{{ item.intitule_formation }}</td>
                <td class="px-6 py-4 text-slate-700">{{ item.organisme }}</td>
                <td class="px-6 py-4 font-mono text-xs text-slate-650">Du {{ item.date_debut }} au {{ item.date_fin }}</td>
                <td class="px-6 py-4">
                  <span 
                    :class="[
                      item.statut_formation === 'Terminée' ? 'bg-green-50 text-green-700 border-green-200' : item.statut_formation === 'En cours' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-slate-100 text-slate-650 border-slate-200',
                      'px-2 py-0.5 rounded text-[10px] uppercase font-bold border'
                    ]"
                  >
                    {{ item.statut_formation }}
                  </span>
                </td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editFormation(item)" class="text-green-600 hover:text-green-800 text-xs font-semibold">Modifier</button>
                  <button @click="deleteFormation(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


    <!-- Tab 6: Absences -->
    <div v-show="activeTab === 'absences'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">Saisie et Suivi des Absences</h3>
            <p class="text-xs text-slate-500">Congés, maladies et autres motifs d'absences.</p>
          </div>
          <button 
            v-if="!showAbsenceForm"
            @click="showAbsenceForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouvelle Absence
          </button>
        </div>

        <!-- Form -->
        <form v-if="showAbsenceForm" @submit.prevent="saveAbsence" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-slate-700">{{ editingAbsence ? 'Modifier l\'absence' : 'Saisir une nouvelle absence' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Motif de l'absence</label>
              <select v-model="formAbsence.type_absence" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="Congés payés">Congés payés</option>
                <option value="Maladie">Maladie</option>
                <option value="Maternité/Paternité">Maternité/Paternité</option>
                <option value="Sans solde">Sans solde</option>
              </select>
            </div>
            <div class="flex items-end pb-2">
              <div class="flex items-center space-x-2">
                <input type="checkbox" id="justif" v-model="formAbsence.justificatif_fourni" class="rounded border-slate-300 text-green-600 focus:ring-green-500 h-4 w-4" />
                <label for="justif" class="text-sm font-semibold text-slate-700">Justificatif fourni</label>
              </div>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de début</label>
              <input type="date" v-model="formAbsence.date_debut_absence" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de fin</label>
              <input type="date" v-model="formAbsence.date_fin_absence" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelAbsence" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="absences.length === 0 && !showAbsenceForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucune absence enregistrée.
        </div>
        <div v-else-if="!showAbsenceForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Motif</th>
                <th scope="col" class="px-6 py-3 text-left">Période</th>
                <th scope="col" class="px-6 py-3 text-left">Justificatif</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in absences" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-medium text-slate-800">{{ item.type_absence }}</td>
                <td class="px-6 py-4 font-mono text-xs text-slate-650">Du {{ item.date_debut_absence }} au {{ item.date_fin_absence }}</td>
                <td class="px-6 py-4">
                  <span 
                    :class="[
                      item.justificatif_fourni ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200',
                      'px-2 py-0.5 rounded text-[10px] uppercase font-bold border'
                    ]"
                  >
                    {{ item.justificatif_fourni ? 'Oui' : 'Non' }}
                  </span>
                </td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editAbsence(item)" class="text-green-600 hover:text-green-800 text-xs font-semibold">Modifier</button>
                  <button @click="deleteAbsence(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


    <!-- Tab 7: Prêts -->
    <div v-show="activeTab === 'prets'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">Prêts accordés au Salarié</h3>
            <p class="text-xs text-slate-500">Suivi des retenues mensuelles et soldes des prêts.</p>
          </div>
          <button 
            v-if="!showPretForm"
            @click="showPretForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouveau Prêt
          </button>
        </div>

        <!-- Form -->
        <form v-if="showPretForm" @submit.prevent="savePret" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-slate-700">{{ editingPret ? 'Modifier le prêt' : 'Saisir un nouveau prêt' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Montant total accordé (FCFA)</label>
              <input type="number" v-model.number="formPret.montant_pret" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de déblocage</label>
              <input type="date" v-model="formPret.date_deblocage" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Retenue mensuelle (FCFA)</label>
              <input type="number" v-model.number="formPret.montant_mensualite" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Reste à rembourser (FCFA)</label>
              <input type="number" v-model.number="formPret.reste_a_rembourser" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelPret" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="prets.length === 0 && !showPretForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun prêt enregistré.
        </div>
        <div v-else-if="!showPretForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Montant Prêt</th>
                <th scope="col" class="px-6 py-3 text-left">Date Déblocage</th>
                <th scope="col" class="px-6 py-3 text-left">Mensualité Retenue</th>
                <th scope="col" class="px-6 py-3 text-left">Reste à Rembourser</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in prets" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-mono font-semibold text-slate-800">{{ item.montant_pret.toLocaleString() }} FCFA</td>
                <td class="px-6 py-4 font-mono">{{ item.date_deblocage }}</td>
                <td class="px-6 py-4 font-mono text-slate-650">{{ item.montant_mensualite.toLocaleString() }} FCFA</td>
                <td class="px-6 py-4 font-mono text-red-650 font-bold">{{ item.reste_a_rembourser.toLocaleString() }} FCFA</td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editPret(item)" class="text-green-600 hover:text-green-800 text-xs font-semibold">Modifier</button>
                  <button @click="deletePret(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


    <!-- Tab 8: Contrats HR -->
    <div v-show="activeTab === 'contrats_hr'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">Suivi Administratif des Contrats</h3>
            <p class="text-xs text-slate-500">Dates clés, périodes d'essai et types de contrats RH.</p>
          </div>
          <button 
            v-if="!showContratHrForm"
            @click="showContratHrForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouveau Contrat HR
          </button>
        </div>

        <!-- Form -->
        <form v-if="showContratHrForm" @submit.prevent="saveContratHr" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-slate-700">{{ editingContratHr ? 'Modifier le contrat' : 'Saisir un nouveau contrat' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Type de contrat</label>
              <select v-model="formContratHr.type_contrat" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="CDI">CDI</option>
                <option value="CDD">CDD</option>
                <option value="Apprentissage">Apprentissage</option>
                <option value="Stage">Stage</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date d'embauche</label>
              <input type="date" v-model="formContratHr.date_embauche" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de fin</label>
              <input type="date" v-model="formContratHr.date_fin_contrat" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Fin période d'essai</label>
              <input type="date" v-model="formContratHr.fin_periode_essai" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelContratHr" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="contratsHr.length === 0 && !showContratHrForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun contrat HR enregistré.
        </div>
        <div v-else-if="!showContratHrForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Type Contrat</th>
                <th scope="col" class="px-6 py-3 text-left">Date Embauche</th>
                <th scope="col" class="px-6 py-3 text-left">Date Fin</th>
                <th scope="col" class="px-6 py-3 text-left">Fin Période Essai</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in contratsHr" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-semibold text-slate-800">{{ item.type_contrat }}</td>
                <td class="px-6 py-4 font-mono">{{ item.date_embauche }}</td>
                <td class="px-6 py-4 font-mono text-slate-650">{{ item.date_fin_contrat || 'Illimité (CDI)' }}</td>
                <td class="px-6 py-4 font-mono text-slate-600">{{ item.fin_periode_essai || '-' }}</td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editContratHr(item)" class="text-green-600 hover:text-green-800 text-xs font-semibold">Modifier</button>
                  <button @click="deleteContratHr(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


    <!-- Tab 9: Services -->
    <div v-show="activeTab === 'services'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">Département, Poste & Matériel</h3>
            <p class="text-xs text-slate-500">Service d'affectation, manager et équipements remis.</p>
          </div>
          <button 
            v-if="!showServiceForm"
            @click="showServiceForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouvelle Affectation
          </button>
        </div>

        <!-- Form -->
        <form v-if="showServiceForm" @submit.prevent="saveService" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-slate-700">{{ editingService ? 'Modifier l\'affectation' : 'Saisir une nouvelle affectation' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Département / Service</label>
              <select v-model="formService.departement" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="" disabled>-- Choisir un service --</option>
                <option v-for="d in dossierDepartements" :key="d.id" :value="d.nom">
                  {{ d.nom }} {{ d.code ? `(${d.code})` : '' }}
                </option>
              </select>
              <p v-if="dossierDepartements.length === 0" class="mt-1 text-xs text-amber-600 font-medium">
                <UIcon name="i-lucide-alert-triangle" class="w-3.5 h-3.5 inline mr-1 align-text-bottom" />
                Aucun département configuré pour ce dossier. Veuillez d'abord en ajouter dans la fiche du dossier client.
              </p>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Poste occupé</label>
              <input type="text" v-model="formService.poste_occupe" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Responsable hiérarchique</label>
              <input type="text" v-model="formService.manager" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase">Matériel confié (PC, Téléphone, Voiture...)</label>
            <textarea v-model="formService.dotation_materiel" rows="3" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" placeholder="Ex: PC Dell Latitude, iPhone 13, Clés bureau..."></textarea>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelService" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="services.length === 0 && !showServiceForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucune affectation de service enregistrée.
        </div>
        <div v-else-if="!showServiceForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Service</th>
                <th scope="col" class="px-6 py-3 text-left">Poste</th>
                <th scope="col" class="px-6 py-3 text-left">Responsable (Manager)</th>
                <th scope="col" class="px-6 py-3 text-left">Matériel Dotation</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in services" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-semibold text-slate-800">{{ item.departement }}</td>
                <td class="px-6 py-4 text-slate-700">{{ item.poste_occupe }}</td>
                <td class="px-6 py-4 font-medium text-slate-650">{{ item.manager }}</td>
                <td class="px-6 py-4 text-slate-500 max-w-xs truncate">{{ item.dotation_materiel || '-' }}</td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editService(item)" class="text-green-600 hover:text-green-800 text-xs font-semibold">Modifier</button>
                  <button @click="deleteService(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


    <!-- Tab 10: Archivage -->
    <div v-show="activeTab === 'archivage'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">Archivage de Documents</h3>
            <p class="text-xs text-slate-500">Stockage et dépôt de documents liés au salarié (CNI, RIB, etc.).</p>
          </div>
          <button 
            v-if="!showArchivageForm"
            @click="showArchivageForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouveau Document
          </button>
        </div>

        <!-- Form -->
        <form v-if="showArchivageForm" @submit.prevent="saveArchivage" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-slate-700">{{ editingArchivage ? 'Modifier le document' : 'Archiver un nouveau document' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Type de document</label>
              <input type="text" v-model="formArchivage.type_document" placeholder="Ex: RIB, CNI, Diplôme..." required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de dépôt</label>
              <input type="date" v-model="formArchivage.date_ajout" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Fichier joint</label>
              <input type="file" @change="onFileSelected" :required="!editingArchivage" class="mt-1 block w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100" />
              <div v-if="formArchivage.fichier_joint" class="text-xs text-slate-500 mt-1">
                Fichier actuel : <a :href="`${apiBase}${formArchivage.fichier_joint}`" target="_blank" class="text-green-600 hover:underline font-medium">{{ formArchivage.fichier_joint.split('/').pop() }}</a>
              </div>
            </div>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelArchivage" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="archivages.length === 0 && !showArchivageForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun document archivé.
        </div>
        <div v-else-if="!showArchivageForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Type de Document</th>
                <th scope="col" class="px-6 py-3 text-left">Date de Dépôt</th>
                <th scope="col" class="px-6 py-3 text-left">Fichier</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in archivages" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-semibold text-slate-800">{{ item.type_document }}</td>
                <td class="px-6 py-4 font-mono">{{ item.date_ajout }}</td>
                <td class="px-6 py-4">
                  <a 
                    v-if="item.fichier_joint"
                    :href="`${apiBase}${item.fichier_joint}`" 
                    target="_blank" 
                    class="inline-flex items-center gap-1 text-green-600 hover:text-green-800 font-semibold hover:underline"
                  >
                    <UIcon name="i-lucide-download" class="w-3.5 h-3.5" />
                    Télécharger
                  </a>
                  <span v-else class="text-slate-400 italic">Aucun fichier</span>
                </td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editArchivage(item)" class="text-green-600 hover:text-green-800 text-xs font-semibold">Modifier</button>
                  <button @click="deleteArchivage(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


  </div>
</template>
