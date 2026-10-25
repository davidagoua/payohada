<script setup>
/**
 * Espace salarié — congés.
 *
 * Le salarié consulte son solde (calculé par le serveur, le même que celui du
 * bulletin), dépose une demande et suit la décision de son entreprise.
 */
const { get, post } = useApi()
const toast = useToast()

const MOIS = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
]

const solde = ref(null)
const demandes = ref([])
const chargement = ref(true)
const envoiEnCours = ref(false)
const erreur = ref('')

const form = ref({ date_debut: '', date_fin: '', motif: '' })

const joursDemandes = computed(() => {
  if (!form.value.date_debut || !form.value.date_fin) return 0
  const debut = new Date(form.value.date_debut)
  const fin = new Date(form.value.date_fin)
  const jours = Math.floor((fin - debut) / 86400000) + 1
  return jours > 0 ? jours : 0
})

const libelleMois = (mois, annee) => `${MOIS[(mois || 1) - 1]} ${annee}`

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
    const [monSolde, mesDemandes] = await Promise.all([
      get('/demandes/conges/solde'),
      get('/demandes/conges')
    ])
    solde.value = monSolde
    demandes.value = mesDemandes || []
  } catch (e) {
    console.error('Chargement des congés impossible :', e)
    toast.add({ title: 'Congés indisponibles', color: 'danger' })
  } finally {
    chargement.value = false
  }
}

const deposer = async () => {
  erreur.value = ''
  if (!form.value.date_debut || !form.value.date_fin) {
    erreur.value = 'Renseignez les deux dates.'
    return
  }
  if (joursDemandes.value <= 0) {
    erreur.value = 'La date de fin doit être postérieure au début.'
    return
  }
  envoiEnCours.value = true
  try {
    await post('/demandes/conges', {
      date_debut: form.value.date_debut,
      date_fin: form.value.date_fin,
      motif: form.value.motif || null
    })
    toast.add({
      title: 'Demande envoyée',
      description: `${joursDemandes.value} jour(s) — votre entreprise doit maintenant la valider.`,
      color: 'success'
    })
    form.value = { date_debut: '', date_fin: '', motif: '' }
    await charger()
  } catch (e) {
    const detail = e?.data?.detail
    erreur.value = typeof detail === 'string' ? detail : 'La demande n\'a pas pu être envoyée.'
  } finally {
    envoiEnCours.value = false
  }
}

const formatDate = (valeur) => {
  if (!valeur) return '—'
  const [a, m, j] = String(valeur).slice(0, 10).split('-')
  return `${j}/${m}/${a}`
}

onMounted(charger)
</script>

<template>
  <div class="space-y-6">
    <!-- En-tête -->
    <div class="bg-white border-2 border-slate-200 p-6 shadow-flat border-t-4 border-t-navy-900">
      <h1 class="text-2xl font-black text-navy-900 uppercase">
        Mes congés
      </h1>
      <p class="text-sm text-slate-500 font-medium mt-1">
        Consultez votre solde, déposez une demande et suivez la décision de votre entreprise.
      </p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Solde -->
      <div class="bg-white border-2 border-slate-200 p-6 shadow-flat space-y-4">
        <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider">
          Mon solde
        </h2>
        <div
          v-if="chargement"
          class="text-sm text-slate-400"
        >
          Calcul en cours…
        </div>
        <template v-else-if="solde">
          <p class="text-4xl font-black text-navy-900">
            {{ solde.solde }}<span class="text-lg font-bold text-slate-400"> j</span>
          </p>
          <dl class="text-sm divide-y divide-slate-100">
            <div class="flex justify-between py-1.5">
              <dt class="text-slate-500">
                Droits acquis
              </dt>
              <dd class="font-semibold text-slate-800">
                {{ solde.acquis }} j
              </dd>
            </div>
            <div class="flex justify-between py-1.5">
              <dt class="text-slate-500">
                Jours pris
              </dt>
              <dd class="font-semibold text-slate-800">
                {{ solde.pris }} j
              </dd>
            </div>
            <div class="flex justify-between py-1.5">
              <dt class="text-slate-500">
                Ancienneté retenue
              </dt>
              <dd class="font-semibold text-slate-800">
                {{ solde.mois_anciennete }} mois
              </dd>
            </div>
          </dl>
          <p class="text-[11px] text-slate-400">
            Solde arrêté à fin {{ libelleMois(solde.mois, solde.annee) }}, sur la base de
            {{ solde.mois_anciennete }} mois d'ancienneté depuis le {{ formatDate(solde.debut_anciennete) }}.
          </p>
          <p
            v-if="solde.periode_avant_contrat"
            class="text-[11px] text-amber-600 font-semibold"
          >
            Le mois en cours précède le début de votre contrat : aucun droit n'est encore ouvert.
          </p>
        </template>
      </div>

      <!-- Demande -->
      <div class="lg:col-span-2 bg-white border-2 border-slate-200 p-6 shadow-flat space-y-4">
        <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider">
          Demander des congés
        </h2>
        <form
          class="grid grid-cols-1 sm:grid-cols-2 gap-4"
          @submit.prevent="deposer"
        >
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Date de début</label>
            <input
              v-model="form.date_debut"
              type="date"
              required
              class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white"
            >
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Date de fin</label>
            <input
              v-model="form.date_fin"
              type="date"
              required
              class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white"
            >
          </div>
          <div class="sm:col-span-2">
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Motif (facultatif)</label>
            <input
              v-model="form.motif"
              type="text"
              maxlength="1000"
              placeholder="Congés annuels, événement familial…"
              class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white"
            >
          </div>
          <div class="sm:col-span-2 flex flex-wrap items-center justify-between gap-3">
            <p class="text-xs text-slate-500">
              Durée demandée : <strong>{{ joursDemandes }} jour(s)</strong>
              <span
                v-if="solde"
                class="text-slate-400"
              >· solde actuel {{ solde.solde }} j</span>
            </p>
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
        <p class="text-[11px] text-slate-400">
          Votre demande est transmise au gestionnaire de votre entreprise. Une fois validée,
          elle est enregistrée comme absence et prise en compte dans votre bulletin.
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
        Aucune demande de congés pour l'instant.
      </div>
      <div
        v-else
        class="overflow-x-auto"
      >
        <table class="min-w-full text-sm">
          <thead class="bg-slate-50 text-slate-500 uppercase tracking-wider text-[11px]">
            <tr>
              <th class="px-4 py-2 text-left font-semibold">
                Période
              </th>
              <th class="px-4 py-2 text-right font-semibold">
                Jours
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
                {{ formatDate(demande.date_debut) }} → {{ formatDate(demande.date_fin) }}
              </td>
              <td class="px-4 py-2.5 text-right font-mono">
                {{ demande.nombre_jours }}
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
