<script setup>
/**
 * Espace salarié — acomptes.
 *
 * Le salarié demande une avance sur la paie d'un mois ; une fois validée par
 * son entreprise, elle est retenue sur le bulletin de ce mois, sans ressaisie.
 */
const { get, post } = useApi()
const toast = useToast()

const MOIS = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
]

const maintenant = new Date()
const demandes = ref([])
const chargement = ref(true)
const envoiEnCours = ref(false)
const erreur = ref('')

const form = ref({
  montant: null,
  mois: maintenant.getMonth() + 1,
  annee: maintenant.getFullYear(),
  motif: ''
})

const annees = computed(() => {
  const courante = maintenant.getFullYear()
  return [courante, courante + 1, courante - 1]
})

const formatFCFA = montant =>
  new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(montant || 0) + ' FCFA'

const classeStatut = statut => ({
  en_attente: 'bg-amber-50 text-amber-700 border-amber-200',
  validee: 'bg-green-50 text-green-700 border-green-200',
  refusee: 'bg-red-50 text-red-700 border-red-200'
}[statut] || 'bg-slate-50 text-slate-600 border-slate-200')

const libelleStatut = statut => ({
  en_attente: 'En attente',
  validee: 'Validée',
  refusee: 'Refusée'
}[statut] || statut)

const charger = async () => {
  chargement.value = true
  try {
    demandes.value = (await get('/demandes/acomptes')) || []
  } catch (e) {
    console.error('Chargement des acomptes impossible :', e)
    toast.add({ title: 'Acomptes indisponibles', color: 'danger' })
  } finally {
    chargement.value = false
  }
}

const deposer = async () => {
  erreur.value = ''
  const montant = Number(form.value.montant || 0)
  if (montant <= 0) {
    erreur.value = 'Saisissez un montant supérieur à zéro.'
    return
  }
  envoiEnCours.value = true
  try {
    await post('/demandes/acomptes', {
      montant,
      mois: Number(form.value.mois),
      annee: Number(form.value.annee),
      motif: form.value.motif || null
    })
    toast.add({
      title: 'Demande envoyée',
      description: `${formatFCFA(montant)} — votre entreprise doit maintenant la valider.`,
      color: 'success'
    })
    form.value = { ...form.value, montant: null, motif: '' }
    await charger()
  } catch (e) {
    const detail = e?.data?.detail
    erreur.value = typeof detail === 'string' ? detail : 'La demande n\'a pas pu être envoyée.'
  } finally {
    envoiEnCours.value = false
  }
}

onMounted(charger)
</script>

<template>
  <div class="space-y-6">
    <!-- En-tête -->
    <div class="bg-white border-2 border-slate-200 p-6 shadow-flat border-t-4 border-t-navy-900">
      <h1 class="text-2xl font-black text-navy-900 uppercase">
        Mes acomptes
      </h1>
      <p class="text-sm text-slate-500 font-medium mt-1">
        Demandez une avance sur la paie d'un mois : une fois validée par votre entreprise,
        elle est retenue sur le bulletin correspondant.
      </p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Explication -->
      <div class="bg-white border-2 border-slate-200 p-6 shadow-flat space-y-3">
        <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider">
          Comment ça marche
        </h2>
        <ol class="text-xs text-slate-600 space-y-2 list-decimal list-inside">
          <li>Vous indiquez le montant et le mois concerné.</li>
          <li>Le gestionnaire de votre entreprise valide ou refuse.</li>
          <li>Si c'est validé, le montant est déduit du net à payer de ce mois.</li>
        </ol>
        <p class="text-[11px] text-slate-400">
          Une demande refusée ne produit aucune retenue. Le bulletin validé est figé :
          une demande ne peut plus y entrer.
        </p>
      </div>

      <!-- Demande -->
      <div class="lg:col-span-2 bg-white border-2 border-slate-200 p-6 shadow-flat space-y-4">
        <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider">
          Demander un acompte
        </h2>
        <form
          class="grid grid-cols-1 sm:grid-cols-3 gap-4"
          @submit.prevent="deposer"
        >
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Montant (FCFA)</label>
            <input
              v-model.number="form.montant"
              type="number"
              min="1"
              step="1"
              required
              placeholder="50 000"
              class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white"
            >
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Mois de paie</label>
            <select
              v-model.number="form.mois"
              class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white"
            >
              <option
                v-for="(libelle, index) in MOIS"
                :key="index"
                :value="index + 1"
              >
                {{ libelle }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Année</label>
            <select
              v-model.number="form.annee"
              class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white"
            >
              <option
                v-for="annee in annees"
                :key="annee"
                :value="annee"
              >
                {{ annee }}
              </option>
            </select>
          </div>
          <div class="sm:col-span-3">
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Motif (facultatif)</label>
            <input
              v-model="form.motif"
              type="text"
              maxlength="1000"
              placeholder="Frais imprévus, rentrée scolaire…"
              class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white"
            >
          </div>
          <div class="sm:col-span-3 flex justify-end">
            <button
              type="submit"
              :disabled="envoiEnCours"
              class="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white text-xs font-bold uppercase tracking-wider shadow-flat inline-flex items-center gap-1.5"
            >
              <UIcon
                :name="envoiEnCours ? 'i-lucide-loader-2' : 'i-lucide-send'"
                class="w-4 h-4"
                :class="{ 'animate-spin': envoiEnCours }"
              />
              Envoyer la demande
            </button>
          </div>
        </form>
        <p
          v-if="erreur"
          class="text-xs font-semibold text-red-600"
        >
          {{ erreur }}
        </p>
      </div>
    </div>

    <!-- Historique -->
    <div class="bg-white border-2 border-slate-200 p-6 shadow-flat">
      <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider mb-4">
        Mes demandes
      </h2>
      <div
        v-if="!demandes.length"
        class="text-sm text-slate-400 py-6 text-center"
      >
        Aucune demande d'acompte pour l'instant.
      </div>
      <div
        v-else
        class="overflow-x-auto"
      >
        <table class="min-w-full text-sm">
          <thead class="bg-slate-50 text-slate-500 uppercase tracking-wider text-[11px]">
            <tr>
              <th class="px-4 py-2 text-left font-semibold">
                Mois de paie
              </th>
              <th class="px-4 py-2 text-right font-semibold">
                Montant
              </th>
              <th class="px-4 py-2 text-left font-semibold">
                Motif
              </th>
              <th class="px-4 py-2 text-left font-semibold">
                Statut
              </th>
              <th class="px-4 py-2 text-left font-semibold">
                Réponse
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="demande in demandes"
              :key="demande.id"
              class="hover:bg-slate-50"
            >
              <td class="px-4 py-2.5 font-medium text-slate-800">
                {{ MOIS[(demande.mois || 1) - 1] }} {{ demande.annee }}
              </td>
              <td class="px-4 py-2.5 text-right font-mono">
                {{ formatFCFA(demande.montant) }}
              </td>
              <td class="px-4 py-2.5 text-slate-500">
                {{ demande.motif || '—' }}
              </td>
              <td class="px-4 py-2.5">
                <span
                  class="inline-flex px-2 py-0.5 border text-[11px] font-bold uppercase tracking-wide"
                  :class="classeStatut(demande.statut)"
                >
                  {{ libelleStatut(demande.statut) }}
                </span>
              </td>
              <td class="px-4 py-2.5 text-slate-500">
                {{ demande.commentaire_gestionnaire || '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
