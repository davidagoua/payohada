<script setup>
const route = useRoute()
const router = useRouter()
const { get, post } = useApi()
const toast = useToast()

const dossierId = route.params.dossierId
const etabId = route.params.etabId

const loadingContext = ref(true)
const currentDossier = useState('current-dossier')
const currentEtab = ref(null)

// Form Fields
const salMatricule = ref('')
const salNom = ref('')
const salPrenom = ref('')
const salCivilite = ref('M.')
const salNir = ref('')
const salEmail = ref('')
const salPhone = ref('')
const salIban = ref('')
const salBic = ref('')
const salExpatrie = ref(false)

const fetchContextDetails = async () => {
  loadingContext.value = true
  try {
    if (!currentDossier.value) {
      const data = await get(`/dossiers/${dossierId}`)
      currentDossier.value = data
    }
    const etabData = await get(`/etablissements/${etabId}`)
    currentEtab.value = etabData
  } catch (e) {
    console.error(e)
    router.push(`/dossiers/${dossierId}`)
  } finally {
    loadingContext.value = false
  }
}

const handleCreateSalarie = async () => {
  if (!salNom.value || !salPrenom.value) {
    toast.add({
      title: 'Validation',
      description: 'Le nom et le prénom sont obligatoires.',
      color: 'warning'
    })
    return
  }

  try {
    const payload = {
      nom: salNom.value,
      prenom: salPrenom.value,
      civilite: salCivilite.value,
      numero_securite_sociale: salNir.value || null,
      email: salEmail.value || null,
      telephone: salPhone.value || null,
      iban: salIban.value || null,
      bic: salBic.value || null,
      expatrie: salExpatrie.value
    }

    const res = await post(`/etablissements/${etabId}/salaries`, payload)
    if (res) {
      toast.add({
        title: 'Salarié créé',
        description: `Le salarié ${res.prenom} ${res.nom} a été créé. Veuillez maintenant définir son contrat de travail.`,
        color: 'success'
      })
      // Next Step: Redirect to contract creation page for this new employee
      router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${res.id}/contrats/new`)
    }
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  fetchContextDetails()
})
</script>

<template>
  <div v-if="loadingContext" class="flex flex-col items-center justify-center py-20 space-y-4">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement du contexte...</span>
  </div>

  <div v-else class="max-w-2xl mx-auto space-y-6">
    <!-- Header Page -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-50 text-green-700 rounded-full flex items-center justify-center font-bold text-xl border border-green-200">
          <UIcon name="i-lucide-user-plus" class="w-6 h-6" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-900 leading-tight">Nouvel Employé</h1>
          <p class="text-xs text-slate-500 mt-1">Dossier : {{ currentDossier?.nom_dossier }} | Établissement : {{ currentEtab?.raison_sociale }}</p>
        </div>
      </div>
    </div>

    <!-- Main Form -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <form @submit.prevent="handleCreateSalarie" class="space-y-6">
        <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">État Civil & Informations Générales</h3>

        <div class="grid grid-cols-3 gap-4">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Civilité</label>
            <select v-model="salCivilite" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
              <option value="M.">Monsieur (M.)</option>
              <option value="MME">Madame (Mme)</option>
            </select>
          </div>
          <div class="col-span-2">
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Matricule</label>
            <input 
              type="text" 
              disabled
              value="Généré automatiquement" 
              class="mt-1 block w-full px-3 py-2 border border-slate-200 bg-slate-50 rounded-lg text-sm font-mono text-slate-500 cursor-not-allowed" 
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Prénom <span class="text-red-500">*</span></label>
            <input 
              v-model="salPrenom" 
              type="text" 
              required
              placeholder="Jean" 
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" 
            />
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom de famille <span class="text-red-500">*</span></label>
            <input 
              v-model="salNom" 
              type="text" 
              required
              placeholder="Dupont" 
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" 
            />
          </div>
        </div>

        <div class="grid grid-cols-3 gap-4">
          <div class="col-span-2">
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Numéro de Sécurité Sociale (NIR)</label>
            <input 
              v-model="salNir" 
              type="text" 
              placeholder="15 chiffres (Ex: 180017500123456)" 
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" 
            />
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Régime Expatrié</label>
            <select v-model="salExpatrie" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
              <option :value="false">Non (Local)</option>
              <option :value="true">Oui (Expatrié)</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Email Personnel</label>
            <input 
              v-model="salEmail" 
              type="email" 
              placeholder="jean.dupont@gmail.com" 
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" 
            />
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Téléphone</label>
            <input 
              v-model="salPhone" 
              type="text" 
              placeholder="0607080910" 
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" 
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4 border-t border-slate-100 pt-4">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">IBAN Versement Salaire</label>
            <input 
              v-model="salIban" 
              type="text" 
              placeholder="FR76..."
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" 
            />
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">BIC</label>
            <input 
              v-model="salBic" 
              type="text" 
              placeholder="Ex: CEIDFRPP..."
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" 
            />
          </div>
        </div>

        <div class="flex justify-end space-x-3 pt-4 border-t border-slate-100">
          <NuxtLink 
            :to="`/dossiers/${dossierId}/etablissements/${etabId}`" 
            class="px-4 py-2 border border-slate-200 text-sm font-semibold rounded-lg hover:bg-slate-50 text-slate-700 transition-colors"
          >
            Annuler
          </NuxtLink>
          <button 
            type="submit" 
            class="px-4 py-2 text-sm font-semibold bg-green-600 hover:bg-green-700 text-white rounded-lg shadow transition-colors"
          >
            Créer et configurer le contrat
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
