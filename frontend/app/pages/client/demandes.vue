<script setup>
/**
 * Espace entreprise — demandes du personnel.
 *
 * Le gestionnaire reçoit ici les demandes de congés et d'acompte de ses
 * salariés. Ce qu'il valide entre dans la paie : le congé devient une absence,
 * l'acompte est retenu sur le bulletin du mois.
 */
const { get, post } = useApi()
const toast = useToast()

const MOIS = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
]

const conges = ref([])
const acomptes = ref([])
const chargement = ref(true)
const filtre = ref('en_attente') // en_attente | traitees | toutes
const recherche = ref('')
const decisionEnCours = ref(null)
const refus = ref({ ouvert: false, type: null, id: null, motif: '' })
const refusEnCours = ref(false)

const formaterFCFA = montant =>
  new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(montant || 0) + ' FCFA'

const formaterDate = (valeur) => {
  if (!valeur) return '—'
  const [annee, mois, jour] = String(valeur).slice(0, 10).split('-')
  return `${jour}/${mois}/${annee}`
}

const toutesLesDemandes = computed(() => {
  const liste = [
    ...conges.value.map(d => ({ ...d, type: 'conge' })),
    ...acomptes.value.map(d => ({ ...d, type: 'acompte' }))
  ]
  // En attente d'abord, puis les plus récentes.
  return liste.sort((a, b) => {
    if (a.statut !== b.statut) return a.statut === 'en_attente' ? -1 : 1
    return String(b.created_at || '').localeCompare(String(a.created_at || ''))
  })
})

const demandes = computed(() => {
  let liste = toutesLesDemandes.value
  if (filtre.value === 'en_attente') liste = liste.filter(d => d.statut === 'en_attente')
  if (filtre.value === 'traitees') liste = liste.filter(d => d.statut !== 'en_attente')
  if (recherche.value) {
    const terme = recherche.value.toLowerCase()
    liste = liste.filter(d =>
      `${d.salarie_prenom || ''} ${d.salarie_nom || ''} ${d.matricule || ''}`
        .toLowerCase()
        .includes(terme)
    )
  }
  return liste
})

const nombreEnAttente = computed(() =>
  toutesLesDemandes.value.filter(d => d.statut === 'en_attente').length
)

const detail = demande =>
  demande.type === 'conge'
    ? `Du ${formaterDate(demande.date_debut)} au ${formaterDate(demande.date_fin)} · ${demande.nombre_jours} j`
    : `${formaterFCFA(demande.montant)} · ${MOIS[(demande.mois || 1) - 1]} ${demande.annee}`

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
    const [demandesConges, demandesAcomptes] = await Promise.all([
      get('/demandes/conges'),
      get('/demandes/acomptes')
    ])
    conges.value = demandesConges || []
    acomptes.value = demandesAcomptes || []
  } catch (e) {
    console.error('Chargement des demandes impossible :', e)
    toast.add({ title: 'Demandes indisponibles', color: 'danger' })
  } finally {
    chargement.value = false
  }
}

const valider = async (demande) => {
  decisionEnCours.value = `${demande.type}-${demande.id}`
  try {
    await post(`/demandes/${demande.type === 'conge' ? 'conges' : 'acomptes'}/${demande.id}/valider`)
    toast.add({
      title: 'Demande validée',
      description: demande.type === 'conge'
        ? `Congé enregistré pour ${demande.salarie_prenom} ${demande.salarie_nom} : il entrera dans le prochain calcul du bulletin.`
        : `Acompte de ${formaterFCFA(demande.montant)} retenu sur le bulletin de ${MOIS[(demande.mois || 1) - 1]} ${demande.annee}.`,
      color: 'success'
    })
    await charger()
  } catch (e) {
    const detailErreur = e?.data?.detail
    toast.add({
      title: 'Validation impossible',
      description: typeof detailErreur === 'string' ? detailErreur : 'Une erreur est survenue.',
      color: 'danger'
    })
  } finally {
    decisionEnCours.value = null
  }
}

const ouvrirRefus = (demande) => {
  refus.value = { ouvert: true, type: demande.type, id: demande.id, motif: '', demande }
}

const confirmerRefus = async () => {
  refusEnCours.value = true
  try {
    const base = refus.value.type === 'conge' ? 'conges' : 'acomptes'
    await post(`/demandes/${base}/${refus.value.id}/refuser`, {
      commentaire: refus.value.motif || null
    })
    toast.add({
      title: 'Demande refusée',
      description: refus.value.motif || 'Aucun motif précisé.',
      color: 'success'
    })
    refus.value.ouvert = false
    await charger()
  } catch (e) {
    const detailErreur = e?.data?.detail
    toast.add({
      title: 'Refus impossible',
      description: typeof detailErreur === 'string' ? detailErreur : 'Une erreur est survenue.',
      color: 'danger'
    })
  } finally {
    refusEnCours.value = false
  }
}

onMounted(charger)
</script>

<template>
  <div class="space-y-6">
    <!-- En-tête -->
    <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-black text-slate-900 uppercase">
          Demandes du personnel
        </h1>
        <p class="text-sm text-slate-500 font-medium mt-1">
          Validez les congés et les acomptes de vos salariés : ce qui est validé entre dans la paie.
        </p>
      </div>
      <div class="flex items-center gap-2">
        <span
          class="px-3 py-1.5 rounded-full text-xs font-bold border"
          :class="nombreEnAttente ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-green-50 text-green-700 border-green-200'"
        >
          {{ nombreEnAttente }} en attente
        </span>
      </div>
    </div>

    <!-- Filtres -->
    <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
      <div class="flex gap-1">
        <button
          v-for="choix in [
            { cle: 'en_attente', libelle: 'À traiter' },
            { cle: 'traitees', libelle: 'Traitées' },
            { cle: 'toutes', libelle: 'Toutes' }
          ]"
          :key="choix.cle"
          class="px-3 py-1.5 text-xs font-bold uppercase tracking-wider rounded-lg transition-colors"
          :class="filtre === choix.cle ? 'bg-slate-900 text-white' : 'text-slate-500 hover:bg-slate-100'"
          @click="filtre = choix.cle"
        >
          {{ choix.libelle }}
        </button>
      </div>
      <input
        v-model="recherche"
        type="search"
        placeholder="Rechercher un salarié…"
        class="w-full sm:w-64 px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
      >
    </div>

    <!-- Liste -->
    <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
      <div
        v-if="chargement"
        class="p-8 text-center text-sm text-slate-400"
      >
        Chargement…
      </div>
      <div
        v-else-if="!demandes.length"
        class="p-10 text-center"
      >
        <UIcon
          name="i-lucide-inbox"
          class="w-10 h-10 text-slate-300 inline-block"
        />
        <p class="text-sm text-slate-400 mt-2">
          Aucune demande dans cette vue.
        </p>
      </div>
      <div
        v-else
        class="overflow-x-auto"
      >
        <table class="min-w-full text-sm">
          <thead class="bg-slate-50 text-slate-500 uppercase tracking-wider text-[11px]">
            <tr>
              <th class="px-5 py-3 text-left font-semibold">
                Salarié
              </th>
              <th class="px-5 py-3 text-left font-semibold">
                Type
              </th>
              <th class="px-5 py-3 text-left font-semibold">
                Détail
              </th>
              <th class="px-5 py-3 text-left font-semibold">
                Motif du salarié
              </th>
              <th class="px-5 py-3 text-left font-semibold">
                Statut
              </th>
              <th class="px-5 py-3 text-right font-semibold">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="demande in demandes"
              :key="`${demande.type}-${demande.id}`"
              class="hover:bg-slate-50"
            >
              <td class="px-5 py-3">
                <p class="font-bold text-slate-900">
                  {{ demande.salarie_prenom }} {{ demande.salarie_nom }}
                </p>
                <p class="text-[11px] text-slate-400 font-mono">
                  {{ demande.matricule }}
                </p>
              </td>
              <td class="px-5 py-3">
                <span class="inline-flex items-center gap-1 text-xs font-semibold text-slate-600">
                  <UIcon
                    :name="demande.type === 'conge' ? 'i-lucide-palmtree' : 'i-lucide-hand-coins'"
                    class="w-3.5 h-3.5"
                  />
                  {{ demande.type === 'conge' ? 'Congés' : 'Acompte' }}
                </span>
              </td>
              <td class="px-5 py-3 text-slate-700">
                {{ detail(demande) }}
              </td>
              <td
                class="px-5 py-3 text-slate-500 max-w-[16rem] truncate"
                :title="demande.motif || ''"
              >
                {{ demande.motif || '—' }}
              </td>
              <td class="px-5 py-3">
                <span
                  class="inline-flex px-2 py-0.5 border text-[11px] font-bold uppercase tracking-wide"
                  :class="classeStatut(demande.statut)"
                >
                  {{ libelleStatut(demande.statut) }}
                </span>
                <p
                  v-if="demande.commentaire_gestionnaire"
                  class="text-[11px] text-slate-400 mt-1 max-w-[14rem]"
                >
                  {{ demande.commentaire_gestionnaire }}
                </p>
              </td>
              <td class="px-5 py-3 text-right">
                <div
                  v-if="demande.statut === 'en_attente'"
                  class="flex justify-end gap-2"
                >
                  <button
                    :disabled="decisionEnCours === `${demande.type}-${demande.id}`"
                    class="px-3 py-1.5 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white text-[11px] font-bold uppercase tracking-wider rounded-lg inline-flex items-center gap-1"
                    @click="valider(demande)"
                  >
                    <UIcon
                      :name="decisionEnCours === `${demande.type}-${demande.id}` ? 'i-lucide-loader-2' : 'i-lucide-check'"
                      class="w-3.5 h-3.5"
                      :class="{ 'animate-spin': decisionEnCours === `${demande.type}-${demande.id}` }"
                    />
                    Valider
                  </button>
                  <button
                    class="px-3 py-1.5 border border-red-200 text-red-600 hover:bg-red-50 text-[11px] font-bold uppercase tracking-wider rounded-lg inline-flex items-center gap-1"
                    @click="ouvrirRefus(demande)"
                  >
                    <UIcon
                      name="i-lucide-x"
                      class="w-3.5 h-3.5"
                    />
                    Refuser
                  </button>
                </div>
                <span
                  v-else
                  class="text-[11px] text-slate-400"
                >
                  {{ demande.date_decision ? 'Traitée' : '—' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <p class="text-[11px] text-slate-400">
      Une demande validée ne peut plus changer de statut. Si le bulletin de la période est déjà
      validé, la validation est refusée : rouvrez d'abord le bulletin.
    </p>

    <!-- Refus -->
    <div
      v-if="refus.ouvert"
      class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      @click.self="refus.ouvert = false"
    >
      <div class="bg-white border border-slate-300 w-full max-w-md rounded-xl">
        <div class="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
          <h2 class="font-bold uppercase tracking-wide text-sm">
            Refuser la demande
          </h2>
          <button
            class="text-slate-500 hover:text-slate-900"
            @click="refus.ouvert = false"
          >
            <UIcon
              name="i-lucide-x"
              class="w-4 h-4"
            />
          </button>
        </div>
        <div class="p-4 space-y-3">
          <p class="text-xs text-slate-500">
            {{ refus.demande?.salarie_prenom }} {{ refus.demande?.salarie_nom }} —
            {{ refus.demande ? detail(refus.demande) : '' }}
          </p>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Motif (facultatif)</label>
            <textarea
              v-model="refus.motif"
              rows="3"
              maxlength="1000"
              placeholder="Effectif insuffisant, acompte déjà accordé…"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
            />
          </div>
          <p class="text-[11px] text-slate-400">
            Le salarié verra ce motif dans son espace. Aucune absence ni retenue ne sera créée.
          </p>
        </div>
        <div class="px-4 py-3 border-t border-slate-200 flex justify-end gap-2">
          <button
            class="px-3 py-2 border border-slate-300 rounded-lg text-sm font-semibold hover:bg-slate-50"
            @click="refus.ouvert = false"
          >
            Annuler
          </button>
          <button
            :disabled="refusEnCours"
            class="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-slate-300 text-white text-sm font-bold rounded-lg inline-flex items-center gap-1.5"
            @click="confirmerRefus"
          >
            <UIcon
              :name="refusEnCours ? 'i-lucide-loader-2' : 'i-lucide-x-circle'"
              class="w-4 h-4"
              :class="{ 'animate-spin': refusEnCours }"
            />
            Confirmer le refus
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
