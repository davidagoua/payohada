<script setup>
const route = useRoute()
const router = useRouter()
const { get, post, extractFieldErrors } = useApi()
const toast = useToast()

const dossierId = route.params.dossierId
const etabId = route.params.etabId

const loadingContext = ref(true)
const currentDossier = useState('current-dossier')
const currentEtab = ref(null)

// Form Fields
const salMatricule = ref('')
const fieldErrors = ref({})
const salNom = ref('')
const salPrenom = ref('')
const salCivilite = ref('M.')
const salNir = ref('')
const salEmail = ref('')
const salPhone = ref('')
const salIban = ref('')
const salBic = ref('')
const salExpatrie = ref(false)
const salSituationMatrimoniale = ref('Célibataire')
const salEnfantsCharge = ref(0)
const salModePaiementId = ref(null)
// Modes acceptés par l'établissement ; un seul mode est présélectionné.
const modesEtablissement = computed(() => currentEtab.value?.modes_paiement || [])
watch(modesEtablissement, (modes) => {
  if (modes.length === 1 && !salModePaiementId.value) salModePaiementId.value = modes[0].id
})

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
  fieldErrors.value = {}
  if (!salNom.value || !salPrenom.value) {
    toast.add({
      title: 'Validation',
      description: 'Le nom et le prénom sont obligatoires.',
      color: 'warning'
    })
    return
  }
  if (modesEtablissement.value.length && !salModePaiementId.value) {
    fieldErrors.value = { mode_paiement_id: 'Choisissez le mode de paiement du salarié.' }
    toast.add({
      title: 'Validation',
      description: 'Le mode de paiement du salarié est obligatoire.',
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
      mode_paiement_id: salModePaiementId.value,
      expatrie: salExpatrie.value,
      situation_matrimoniale: salSituationMatrimoniale.value,
      enfants_charge: salEnfantsCharge.value
    }

    const res = await post(`/etablissements/${etabId}/salaries`, payload)
    if (res) {
      // Un email sur la fiche crée le compte d'accès : on dit s'il a été envoyé.
      const envoi = res.acces_email_envoye
      toast.add({
        title: 'Salarié créé',
        description: envoi
          ? `Le salarié ${res.prenom} ${res.nom} a été créé et ses identifiants de connexion lui ont été envoyés. Veuillez maintenant définir son contrat de travail.`
          : `Le salarié ${res.prenom} ${res.nom} a été créé. Veuillez maintenant définir son contrat de travail.`,
        color: 'success'
      })
      if (envoi === false) {
        toast.add({
          title: 'Identifiants non envoyés',
          description: `L'email n'a pas pu partir${res.acces_email_message ? ` (${res.acces_email_message})` : ''}. Mot de passe provisoire : ${res.mot_de_passe_initial} — transmettez-le au salarié.`,
          color: 'warning',
          duration: 20000
        })
      }
      router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${res.id}/contrats/new`)
    }
  } catch (e) {
    console.error(e)
    if (e.status === 422) {
      fieldErrors.value = extractFieldErrors(e)
    }
  }
}

onMounted(() => {
  fetchContextDetails()
})
</script>

<template>
  <div v-if="loadingContext" class="flex flex-col items-center justify-center py-20 space-y-4">
    <Icon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement du contexte...</span>
  </div>

  <div v-else class="max-w-2xl mx-auto space-y-6">
    <!-- Header Page -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-navy-50 text-navy-700 rounded-full flex items-center justify-center font-bold text-xl border border-navy-200">
          <Icon name="i-lucide-user-plus" class="w-6 h-6" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-navy-900 leading-tight">Nouvel Employé</h1>
          <p class="text-xs text-slate-500 mt-1">Dossier : {{ currentDossier?.nom_dossier }} | Établissement : {{ currentEtab?.raison_sociale }}</p>
        </div>
      </div>
    </div>

    <!-- Main Form -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <form @submit.prevent="handleCreateSalarie" class="space-y-6">
        <h3 class="text-md font-bold text-navy-900 border-b border-slate-100 pb-2">État Civil & Informations Générales</h3>

        <div class="grid grid-cols-3 gap-4">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Civilité</label>
            <Select
              v-model="salCivilite"
              class="mt-1 block w-full text-sm"
              :options="[
                { label: `Monsieur (M.)`, value: 'M.' },
                { label: `Madame (Mme)`, value: 'MME' }
              ]"
              option-label="label"
              option-value="value"
            />
          </div>
          <div class="col-span-2">
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Matricule</label>
            <InputText
              disabled
              model-value="Généré automatiquement"
              class="mt-1 block w-full px-3 py-2 border border-slate-200 bg-slate-50 rounded-lg text-sm font-mono text-slate-500 cursor-not-allowed"
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Prénom <span class="text-red-500">*</span></label>
            <InputText
              v-model="salPrenom"
              required
              placeholder="Jean"
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm transition-colors',
                fieldErrors.prenom ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.prenom" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.prenom }}</p>
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom de famille <span class="text-red-500">*</span></label>
            <InputText
              v-model="salNom"
              required
              placeholder="Dupont"
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm transition-colors',
                fieldErrors.nom ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.nom" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.nom }}</p>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-4">
          <div class="col-span-2">
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">N° CNPS du salarié</label>
            <InputText
              v-model="salNir"
              inputmode="numeric"
              placeholder="12 chiffres (ex. 202100108350)"
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono transition-colors',
                fieldErrors.numero_securite_sociale ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.numero_securite_sociale" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.numero_securite_sociale }}</p>
            <p v-else-if="alerteNumeroCnps(salNir)" class="mt-1 text-xs text-yellow-700">{{ alerteNumeroCnps(salNir) }}</p>
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Régime Expatrié</label>
            <Select
              v-model="salExpatrie"
              class="mt-1 block w-full text-sm"
              :options="[
                { label: `Non (Local)`, value: false },
                { label: `Oui (Expatrié)`, value: true }
              ]"
              option-label="label"
              option-value="value"
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Situation Matrimoniale</label>
            <Select
              v-model="salSituationMatrimoniale"
              class="mt-1 block w-full text-sm"
              :options="[
                { label: `Célibataire`, value: 'Célibataire' },
                { label: `Marié(e)`, value: 'Marié' },
                { label: `Divorcé(e)`, value: 'Divorcé' },
                { label: `Veuf(ve)`, value: 'Veuf' }
              ]"
              option-label="label"
              option-value="value"
            />
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Enfants à charge</label>
            <InputText
              v-model.number="salEnfantsCharge"
              type="number"
              min="0"
              max="20"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Email Personnel</label>
            <InputText
              v-model="salEmail"
              type="email"
              placeholder="jean.dupont@gmail.com"
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm transition-colors',
                fieldErrors.email ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.email" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.email }}</p>
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Téléphone</label>
            <InputText
              v-model="salPhone"
              placeholder="0607080910"
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm transition-colors',
                fieldErrors.telephone ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.telephone" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.telephone }}</p>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4 border-t border-slate-100 pt-4">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">IBAN Versement Salaire</label>
            <InputText
              v-model="salIban"
              placeholder="FR76..."
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono transition-colors',
                fieldErrors.iban ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.iban" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.iban }}</p>
          </div>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">BIC</label>
            <InputText
              v-model="salBic"
              placeholder="Ex: CEIDFRPP..."
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono transition-colors',
                fieldErrors.bic ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.bic" class="mt-1 text-xs text-red-655 font-medium">{{ fieldErrors.bic }}</p>
          </div>
          <div class="col-span-2">
            <SalarieModePaiement
              v-model="salModePaiementId"
              :modes="modesEtablissement"
              :lien-etablissement="`/dossiers/${dossierId}/etablissements/${etabId}?tab=infos`"
              :erreur="fieldErrors.mode_paiement_id"
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
