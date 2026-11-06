<script setup>
/**
 * Modales de saisie des variables d'un bulletin (heures supplémentaires,
 * absence, prime, acompte). Chaque saisie recalcule le bulletin du contrat
 * puis émet `recalcule` pour que la liste se rafraîchisse.
 */
const props = defineProps({
  contracts: { type: Array, required: true },
  bulletinsMap: { type: Object, required: true },
  mois: { type: [String, Number], required: true },
  annee: { type: [String, Number], required: true }
})
const emit = defineEmits(['recalcule'])
const { contracts, bulletinsMap, mois, annee } = toRefs(props)

const { get, post } = useApi()
const toast = useToast()

// Active context for modal actions
const activeContrat = ref(null)
const activeBulletin = ref(null)

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
const primeEstPersistant = ref(false)

// Acompte state
const acompteModalOpen = ref(false)
const acompteMontant = ref(0)

// Plan de paie items & dynamic lists
const planPaieItems = ref([])

const primesDisponibles = computed(() => {
  const excludedCodes = ['BASE', 'SURSALAIRE', 'ABS', '1001', '1051', '1101', '1111', '1121', '1131', '1141', '1151', '1161', '1181']
  return planPaieItems.value.filter(item => {
    return item.type === 'B' &&
           !excludedCodes.includes(item.code) &&
           !item.code.startsWith('HS_') &&
           !item.code.startsWith('ABS_') &&
           item.est_actif
  })
})

const fetchPlanPaie = async () => {
  try {
    planPaieItems.value = await get('/plan-paie') || []
  } catch (e) {
    console.error("Error loading plan de paie:", e)
  }
}

watch(primeCode, (newCode) => {
  const match = primesDisponibles.value.find(p => p.code === newCode)
  if (match) {
    primeLibelle.value = match.libelle
  }
})

watch(primeModalOpen, (isOpen) => {
  if (isOpen && primesDisponibles.value.length > 0) {
    if (!primesDisponibles.value.some(p => p.code === primeCode.value)) {
      primeCode.value = primesDisponibles.value[0].code
    }
    const match = primesDisponibles.value.find(p => p.code === primeCode.value)
    if (match) {
      primeLibelle.value = match.libelle
    }
  }
})

// Modal quick open handlers
const openPrimeModal = (contratId) => {
  activeContrat.value = contracts.value.find(c => c.id === contratId)
  activeBulletin.value = bulletinsMap.value[contratId]
  if (primesDisponibles.value.length > 0) {
    primeCode.value = primesDisponibles.value[0].code
    primeLibelle.value = primesDisponibles.value[0].libelle
  } else {
    primeCode.value = 'PRIME_RENDEMENT'
    primeLibelle.value = 'Prime de rendement'
  }
  primeMontant.value = 0
  primeMode.value = 'direct'
  primeBase.value = 0
  primeTaux.value = 0
  primeEstPersistant.value = false
  primeModalOpen.value = true
}

const openAbsModal = (contratId) => {
  activeContrat.value = contracts.value.find(c => c.id === contratId)
  activeBulletin.value = bulletinsMap.value[contratId]
  absCode.value = 'CONGES'
  absDateDebut.value = ''
  absDateFin.value = ''
  absNbrHeure.value = 0
  absNbrJour.value = 0
  absModalOpen.value = true
}

const openHsModal = (contratId) => {
  activeContrat.value = contracts.value.find(c => c.id === contratId)
  activeBulletin.value = bulletinsMap.value[contratId]
  hsCode.value = 'HS_15'
  hsNombre.value = 0
  hsModalOpen.value = true
}

const openAcompteModal = (contratId) => {
  const b = bulletinsMap.value[contratId]
  activeContrat.value = contracts.value.find(c => c.id === contratId)
  activeBulletin.value = b
  if (b) {
    const acompteLine = (b.lignes || []).find(l => l.code === 'ACOMPTE')
    acompteMontant.value = acompteLine ? acompteLine.montant_cs : 0
  } else {
    acompteMontant.value = 0
  }
  acompteModalOpen.value = true
}

// Recalculate helper
const handleRecalculateForContrat = async (contratId, acompteVal = 0) => {
  try {
    const payload = {
      contrat_id: contratId,
      mois: Number(mois.value),
      annee: Number(annee.value),
      acompte: Number(acompteVal),
      commentaire: "Recalculé suite à modification des variables"
    }
    const res = await post('/bulletins/calculer', payload)
    if (res) {
      toast.add({
        title: 'Bulletin Recalculé',
        description: 'Les modifications ont été prises en compte.',
        color: 'success'
      })
      emit('recalcule')
    }
  } catch (e) {
    console.error(e)
  }
}

// Modal submits
const handleAddHeureSupp = async () => {
  if (hsNombre.value <= 0) {
    toast.add({ title: 'Validation', description: 'Le nombre d\'heures doit être supérieur à 0.', color: 'warning' })
    return
  }
  try {
    const payload = {
      code: hsCode.value,
      nombre: Number(hsNombre.value),
      mois: Number(mois.value),
      annee: String(annee.value)
    }
    await post(`/contrats/${activeContrat.value.id}/heures-supplementaires`, payload)
    hsModalOpen.value = false
    hsNombre.value = 0

    let currentAcompte = 0
    if (activeBulletin.value) {
      const acompteLine = (activeBulletin.value.lignes || []).find(l => l.code === 'ACOMPTE')
      if (acompteLine) currentAcompte = acompteLine.montant_cs || 0
    }
    await handleRecalculateForContrat(activeContrat.value.id, currentAcompte)
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
      mois: Number(mois.value),
      annee: String(annee.value)
    }
    await post(`/contrats/${activeContrat.value.id}/absences`, payload)
    absModalOpen.value = false
    absDateDebut.value = ''
    absDateFin.value = ''
    absNbrHeure.value = 0
    absNbrJour.value = 0

    let currentAcompte = 0
    if (activeBulletin.value) {
      const acompteLine = (activeBulletin.value.lignes || []).find(l => l.code === 'ACOMPTE')
      if (acompteLine) currentAcompte = acompteLine.montant_cs || 0
    }
    await handleRecalculateForContrat(activeContrat.value.id, currentAcompte)
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
      mois: Number(mois.value),
      annee: String(annee.value),
      est_persistant: primeEstPersistant.value
    }
    await post(`/contrats/${activeContrat.value.id}/primes`, payload)
    primeModalOpen.value = false
    primeLibelle.value = ''
    primeMontant.value = 0
    primeBase.value = 0
    primeTaux.value = 0
    primeEstPersistant.value = false

    let currentAcompte = 0
    if (activeBulletin.value) {
      const acompteLine = (activeBulletin.value.lignes || []).find(l => l.code === 'ACOMPTE')
      if (acompteLine) currentAcompte = acompteLine.montant_cs || 0
    }
    await handleRecalculateForContrat(activeContrat.value.id, currentAcompte)
  } catch (e) {
    console.error(e)
  }
}

const handleSaveAcompte = async () => {
  acompteModalOpen.value = false
  await handleRecalculateForContrat(activeContrat.value.id, acompteMontant.value)
}

defineExpose({ openPrimeModal, openAbsModal, openHsModal, openAcompteModal })

onMounted(fetchPlanPaie)
</script>

<template>
  <div>
  <!-- Modals for adding variables -->

  <!-- Modal: Overtime -->
  <UModal v-model:open="hsModalOpen" title="Saisir des Heures Supplémentaires">
    <template #content>
      <div class="p-6 space-y-4 rounded-xl bg-white border border-slate-200">
        <h2 class="text-lg font-bold text-navy-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Nouvelle Heure Supp.</h2>

        <div class="space-y-4">
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Taux de majoration</label>
            <select v-model="hsCode" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white select">
              <option value="HS_15">Majoration à 15%</option>
              <option value="HS_25">Majoration à 25%</option>
              <option value="HS_50">Majoration à 50%</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Nombre d'heures</label>
            <input v-model="hsNombre" type="number" step="0.5" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
          </div>
        </div>

        <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
          <button type="button" @click="hsModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-lg hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
            Annuler
          </button>
          <button type="button" @click="handleAddHeureSupp" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-lg shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
            Enregistrer et Recalculer
          </button>
        </div>
      </div>
    </template>
  </UModal>

  <!-- Modal: Absence -->
  <UModal v-model:open="absModalOpen" title="Saisir une Absence / Congé">
    <template #content>
      <div class="p-6 space-y-4 rounded-xl bg-white border border-slate-200">
        <h2 class="text-lg font-bold text-navy-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Saisir Absence</h2>

        <div class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Motif de l'absence</label>
              <select v-model="absCode" class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-lg text-sm bg-white select">
                <option value="CONGES">Congés payés</option>
                <option value="MALADIE">Maladie</option>
                <option value="AT">Accident du travail</option>
                <option value="SANS_SOLDE">Absence non autorisée (Sans solde)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Nbr jours d'absence</label>
              <input v-model="absNbrJour" type="number" step="0.5" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Date début</label>
              <input v-model="absDateDebut" type="date" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Date fin</label>
              <input v-model="absDateFin" type="date" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Nombre d'heures correspondantes (Si contrat horaire)</label>
            <input v-model="absNbrHeure" type="number" step="1" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
          </div>
        </div>

        <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
          <button type="button" @click="absModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-lg hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
            Annuler
          </button>
          <button type="button" @click="handleAddAbsence" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-lg shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
            Enregistrer et Recalculer
          </button>
        </div>
      </div>
    </template>
  </UModal>

  <!-- Modal: Prime -->
  <UModal v-model:open="primeModalOpen" title="Saisir une Prime">
    <template #content>
      <div class="p-6 space-y-4 rounded-xl bg-white border border-slate-200">
        <h2 class="text-lg font-bold text-navy-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Nouvelle Prime</h2>

        <div class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Code Identifiant</label>
              <select v-model="primeCode" class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-lg text-sm bg-white select">
                <option v-for="p in primesDisponibles" :key="p.code" :value="p.code">
                  {{ p.libelle }} ({{ p.code }})
                </option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Mode de saisie</label>
              <select v-model="primeMode" class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-lg text-sm bg-white select">
                <option value="direct">Montant Direct</option>
                <option value="calcul">Calcul par Base et Taux</option>
              </select>
            </div>
          </div>

          <div v-if="primeMode === 'calcul'" class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Base (FCFA)</label>
              <input v-model="primeBase" type="number" @input="primeMontant = (Number(primeBase) || 0) * ((Number(primeTaux) || 0) / 100)" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Taux (%)</label>
              <input v-model="primeTaux" type="number" step="0.01" @input="primeMontant = (Number(primeBase) || 0) * ((Number(primeTaux) || 0) / 100)" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Montant de la prime (FCFA)</label>
              <input v-model="primeMontant" type="number" :disabled="primeMode === 'calcul'" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white disabled:bg-slate-100" />
            </div>
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Libellé (Affiché sur le bulletin)</label>
              <input v-model="primeLibelle" type="text" placeholder="Ex: Prime de rendement" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>
          <div class="flex items-center space-x-2 pt-2">
            <input v-model="primeEstPersistant" type="checkbox" id="prime_est_persistant" class="w-4 h-4 text-green-600 focus:ring-green-500 border-slate-300 rounded" />
            <label for="prime_est_persistant" class="text-xs font-semibold uppercase tracking-wider text-slate-500 cursor-pointer">
              Répéter les mois suivants (Persistant)
            </label>
          </div>
        </div>

        <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
          <button type="button" @click="primeModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-lg hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
            Annuler
          </button>
          <button type="button" @click="handleAddPrime" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-lg shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
            Enregistrer et Recalculer
          </button>
        </div>
      </div>
    </template>
  </UModal>

  <!-- Modal: Acompte -->
  <UModal v-model:open="acompteModalOpen" title="Définir un Acompte">
    <template #content>
      <div class="p-6 space-y-4 rounded-xl bg-white border border-slate-200">
        <h2 class="text-lg font-bold text-navy-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Acompte sur salaire</h2>

        <div class="space-y-4">
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Montant de l'acompte (FCFA)</label>
            <input v-model="acompteMontant" type="number" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            <p class="text-[10px] text-slate-500 mt-1">Sera déduit directement du salaire net à payer.</p>
          </div>
        </div>

        <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
          <button type="button" @click="acompteModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-lg hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
            Annuler
          </button>
          <button type="button" @click="handleSaveAcompte" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-lg shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
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
</style>

