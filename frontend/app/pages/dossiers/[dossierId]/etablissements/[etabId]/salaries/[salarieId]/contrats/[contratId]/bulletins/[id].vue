<script setup>
const route = useRoute()
const router = useRouter()
const { get, put, post, delete: apiDelete } = useApi()
const toast = useToast()

const dossierId = route.params.dossierId
const etabId = route.params.etabId
const salarieId = route.params.salarieId
const contratId = route.params.contratId
const bulletinId = route.params.id

// Context & Data states
const loading = ref(true)
const currentDossier = useState('current-dossier')
const etablissement = ref(null)
const salarie = ref(null)
const contrat = ref(null)
const bulletin = ref(null)

// Add Heure Supp state
const hsModalOpen = ref(false)
const hsCode = ref('HS_15')
const hsNombre = ref(0)

// Add Absence state
const absModalOpen = ref(false)
const absCode = ref('CONGES')
const absDateDebut = ref('')
const absDateFin = ref('')
const absNbrHeure = ref(0)
const absNbrJour = ref(0)

// Add Prime state
const primeModalOpen = ref(false)
const primeCode = ref('PRIME_RENDEMENT')
const primeLibelle = ref('')
const primeMontant = ref(0)
const primeMode = ref('direct')
const primeBase = ref(0)
const primeTaux = ref(0)

// Acompte state
const acompteModalOpen = ref(false)
const acompteMontant = ref(0)

// Add Option state
const optionModalOpen = ref(false)
const optionCode = ref('AVANTAGE_LOGEMENT')
const optionLibelle = ref('')
const optionMontant = ref(0)

// Period variables list
const activeAbsences = ref([])
const activeHs = ref([])
const activePrimes = ref([])
const activeOptions = ref([])

const fetchVariables = async () => {
  if (!bulletin.value) return
  try {
    const absList = await get(`/contrats/${contratId}/absences`)
    activeAbsences.value = (absList || []).filter(a => a.mois === Number(bulletin.value.mois) && String(a.annee) === String(bulletin.value.annee))
    
    const hsList = await get(`/contrats/${contratId}/heures-supplementaires`)
    activeHs.value = (hsList || []).filter(h => h.mois === Number(bulletin.value.mois) && String(h.annee) === String(bulletin.value.annee))
    
    const primesList = await get(`/contrats/${contratId}/primes`)
    activePrimes.value = (primesList || []).filter(p => p.mois === Number(bulletin.value.mois) && String(p.annee) === String(bulletin.value.annee))

    const optionsList = await get(`/contrats/${contratId}/options`)
    activeOptions.value = (optionsList || []).filter(o => o.mois === Number(bulletin.value.mois) && String(o.annee) === String(bulletin.value.annee))
  } catch (e) {
    console.error("Error fetching variables:", e)
  }
}

const fetchDetails = async () => {
  loading.value = true
  try {
    // 1. Fetch Dossier Context
    if (!currentDossier.value) {
      currentDossier.value = await get(`/dossiers/${dossierId}`)
    }
    
    // 2. Fetch Etablissement
    etablissement.value = await get(`/etablissements/${etabId}`)
    
    // 3. Fetch Salarie
    salarie.value = await get(`/salaries/${salarieId}`)
    
    // 4. Fetch Contrat
    contrat.value = await get(`/contrats/${contratId}`)
    
    // 5. Fetch Bulletin details (includes lines and cumuls)
    bulletin.value = await get(`/bulletins/${bulletinId}`)

    // Find Acompte from lines
    const acompteLine = (bulletin.value.lignes || []).find(l => l.code === 'ACOMPTE')
    if (acompteLine) {
      acompteMontant.value = acompteLine.montant_cs || 0
    } else {
      acompteMontant.value = 0
    }

    // 6. Fetch period variables
    await fetchVariables()
  } catch (e) {
    console.error("Error loading payslip details:", e)
    router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/${contratId}`)
  } finally {
    loading.value = false
  }
}

const handleRecalculate = async () => {
  try {
    const payload = {
      contrat_id: Number(contratId),
      mois: Number(bulletin.value.mois),
      annee: Number(bulletin.value.annee),
      acompte: Number(acompteMontant.value),
      commentaire: "Recalculé suite à modification des variables"
    }
    const res = await post('/bulletins/calculer', payload)
    if (res) {
      toast.add({
        title: 'Bulletin Recalculé',
        description: 'Les modifications ont été prises en compte.',
        color: 'success'
      })
      await fetchDetails()
    }
  } catch (e) {
    console.error(e)
  }
}

const handleAddHeureSupp = async () => {
  if (hsNombre.value <= 0) {
    toast.add({ title: 'Validation', description: 'Le nombre d\'heures doit être supérieur à 0.', color: 'warning' })
    return
  }
  try {
    const payload = {
      code: hsCode.value,
      nombre: Number(hsNombre.value),
      mois: Number(bulletin.value.mois),
      annee: String(bulletin.value.annee)
    }
    await post(`/contrats/${contratId}/heures-supplementaires`, payload)
    hsModalOpen.value = false
    hsNombre.value = 0
    await handleRecalculate()
  } catch (e) {
    console.error(e)
  }
}

const handleAddAbsence = async () => {
  if (!absDateDebut.value || !absDateFin.value) {
    toast.add({ title: 'Validation', description: 'Les dates de début et de fin sont obligatoires.', color: 'warning' })
    return
  }
  try {
    const payload = {
      code: absCode.value,
      date_debut: new Date(absDateDebut.value).toISOString(),
      date_fin: new Date(absDateFin.value).toISOString(),
      nbr_heure_by_user: Number(absNbrHeure.value),
      nbr_jour_by_user: Number(absNbrJour.value),
      mois: Number(bulletin.value.mois),
      annee: String(bulletin.value.annee)
    }
    await post(`/contrats/${contratId}/absences`, payload)
    absModalOpen.value = false
    absDateDebut.value = ''
    absDateFin.value = ''
    absNbrHeure.value = 0
    absNbrJour.value = 0
    await handleRecalculate()
  } catch (e) {
    console.error(e)
  }
}

const handleAddPrime = async () => {
  if (primeMontant.value <= 0) {
    toast.add({ title: 'Validation', description: 'Le montant de la prime doit être supérieur à 0.', color: 'warning' })
    return
  }
  try {
    const payload = {
      code: primeCode.value,
      libelle: primeLibelle.value || primeCode.value,
      montant: Number(primeMontant.value),
      base: primeMode.value === 'calcul' ? (Number(primeBase.value) || null) : null,
      taux: primeMode.value === 'calcul' ? (Number(primeTaux.value) || null) : null,
      mois: Number(bulletin.value.mois),
      annee: String(bulletin.value.annee)
    }
    await post(`/contrats/${contratId}/primes`, payload)
    primeModalOpen.value = false
    primeLibelle.value = ''
    primeMontant.value = 0
    primeBase.value = 0
    primeTaux.value = 0
    await handleRecalculate()
  } catch (e) {
    console.error(e)
  }
}

const handleSaveAcompte = async () => {
  acompteModalOpen.value = false
  await handleRecalculate()
}

const handleAddOption = async () => {
  if (optionMontant.value <= 0) {
    toast.add({ title: 'Validation', description: 'Le montant de l\'option doit être supérieur à 0.', color: 'warning' })
    return
  }
  try {
    const payload = {
      code: optionCode.value,
      libelle: optionLibelle.value || optionCode.value.replace(/_/g, ' '),
      valeur_numerique: Number(optionMontant.value),
      mois: Number(bulletin.value.mois),
      annee: String(bulletin.value.annee)
    }
    await post(`/contrats/${contratId}/options`, payload)
    optionModalOpen.value = false
    optionLibelle.value = ''
    optionMontant.value = 0
    await handleRecalculate()
  } catch (e) {
    console.error(e)
  }
}

const handleDeleteAbsence = async (absId) => {
  if (!confirm('Supprimer cette absence ?')) return
  try {
    await apiDelete(`/contrats/absences/${absId}`)
    await handleRecalculate()
  } catch (e) {
    console.error(e)
  }
}

const handleDeleteHs = async (hsId) => {
  if (!confirm('Supprimer ces heures supplémentaires ?')) return
  try {
    await apiDelete(`/contrats/heures-supplementaires/${hsId}`)
    await handleRecalculate()
  } catch (e) {
    console.error(e)
  }
}

const handleDeletePrime = async (primeId) => {
  if (!confirm('Supprimer cette prime ?')) return
  try {
    await apiDelete(`/contrats/primes/${primeId}`)
    await handleRecalculate()
  } catch (e) {
    console.error(e)
  }
}

const handleDeleteOption = async (optionId) => {
  if (!confirm('Supprimer cette option ?')) return
  try {
    await apiDelete(`/contrats/options/${optionId}`)
    await handleRecalculate()
  } catch (e) {
    console.error(e)
  }
}

const handleValidate = async () => {
  if (!confirm('Êtes-vous sûr de vouloir valider définitivement ce bulletin ? Il ne pourra plus être modifié ni supprimé.')) return
  try {
    const res = await put(`/bulletins/${bulletinId}/valider`)
    if (res) {
      toast.add({
        title: 'Bulletin Validé',
        description: 'Le bulletin a été validé définitivement.',
        color: 'success'
      })
      await fetchDetails()
    }
  } catch (e) {
    console.error(e)
  }
}

const handleDelete = async () => {
  if (!confirm('Supprimer définitivement ce bulletin ?')) return
  try {
    await apiDelete(`/bulletins/${bulletinId}`)
    toast.add({
      title: 'Bulletin Supprimé',
      description: 'Le bulletin de salaire a été supprimé.',
      color: 'success'
    })
    router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/${contratId}`)
  } catch (e) {
    console.error(e)
  }
}

const triggerPrint = () => {
  window.print()
}

// Formatting helpers
const formatXOF = (value) => {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'XOF',
    maximumFractionDigits: 0
  }).format(value).replace('XOF', 'FCFA')
}

const formatPercent = (value) => {
  if (!value) return '-'
  return `${value.toFixed(2)} %`
}

const getPeriodLabel = (mois, annee) => {
  const months = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
  ]
  return `${months[mois - 1]} ${annee}`
}

const grossLines = computed(() => {
  if (!bulletin.value || !bulletin.value.lignes) return []
  return bulletin.value.lignes.filter(l => {
    const c = l.code.toUpperCase()
    return !['IBS', 'RICF', 'CNPS_RETRAITE', 'CMU_S', 'CN', 'TA', 'TFC', 'CNPS_PF', 'CNPS_AT', 'CNPS_MATERNITE', 'CMU_P', 'TRANSPORT', 'TELEPHONE', 'ACOMPTE'].includes(c)
  })
})

const cotisationsLines = computed(() => {
  if (!bulletin.value || !bulletin.value.lignes) return []
  return bulletin.value.lignes.filter(l => {
    const c = l.code.toUpperCase()
    return ['IBS', 'RICF', 'CNPS_RETRAITE', 'CMU_S', 'CN', 'TA', 'TFC', 'CNPS_PF', 'CNPS_AT', 'CNPS_MATERNITE', 'CMU_P'].includes(c)
  })
})

const netLines = computed(() => {
  if (!bulletin.value || !bulletin.value.lignes) return []
  return bulletin.value.lignes.filter(l => {
    const c = l.code.toUpperCase()
    return ['TRANSPORT', 'TELEPHONE', 'ACOMPTE'].includes(c)
  })
})

onMounted(() => {
  fetchDetails()
})
</script>

<template>
  <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4 no-print">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement du bulletin de paie...</span>
  </div>

  <div v-else-if="bulletin" class="space-y-6">
    
    <!-- Action Bar (Hidden on Print) -->
    <div class="bg-white border-2 border-slate-200 rounded-none p-4 shadow-flat flex flex-col sm:flex-row justify-between items-center gap-4 no-print border-t-4 border-t-green-600">
      <div class="flex items-center space-x-3">
        <NuxtLink 
          :to="`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/${contratId}`"
          class="p-2 border-2 border-slate-200 rounded-none hover:bg-slate-50 text-slate-700 transition-colors"
        >
          <UIcon name="i-lucide-arrow-left" class="w-4 h-4" />
        </NuxtLink>
        <div>
          <h1 class="text-lg font-bold text-slate-900 leading-tight uppercase">
            Bulletin {{ getPeriodLabel(bulletin.mois, bulletin.annee) }}
          </h1>
          <p class="text-xs text-slate-500 uppercase">
            Salarié : {{ salarie?.prenom }} {{ salarie?.nom?.toUpperCase() }} | Statut : 
            <span class="font-bold" :class="bulletin.statut === 'valide' ? 'text-green-600' : 'text-yellow-600'">
              {{ bulletin.statut }}
            </span>
          </p>
        </div>
      </div>

      <div class="flex space-x-3 w-full sm:w-auto justify-end">
        <button 
          v-if="bulletin.statut !== 'valide'"
          @click="handleDelete"
          class="px-4 py-2 border-2 border-red-200 text-sm font-bold rounded-none hover:bg-red-50 text-red-650 transition-colors flex items-center gap-1.5 uppercase tracking-wider cursor-pointer shadow-flat-hover shadow-flat-active"
        >
          <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
          Supprimer
        </button>
        <button 
          v-if="bulletin.statut !== 'valide'"
          @click="handleValidate"
          class="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white text-sm font-bold rounded-none shadow-flat transition-colors flex items-center gap-1.5 uppercase tracking-wider cursor-pointer shadow-flat-hover shadow-flat-active"
        >
          <UIcon name="i-lucide-check-circle" class="w-4 h-4" />
          Valider
        </button>
        <button 
          @click="triggerPrint"
          class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-bold rounded-none shadow-flat transition-colors flex items-center gap-1.5 uppercase tracking-wider cursor-pointer shadow-flat-hover shadow-flat-active"
        >
          <UIcon name="i-lucide-printer" class="w-4 h-4" />
          Imprimer
        </button>
      </div>
    </div>

    <!-- Variable Entry Toolbar (Hidden on Print) -->
    <div v-if="bulletin.statut !== 'valide'" class="bg-white border-2 border-slate-200 p-4 shadow-flat flex flex-wrap gap-3 no-print border-t-4 border-t-slate-500">
      <span class="text-xs font-bold uppercase tracking-wider text-slate-500 w-full mb-1">Modifier le Bulletin (Saisie de Variables) :</span>
      
      <button 
        @click="hsModalOpen = true"
        class="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-850 text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-1.5 border border-slate-350 rounded-none shadow-flat-hover shadow-flat-active cursor-pointer"
      >
        <UIcon name="i-lucide-plus-circle" class="w-4 h-4 text-green-600" />
        Saisir Heure Supp
      </button>

      <button 
        @click="absModalOpen = true"
        class="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-850 text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-1.5 border border-slate-350 rounded-none shadow-flat-hover shadow-flat-active cursor-pointer"
      >
        <UIcon name="i-lucide-minus-circle" class="w-4 h-4 text-red-650" />
        Saisir Absence
      </button>

      <button 
        @click="primeModalOpen = true"
        class="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-850 text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-1.5 border border-slate-350 rounded-none shadow-flat-hover shadow-flat-active cursor-pointer"
      >
        <UIcon name="i-lucide-award" class="w-4 h-4 text-blue-600" />
        Saisir Prime
      </button>

      <button 
        @click="acompteModalOpen = true"
        class="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-850 text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-1.5 border border-slate-350 rounded-none shadow-flat-hover shadow-flat-active cursor-pointer"
      >
        <UIcon name="i-lucide-banknote" class="w-4 h-4 text-amber-600" />
        Définir Acompte
      </button>

      <button 
        @click="optionModalOpen = true"
        class="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-850 text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-1.5 border border-slate-350 rounded-none shadow-flat-hover shadow-flat-active cursor-pointer"
      >
        <UIcon name="i-lucide-plus-circle" class="w-4 h-4 text-purple-600" />
        Saisir Option / Avantage
      </button>
    </div>

    <!-- Official Printable Payslip Container -->
    <div class="bg-white border-2 border-slate-200 shadow-flat rounded-none p-4  mx-auto print-payslip text-slate-800 border-t-4 border-t-green-600">
      
      <!-- Top Columns: Employer vs Employee -->
      <div class="grid grid-cols-2 gap-8 border-b-2 border-slate-200 pb-6 text-xs">
        
        <!-- Left Side: Employer Info -->
        <div class="space-y-2">
          <div class="space-y-1">
            <h2 class="text-sm font-black text-slate-900 uppercase">{{ etablissement?.raison_sociale }}</h2>
            <p class="text-slate-650 leading-relaxed font-medium">
              {{ etablissement?.adresse?.adresse_postale }}<br />
              {{ etablissement?.adresse?.adresse_postale2 || '' }}<br />
              {{ etablissement?.adresse?.code_postal }} {{ etablissement?.adresse?.ville }}<br />
              {{ etablissement?.adresse?.pays }}
            </p>
          </div>
          
          <div class="grid grid-cols-2 gap-2 border-t border-slate-200 pt-2 font-mono text-[10px] text-slate-500">
            <div>
              <span class="block text-[8px] font-bold uppercase tracking-wider text-slate-450">N° SIRET</span>
              <span class="font-bold text-slate-700">{{ etablissement?.siret || '-' }}</span>
            </div>
            <div>
              <span class="block text-[8px] font-bold uppercase tracking-wider text-slate-450">Code APE / NAF</span>
              <span class="font-bold text-slate-700">{{ etablissement?.ape || '-' }}</span>
            </div>
            <div class="col-span-2">
              <span class="block text-[8px] font-bold uppercase tracking-wider text-slate-450">N° Cotisant</span>
              <span class="font-bold text-slate-700">{{ etablissement?.numero_cotisant || '-' }}</span>
            </div>
          </div>
        </div>

        <!-- Right Side: Employee Info -->
        <div class="space-y-3">
          <div class="bg-slate-50 border-2 border-slate-200 rounded-none p-4 space-y-2 shadow-flat">
            <div class="flex justify-between border-b border-slate-200 pb-1">
              <span class="font-bold text-slate-900 uppercase">{{ salarie?.civilite }} {{ salarie?.prenom }} {{ salarie?.nom?.toUpperCase() }}</span>
              <span class="font-mono text-slate-500 text-[10px] font-bold">Matricule : {{ salarie?.matricule }}</span>
            </div>
            
            <div class="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[10px] leading-tight">
              <div>
                <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">Emploi / Poste</span>
                <span class="font-bold text-slate-800 uppercase">{{ contrat?.emploi || 'Non spécifié' }}</span>
              </div>
              <div>
                <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">Date d'embauche</span>
                <span class="font-mono text-slate-800 font-semibold">{{ contrat?.date_debut_contrat || '-' }}</span>
              </div>
              <div class="col-span-2 border-t border-slate-200 pt-1">
                <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">Adresse du Salarié</span>
                <span class="text-slate-700 font-medium">
                  {{ salarie?.adresse || '-' }} {{ salarie?.adresse2 || '' }}<br />
                  {{ salarie?.code_postal }} {{ salarie?.ville }}
                </span>
              </div>
              <div class="border-t border-slate-200 pt-1">
                <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">N° Securité Sociale</span>
                <span class="font-mono text-slate-800 font-semibold">{{ salarie?.numero_securite_sociale || '-' }}</span>
              </div>
              <div class="border-t border-slate-200 pt-1">
                <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">Régime</span>
                <span class="font-bold text-xs uppercase" :class="salarie?.expatrie ? 'text-amber-700' : 'text-slate-700'">
                  {{ salarie?.expatrie ? 'EXPATRIÉ (8.0% CN)' : 'LOCAL (1.5% CN)' }}
                </span>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Payslip Metadata / Period Bar -->
      <div class="my-4 py-3 px-4 bg-slate-50 border-2 border-slate-200 rounded-none flex justify-between items-center text-xs font-semibold shadow-flat">
        <div>
          <span>PÉRIODE : </span>
          <span class="font-bold text-slate-900 font-mono uppercase">{{ getPeriodLabel(bulletin.mois, bulletin.annee) }}</span>
        </div>
        <div>
          <span>DATE DE PAIEMENT : </span>
          <span class="font-mono text-slate-900">{{ bulletin.date_paiement ? new Date(bulletin.date_paiement).toLocaleDateString('fr-FR') : '-' }}</span>
        </div>
        <div>
          <span>MODE DE RÈGLEMENT : </span>
          <span class="text-slate-900 uppercase">VIREMENT BANCAIRE</span>
        </div>
      </div>

      <!-- Main Pay Lines Table -->
      <div class="overflow-x-auto border-2 border-slate-200 rounded-none shadow-flat">
        <table class="min-w-full divide-y divide-slate-250 text-xs">
          <thead class="bg-slate-100 text-slate-650 font-bold uppercase tracking-wider text-[9px] border-b-2 border-slate-200">
            <!-- Group Headers -->
            <tr>
              <th scope="col" rowspan="2" class="px-4 py-2.5 text-left w-1/4 border-r border-slate-200 align-middle">Rubrique / Libellé</th>
              <th scope="col" colspan="4" class="px-2 py-1 text-center bg-slate-50 border-r border-slate-200 border-b border-slate-200">Charges Employé</th>
              <th scope="col" colspan="3" class="px-2 py-1 text-center bg-slate-100 border-b border-slate-200">Charges Patronales</th>
            </tr>
            <!-- Sub Headers -->
            <tr class="bg-slate-50/50">
              <th scope="col" class="px-2 py-1.5 text-right border-r border-slate-200">Base</th>
              <th scope="col" class="px-2 py-1.5 text-right border-r border-slate-200">Taux</th>
              <th scope="col" class="px-2 py-1.5 text-right border-r border-slate-200">A déduire</th>
              <th scope="col" class="px-2 py-1.5 text-right border-r border-slate-200">A payer</th>
              <th scope="col" class="px-2 py-1.5 text-right border-r border-slate-200">Base</th>
              <th scope="col" class="px-2 py-1.5 text-right border-r border-slate-200">Taux</th>
              <th scope="col" class="px-2 py-1.5 text-right">Montant</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-150 font-mono text-slate-700 bg-white">
            <!-- Group 1: Gross Salary Elements -->
            <tr class="bg-slate-50/50 font-bold text-[10px] text-slate-650 uppercase tracking-wider no-print">
              <td colspan="8" class="px-4 py-1.5 text-left font-sans border-b border-slate-200">1. Éléments de Salaire Brut</td>
            </tr>
            <tr v-for="line in grossLines" :key="line.code" class="hover:bg-slate-50/50 transition-colors">
              <td class="px-4 py-2 text-left font-sans font-medium text-slate-900 border-r border-slate-100">{{ line.libelle }}</td>
              <!-- Emp Base -->
              <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-500">{{ line.base_s || '-' }}</td>
              <!-- Emp Taux -->
              <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-400">{{ line.taux_s > 0 ? formatPercent(line.taux_s) : '-' }}</td>
              <!-- Emp Deduct -->
              <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-400">-</td>
              <!-- Emp Pay -->
              <td class="px-2 py-2 text-right border-r border-slate-100 font-bold text-slate-900" :class="{ 'text-red-650': line.montant_pr < 0 }">
                {{ line.montant_pr !== 0 ? formatXOF(line.montant_pr) : '-' }}
              </td>
              <!-- Pat Base -->
              <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-550">{{ line.base_p || '-' }}</td>
              <!-- Pat Taux -->
              <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-400">{{ line.taux_p > 0 ? formatPercent(line.taux_p) : '-' }}</td>
              <!-- Pat Montant -->
              <td class="px-2 py-2 text-right" :class="line.montant_cp > 0 ? 'text-slate-900 font-bold' : 'text-slate-400'">
                {{ line.montant_cp > 0 ? formatXOF(line.montant_cp) : '-' }}
              </td>
            </tr>
            <!-- Subtotal Gross -->
            <tr class="bg-slate-100 font-extrabold border-t border-b border-slate-300">
              <td class="px-4 py-2 text-left font-sans text-slate-950 uppercase text-[10px] border-r border-slate-200">Total Salaire Brut</td>
              <td class="px-2 py-2 border-r border-slate-100"></td>
              <td class="px-2 py-2 border-r border-slate-100"></td>
              <td class="px-2 py-2 border-r border-slate-100"></td>
              <td class="px-2 py-2 text-right font-mono text-slate-950 border-r border-slate-200">{{ formatXOF(bulletin.salaire_brut) }}</td>
              <td class="px-2 py-2 border-r border-slate-100"></td>
              <td class="px-2 py-2 border-r border-slate-100"></td>
              <td class="px-2 py-2 text-right text-slate-450">-</td>
            </tr>

            <!-- Group 2: Cotisations & Retenues -->
            <tr class="bg-slate-50/50 font-bold text-[10px] text-slate-650 uppercase tracking-wider no-print">
              <td colspan="8" class="px-4 py-1.5 text-left font-sans border-b border-slate-200">2. Cotisations & Retenues Fiscales et Sociales</td>
            </tr>
            <tr v-for="line in cotisationsLines" :key="line.code" class="hover:bg-slate-50/50 transition-colors">
              <td class="px-4 py-2 text-left font-sans font-medium text-slate-900 border-r border-slate-100">{{ line.libelle }}</td>
              <!-- Emp Base -->
              <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-500">{{ line.base_s || '-' }}</td>
              <!-- Emp Taux -->
              <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-400">{{ line.taux_s > 0 ? formatPercent(line.taux_s) : '-' }}</td>
              <!-- Emp Deduct -->
              <td class="px-2 py-2 text-right border-r border-slate-100 font-bold text-slate-900">{{ line.montant_cs > 0 ? formatXOF(line.montant_cs) : '-' }}</td>
              <!-- Emp Pay -->
              <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-400">-</td>
              <!-- Pat Base -->
              <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-500">{{ line.base_p || '-' }}</td>
              <!-- Pat Taux -->
              <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-400">{{ line.taux_p > 0 ? formatPercent(line.taux_p) : '-' }}</td>
              <!-- Pat Montant -->
              <td class="px-2 py-2 text-right font-bold text-slate-900">{{ line.montant_cp > 0 ? formatXOF(line.montant_cp) : '-' }}</td>
            </tr>
            <!-- Subtotal Cotisations -->
            <tr class="bg-slate-100 font-extrabold border-t border-b border-slate-300">
              <td class="px-4 py-2 text-left font-sans text-slate-950 uppercase text-[10px] border-r border-slate-200">Total Cotisations & Retenues</td>
              <td class="px-2 py-2 border-r border-slate-100"></td>
              <td class="px-2 py-2 border-r border-slate-100"></td>
              <td class="px-2 py-2 text-right font-mono text-slate-950 border-r border-slate-200">{{ formatXOF(bulletin.cotisations_salariales) }}</td>
              <td class="px-2 py-2 border-r border-slate-100 text-slate-450">-</td>
              <td class="px-2 py-2 border-r border-slate-100"></td>
              <td class="px-2 py-2 border-r border-slate-100"></td>
              <td class="px-2 py-2 text-right font-mono text-slate-950">{{ formatXOF(bulletin.cotisations_patronales) }}</td>
            </tr>

            <!-- Group 3: Indemnités & Retenues diverses -->
            <tr class="bg-slate-50/50 font-bold text-[10px] text-slate-650 uppercase tracking-wider no-print">
              <td colspan="8" class="px-4 py-1.5 text-left font-sans border-b border-slate-200">3. Indemnités & Retenues diverses</td>
            </tr>
            <tr v-for="line in netLines" :key="line.code" class="hover:bg-slate-50/50 transition-colors">
              <td class="px-4 py-2 text-left font-sans font-medium text-slate-900 border-r border-slate-100">{{ line.libelle }}</td>
              <!-- Emp Base -->
              <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-500">{{ line.base_s || '-' }}</td>
              <!-- Emp Taux -->
              <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-400">-</td>
              <!-- Emp Deduct -->
              <td class="px-2 py-2 text-right border-r border-slate-100 font-bold text-slate-900" :class="{ 'text-red-650': line.montant_cs > 0 }">
                {{ line.montant_cs > 0 ? formatXOF(line.montant_cs) : '-' }}
              </td>
              <!-- Emp Pay -->
              <td class="px-2 py-2 text-right border-r border-slate-100 font-bold text-slate-900" :class="{ 'text-red-650': line.montant_pr < 0 }">
                {{ line.montant_pr > 0 ? formatXOF(line.montant_pr) : '-' }}
              </td>
              <!-- Pat Base -->
              <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-450">-</td>
              <!-- Pat Taux -->
              <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-450">-</td>
              <!-- Pat Montant -->
              <td class="px-2 py-2 text-right text-slate-400">-</td>
            </tr>

            <!-- Net à Payer Highlight Row -->
            <tr class="bg-green-600 font-extrabold text-white">
              <td class="px-4 py-3 text-left font-sans uppercase tracking-wider text-[11px] text-white border-r border-green-700">Net à payer</td>
              <td class="px-2 py-3 border-r border-green-500"></td>
              <td class="px-2 py-3 border-r border-green-500"></td>
              <td class="px-2 py-3 border-r border-green-500"></td>
              <td class="px-2 py-3 text-right font-mono text-white text-base border-r border-green-700">{{ formatXOF(bulletin.net_a_payer) }}</td>
              <td class="px-2 py-3 border-r border-green-500"></td>
              <td class="px-2 py-3 border-r border-green-500"></td>
              <td class="px-2 py-3 text-right text-white font-mono">-</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Quick Inline Action Toolbar (Hidden on Print) -->
      <div v-if="bulletin.statut !== 'valide'" class="mt-4 no-print flex flex-wrap gap-2 justify-center border-t border-slate-200 pt-4">
        <button @click="hsModalOpen = true" class="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-800 text-xs font-bold uppercase border-2 border-slate-250 rounded-none shadow-sm flex items-center gap-1 cursor-pointer">
          <UIcon name="i-lucide-plus" class="w-3.5 h-3.5 text-green-600" /> + Heure Supp
        </button>
        <button @click="absModalOpen = true" class="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-800 text-xs font-bold uppercase border-2 border-slate-250 rounded-none shadow-sm flex items-center gap-1 cursor-pointer">
          <UIcon name="i-lucide-minus" class="w-3.5 h-3.5 text-red-650" /> + Absence
        </button>
        <button @click="primeModalOpen = true" class="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-800 text-xs font-bold uppercase border-2 border-slate-250 rounded-none shadow-sm flex items-center gap-1 cursor-pointer">
          <UIcon name="i-lucide-award" class="w-3.5 h-3.5 text-blue-600" /> + Prime
        </button>
        <button @click="acompteModalOpen = true" class="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-800 text-xs font-bold uppercase border-2 border-slate-250 rounded-none shadow-sm flex items-center gap-1 cursor-pointer">
          <UIcon name="i-lucide-banknote" class="w-3.5 h-3.5 text-amber-600" /> + Acompte
        </button>
        <button @click="optionModalOpen = true" class="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-800 text-xs font-bold uppercase border-2 border-slate-250 rounded-none shadow-sm flex items-center gap-1 cursor-pointer">
          <UIcon name="i-lucide-plus" class="w-3.5 h-3.5 text-purple-600" /> + Option / Avantage
        </button>
      </div>

      <!-- Totals & Net Pay Card Layout -->
      <div class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        
        <!-- Totals Table -->
        <div class="bg-slate-50 border-2 border-slate-200 rounded-none p-4 space-y-2 text-xs shadow-flat">
          <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500 font-bold uppercase tracking-wider">Total Salaire Brut :</span>
            <span class="font-bold font-mono text-slate-900">{{ formatXOF(bulletin.salaire_brut) }}</span>
          </div>
          <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500 font-bold uppercase tracking-wider">Total Retenues Salariales :</span>
            <span class="font-bold font-mono text-slate-900">{{ formatXOF(bulletin.cotisations_salariales) }}</span>
          </div>
          <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500 font-bold uppercase tracking-wider">Total Charges Patronales :</span>
            <span class="font-bold font-mono text-slate-900">{{ formatXOF(bulletin.cotisations_patronales) }}</span>
          </div>
          <div class="flex justify-between border-b border-slate-200 pb-1.5">
            <span class="text-slate-500 font-bold uppercase tracking-wider">Net Imposable :</span>
            <span class="font-bold font-mono text-slate-900">{{ formatXOF(bulletin.net_imposable) }}</span>
          </div>
        </div>

        <!-- High-contrast Premium Net à Payer Callout -->
        <div class="bg-green-600 rounded-none p-5 text-white flex justify-between items-center shadow-flat">
          <div class="space-y-0.5">
            <p class="text-[9px] font-black uppercase tracking-widest text-green-200">NET À PAYER</p>
            <p class="text-3xl font-black tracking-tight font-mono">
              {{ formatXOF(bulletin.net_a_payer) }}
            </p>
          </div>
          <div class="text-right text-[10px] text-green-100 leading-snug max-w-[160px] font-sans font-bold">
            Versement par virement bancaire.<br />
            <span class="italic text-[9px] text-green-200">Conservez ce bulletin sans limite de durée.</span>
          </div>
        </div>

      </div>

      <!-- Bottom Tables: Monthly/Annual Cumulates & Vacation Tracker -->
      <div v-if="bulletin.cumuls" class="mt-8 border-t-2 border-slate-200 pt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <!-- Cumuls Table (cols-span 2) -->
        <div class="md:col-span-2 space-y-2">
          <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider">Cumuls Période et Annuel</h4>
          <div class="overflow-x-auto rounded-none border-2 border-slate-200 shadow-flat">
            <table class="min-w-full divide-y divide-slate-200 text-[10px] text-left">
              <thead class="bg-slate-100 font-bold text-slate-650 border-b border-slate-200">
                <tr>
                  <th scope="col" class="px-2 py-1.5">Période</th>
                  <th scope="col" class="px-2 py-1.5 text-right">Heures/Jours</th>
                  <th scope="col" class="px-2 py-1.5 text-right">Brut (FCFA)</th>
                  <th scope="col" class="px-2 py-1.5 text-right">Brut CNPS</th>
                  <th scope="col" class="px-2 py-1.5 text-right">Retraite</th>
                  <th scope="col" class="px-2 py-1.5 text-right">IBS</th>
                  <th scope="col" class="px-2 py-1.5 text-right">CMU</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-150 font-mono text-slate-700 bg-white">
                <tr class="hover:bg-slate-50/50">
                  <td class="px-2 py-1.5 font-sans font-bold text-slate-900">Mensuel</td>
                  <td class="px-2 py-1.5 text-right font-semibold">{{ bulletin.cumuls.mensuel.heures_jours }}</td>
                  <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(bulletin.cumuls.mensuel.salaire_brut) }}</td>
                  <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(bulletin.cumuls.mensuel.brut_cnps) }}</td>
                  <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(bulletin.cumuls.mensuel.cot_retraite) }}</td>
                  <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(bulletin.cumuls.mensuel.ibs) }}</td>
                  <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(bulletin.cumuls.mensuel.cmu) }}</td>
                </tr>
                <tr class="hover:bg-slate-50/50 bg-slate-50/30">
                  <td class="px-2 py-1.5 font-sans font-bold text-slate-900">Annuel</td>
                  <td class="px-2 py-1.5 text-right font-semibold">{{ bulletin.cumuls.annuel.heures_jours }}</td>
                  <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(bulletin.cumuls.annuel.salaire_brut) }}</td>
                  <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(bulletin.cumuls.annuel.brut_cnps) }}</td>
                  <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(bulletin.cumuls.annuel.cot_retraite) }}</td>
                  <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(bulletin.cumuls.annuel.ibs) }}</td>
                  <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(bulletin.cumuls.annuel.cmu) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Congés Payés Card -->
        <div class="space-y-2">
          <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider">Congés Payés</h4>
          <div class="bg-white border-2 border-slate-200 rounded-none p-3 space-y-1.5 shadow-flat text-[10px] text-slate-650">
            <div class="flex justify-between font-mono font-semibold">
              <span>Droits acquis :</span>
              <span class="font-bold text-slate-900">2.50 / mois</span>
            </div>
            <div class="flex justify-between font-mono font-semibold">
              <span>Pris ce mois :</span>
              <span class="font-bold text-slate-900">0.00</span>
            </div>
            <div class="flex justify-between font-mono border-t border-slate-200 pt-1.5 font-semibold">
              <span>Solde disponible :</span>
              <span class="font-bold text-green-700 text-sm">2.50 jours</span>
            </div>
          </div>
        </div>

      </div>

    </div>

    <!-- Period Variables Management Section (Hidden on Print) -->
    <div v-if="bulletin.statut !== 'valide' && (activeAbsences.length > 0 || activeHs.length > 0 || activePrimes.length > 0 || activeOptions.length > 0)" class="bg-white border-2 border-slate-200 p-6 shadow-flat no-print border-t-4 border-t-slate-500 space-y-4 rounded-none">
      <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider border-b border-slate-200 pb-2">Variables actives sur cette période de paie</h3>
      
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <!-- Absences list -->
        <div v-if="activeAbsences.length > 0" class="space-y-2">
          <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-100 pb-1">Absences</h4>
          <div class="space-y-1.5">
            <div v-for="a in activeAbsences" :key="a.id" class="p-2 border border-slate-200 flex justify-between items-center text-xs bg-slate-50/50">
              <div>
                <span class="font-bold text-slate-800 uppercase">{{ a.code }}</span>
                <span class="block text-[10px] text-slate-500 font-mono">
                  {{ a.nbr_jour_by_user }} j ({{ a.nbr_heure_by_user }} h)
                </span>
              </div>
              <button @click="handleDeleteAbsence(a.id)" class="text-red-650 hover:text-red-750 p-1 cursor-pointer">
                <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <!-- Overtime list -->
        <div v-if="activeHs.length > 0" class="space-y-2">
          <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-100 pb-1">Heures Supplémentaires</h4>
          <div class="space-y-1.5">
            <div v-for="h in activeHs" :key="h.id" class="p-2 border border-slate-200 flex justify-between items-center text-xs bg-slate-50/50">
              <div>
                <span class="font-bold text-slate-800 uppercase">{{ h.code.replace('HS_', 'HS ') }}%</span>
                <span class="block text-[10px] text-slate-500 font-mono">
                  {{ h.nombre }} heures
                </span>
              </div>
              <button @click="handleDeleteHs(h.id)" class="text-red-650 hover:text-red-750 p-1 cursor-pointer">
                <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <!-- Primes list -->
        <div v-if="activePrimes.length > 0" class="space-y-2">
          <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-100 pb-1">Primes</h4>
          <div class="space-y-1.5">
            <div v-for="p in activePrimes" :key="p.id" class="p-2 border border-slate-200 flex justify-between items-center text-xs bg-slate-50/50">
              <div>
                <span class="font-bold text-slate-800 uppercase">{{ p.libelle }}</span>
                <span class="block text-[10px] text-slate-500 font-mono">
                  {{ formatXOF(p.montant) }}
                </span>
              </div>
              <button @click="handleDeletePrime(p.id)" class="text-red-650 hover:text-red-750 p-1 cursor-pointer">
                <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <!-- Options list -->
        <div v-if="activeOptions.length > 0" class="space-y-2">
          <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-100 pb-1">Options & Avantages</h4>
          <div class="space-y-1.5">
            <div v-for="o in activeOptions" :key="o.id" class="p-2 border border-slate-200 flex justify-between items-center text-xs bg-slate-50/50">
              <div>
                <span class="font-bold text-slate-800 uppercase">{{ o.libelle }}</span>
                <span class="block text-[10px] text-slate-500 font-mono">
                  {{ formatXOF(o.valeur_numerique) }}
                </span>
              </div>
              <button @click="handleDeleteOption(o.id)" class="text-red-650 hover:text-red-750 p-1 cursor-pointer">
                <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals for adding variables -->
    
    <!-- Modal: Overtime -->
    <UModal v-model:open="hsModalOpen" title="Saisir des Heures Supplémentaires">
      <template #content>
        <div class="p-6 space-y-4 bg-white border border-slate-200">
          <h2 class="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Nouvelle Heure Supp.</h2>
          
          <div class="space-y-4">
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Taux de majoration</label>
              <select v-model="hsCode" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white select">
                <option value="HS_15">Majoration à 15%</option>
                <option value="HS_25">Majoration à 25%</option>
                <option value="HS_50">Majoration à 50%</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Nombre d'heures</label>
              <input v-model="hsNombre" type="number" step="0.5" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button type="button" @click="hsModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-none hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
              Annuler
            </button>
            <button type="button" @click="handleAddHeureSupp" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-none shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
              Enregistrer et Recalculer
            </button>
          </div>
        </div>
      </template>
    </UModal>

    <!-- Modal: Absence -->
    <UModal v-model:open="absModalOpen" title="Saisir une Absence / Congé">
      <template #content>
        <div class="p-6 space-y-4 bg-white border border-slate-200">
          <h2 class="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Saisir Absence</h2>
          
          <div class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Motif de l'absence</label>
                <select v-model="absCode" class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-none text-sm bg-white select">
                  <option value="CONGES">Congés payés</option>
                  <option value="MALADIE">Maladie</option>
                  <option value="AT">Accident du travail</option>
                  <option value="SANS_SOLDE">Absence non autorisée (Sans solde)</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Nbr jours d'absence</label>
                <input v-model="absNbrJour" type="number" step="0.5" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Date début</label>
                <input v-model="absDateDebut" type="date" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Date fin</label>
                <input v-model="absDateFin" type="date" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
              </div>
            </div>

            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Nombre d'heures correspondantes (Si contrat horaire)</label>
              <input v-model="absNbrHeure" type="number" step="1" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button type="button" @click="absModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-none hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
              Annuler
            </button>
            <button type="button" @click="handleAddAbsence" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-none shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
              Enregistrer et Recalculer
            </button>
          </div>
        </div>
      </template>
    </UModal>

    <!-- Modal: Prime -->
    <UModal v-model:open="primeModalOpen" title="Saisir une Prime">
      <template #content>
        <div class="p-6 space-y-4 bg-white border border-slate-200">
          <h2 class="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Nouvelle Prime</h2>
          
          <div class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Code Identifiant</label>
                <select v-model="primeCode" class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-none text-sm bg-white select">
                  <option value="PRIME_RENDEMENT">PRIME_RENDEMENT</option>
                  <option value="PRIME_ASSIDUITE">PRIME_ASSIDUITE</option>
                  <option value="PRIME_EXCEP">PRIME_EXCEP</option>
                  <option value="PRIME_ANCIENNETE">PRIME_ANCIENNETE</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Mode de saisie</label>
                <select v-model="primeMode" class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-none text-sm bg-white select">
                  <option value="direct">Montant Direct</option>
                  <option value="calcul">Calcul par Base et Taux</option>
                </select>
              </div>
            </div>

            <div v-if="primeMode === 'calcul'" class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Base (FCFA)</label>
                <input v-model="primeBase" type="number" @input="primeMontant = (Number(primeBase) || 0) * ((Number(primeTaux) || 0) / 100)" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Taux (%)</label>
                <input v-model="primeTaux" type="number" step="0.01" @input="primeMontant = (Number(primeBase) || 0) * ((Number(primeTaux) || 0) / 100)" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Montant de la prime (FCFA)</label>
                <input v-model="primeMontant" type="number" :disabled="primeMode === 'calcul'" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white disabled:bg-slate-100" />
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Libellé (Affiché sur le bulletin)</label>
                <input v-model="primeLibelle" type="text" placeholder="Ex: Prime de rendement" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
              </div>
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button type="button" @click="primeModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-none hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
              Annuler
            </button>
            <button type="button" @click="handleAddPrime" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-none shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
              Enregistrer et Recalculer
            </button>
          </div>
        </div>
      </template>
    </UModal>

    <!-- Modal: Acompte -->
    <UModal v-model:open="acompteModalOpen" title="Définir un Acompte">
      <template #content>
        <div class="p-6 space-y-4 bg-white border border-slate-200">
          <h2 class="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Acompte sur salaire</h2>
          
          <div class="space-y-4">
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Montant de l'acompte (FCFA)</label>
              <input v-model="acompteMontant" type="number" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
              <p class="text-[10px] text-slate-500 mt-1">Sera déduit directement du salaire net à payer.</p>
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button type="button" @click="acompteModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-none hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
              Annuler
            </button>
            <button type="button" @click="handleSaveAcompte" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-none shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
              Enregistrer et Recalculer
            </button>
          </div>
        </div>
      </template>
    </UModal>

    <!-- Modal: Option -->
    <UModal v-model:open="optionModalOpen" title="Saisir une Option / Avantage">
      <template #content>
        <div class="p-6 space-y-4 bg-white border border-slate-200">
          <h2 class="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Option ou Avantage</h2>
          
          <div class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Type d'option</label>
                <select v-model="optionCode" class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-none text-sm bg-white select">
                  <option value="AVANTAGE_LOGEMENT">Avantage Logement</option>
                  <option value="AVANTAGE_VEHICULE">Avantage Véhicule</option>
                  <option value="AVANTAGE_NOURRITURE">Avantage Nourriture</option>
                  <option value="AVANTAGE_AUTRE">Autre avantage en nature</option>
                  <option value="FRAIS_PROFESSIONNELS">Frais professionnels</option>
                  <option value="AUTRE_GAIN">Autre gain libre</option>
                  <option value="AUTRE_RETENUE">Autre retenue libre</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Montant (FCFA)</label>
                <input v-model="optionMontant" type="number" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
              </div>
            </div>
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Libellé (Affiché sur le bulletin)</label>
              <input v-model="optionLibelle" type="text" placeholder="Ex: Logement de fonction" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button type="button" @click="optionModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-none hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
              Annuler
            </button>
            <button type="button" @click="handleAddOption" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-none shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
              Enregistrer et Recalculer
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

@media print {
  .no-print {
    display: none !important;
  }
  .print-payslip {
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    max-w: 100% !important;
    background: white !important;
    color: black !important;
  }
  body {
    background-color: white !important;
  }
}
</style>
