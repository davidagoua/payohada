<script setup>
/**
 * Onglet « DSN » : déclarations sociales de l'établissement.
 *
 * Cotisation CNPS mensuelle : pour chaque mois, l'aperçu calcule les lignes à
 * partir des bulletins et signale les anomalies ; la génération fige la
 * déclaration ; le fichier nominatif se charge sur e-CNPS, puis le dépôt est
 * enregistré (date et référence du reçu), ce qui verrouille la déclaration.
 */
const props = defineProps({
  etabId: { type: [String, Number], required: true }
})

const { get, post, put, delete: apiDelete } = useApi()
const toast = useToast()

const MOIS = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
const anneeCourante = new Date().getFullYear()
const annees = Array.from({ length: 5 }, (_, i) => ({ label: String(anneeCourante - i), value: anneeCourante - i }))

const annee = ref(anneeCourante)
const lignesMois = ref([])
const chargement = ref(false)

const moisOuvert = ref(null)
const apercu = ref(null)
const apercuEnCours = ref(false)
const generationEnCours = ref(false)

// Paiements d'une déclaration
const MODES_PAIEMENT = [
  { label: 'Paiement en ligne e-CNPS', value: 'e_cnps' },
  { label: 'Virement', value: 'virement' },
  { label: 'Chèque', value: 'cheque' },
  { label: 'Espèces', value: 'especes' },
  { label: 'Autre', value: 'autre' }
]
const libelleMode = (mode) => MODES_PAIEMENT.find(m => m.value === mode)?.label || mode
const paiementsOuverts = ref(null)
const nouveauPaiement = ref({ date_paiement: '', montant: null, mode: 'e_cnps', reference: '' })
const enregistrementPaiement = ref(false)

const ouvrirPaiements = async (declaration) => {
  try {
    paiementsOuverts.value = await get(`/declarations-cnps/${declaration.id}`)
    nouveauPaiement.value = {
      date_paiement: new Date().toISOString().slice(0, 10),
      montant: Math.round(paiementsOuverts.value.reste_a_payer) || null,
      mode: 'e_cnps',
      reference: ''
    }
  } catch (e) {
    console.error('Chargement des paiements impossible :', e)
  }
}

const ajouterPaiement = async () => {
  const montant = Number(nouveauPaiement.value.montant)
  if (!nouveauPaiement.value.date_paiement || !(montant > 0)) {
    toast.add({ title: 'Champs requis', description: 'Renseignez la date et un montant positif.', color: 'warning' })
    return
  }
  enregistrementPaiement.value = true
  try {
    paiementsOuverts.value = await post(`/declarations-cnps/${paiementsOuverts.value.id}/paiements`, {
      ...nouveauPaiement.value,
      montant,
      reference: nouveauPaiement.value.reference || null
    })
    nouveauPaiement.value.montant = Math.round(paiementsOuverts.value.reste_a_payer) || null
    nouveauPaiement.value.reference = ''
    toast.add({ title: 'Paiement enregistré', description: formatFcfa(montant), color: 'success' })
    await charger()
  } catch (e) {
    console.error('Enregistrement du paiement impossible :', e)
  } finally {
    enregistrementPaiement.value = false
  }
}

const supprimerPaiement = async (paiement) => {
  if (!confirm(`Supprimer le paiement de ${formatFcfa(paiement.montant)} du ${dateFr(paiement.date_paiement)} ?`)) return
  try {
    paiementsOuverts.value = await apiDelete(`/paiements-cnps/${paiement.id}`)
    await charger()
  } catch (e) {
    console.error('Suppression du paiement impossible :', e)
  }
}

const depotOuvert = ref(null)
const depot = ref({ date_depot: '', reference_depot: '' })

const formatFcfa = (v) => `${Math.round(Number(v) || 0).toLocaleString('fr-FR')} F`
const dateFr = (v) => (v ? new Date(v).toLocaleDateString('fr-FR') : '—')

const charger = async () => {
  chargement.value = true
  try {
    lignesMois.value = (await get(`/etablissements/${props.etabId}/declarations-cnps`, { params: { annee: annee.value } })) || []
  } catch (e) {
    console.error('Chargement des déclarations impossible :', e)
  } finally {
    chargement.value = false
  }
}

watch(annee, () => {
  moisOuvert.value = null
  apercu.value = null
  charger()
})
onMounted(charger)

const ouvrirApercu = async (mois) => {
  moisOuvert.value = mois
  apercu.value = null
  apercuEnCours.value = true
  try {
    apercu.value = await get(`/etablissements/${props.etabId}/declarations-cnps/${annee.value}/${mois}/apercu`)
  } catch (e) {
    console.error('Aperçu impossible :', e)
  } finally {
    apercuEnCours.value = false
  }
}

const generer = async () => {
  generationEnCours.value = true
  try {
    await post(`/etablissements/${props.etabId}/declarations-cnps/${annee.value}/${moisOuvert.value}`)
    toast.add({ title: 'Déclaration générée', description: `${MOIS[moisOuvert.value - 1]} ${annee.value}`, color: 'success' })
    moisOuvert.value = null
    apercu.value = null
    await charger()
  } catch (e) {
    console.error('Génération impossible :', e)
  } finally {
    generationEnCours.value = false
  }
}

const telecharger = async (declaration) => {
  try {
    const config = useRuntimeConfig()
    const { token } = useSupabase()
    const reponse = await fetch(`${resoudreApiBase(config.public.apiBase)}/declarations-cnps/${declaration.id}/fichier`, {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    if (!reponse.ok) throw new Error(`HTTP ${reponse.status}`)
    const lien = document.createElement('a')
    lien.href = URL.createObjectURL(await reponse.blob())
    lien.download = `cotisation_nominative_CNPS_${String(declaration.mois).padStart(2, '0')}-${declaration.annee}.xlsx`
    lien.click()
    URL.revokeObjectURL(lien.href)
  } catch (e) {
    console.error('Téléchargement impossible :', e)
    toast.add({ title: 'Téléchargement impossible', description: 'Le fichier n\'a pas pu être produit.', color: 'danger' })
  }
}

const ouvrirDepot = (declaration) => {
  depotOuvert.value = declaration
  depot.value = { date_depot: new Date().toISOString().slice(0, 10), reference_depot: '' }
}

const enregistrerDepot = async () => {
  if (!depot.value.date_depot) return
  try {
    await put(`/declarations-cnps/${depotOuvert.value.id}/depot`, depot.value)
    toast.add({ title: 'Dépôt enregistré', description: 'La déclaration est verrouillée.', color: 'success' })
    depotOuvert.value = null
    await charger()
  } catch (e) {
    console.error('Enregistrement du dépôt impossible :', e)
  }
}

const annulerDepot = async (declaration) => {
  if (!confirm('Annuler le dépôt ? La déclaration redevient modifiable.')) return
  try {
    await apiDelete(`/declarations-cnps/${declaration.id}/depot`)
    await charger()
  } catch (e) {
    console.error('Annulation du dépôt impossible :', e)
  }
}

const anomaliesBloquantes = computed(() => (apercu.value?.anomalies || []).filter(a => a.niveau === 'bloquant'))
const alertes = computed(() => (apercu.value?.anomalies || []).filter(a => a.niveau !== 'bloquant'))
const declarationOuverte = computed(() => lignesMois.value.find(l => l.mois === moisOuvert.value)?.declaration || null)
const LIBELLES_COTISATIONS = {
  retraite: 'Retraite',
  prestations_familiales: 'Prestations familiales',
  accidents_travail: 'Accidents du travail',
  assurance_maternite: 'Assurance maternité'
}
</script>

<template>
  <div class="space-y-6">
    <div class="bg-white border-2 border-slate-200 p-5 shadow-flat border-t-4 border-t-navy-900 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h2 class="text-lg font-bold text-navy-900 uppercase tracking-wider">Cotisations CNPS mensuelles</h2>
        <p class="text-xs text-slate-500 mt-1">
          Préparez chaque mois le fichier de cotisation nominative à charger sur e-CNPS, puis enregistrez son dépôt.
        </p>
      </div>
      <div class="flex items-center gap-2">
        <label for="dsn-annee" class="text-xs font-semibold text-slate-500">Année</label>
        <Select v-model="annee" input-id="dsn-annee" :options="annees" option-label="label" option-value="value" class="w-28 text-sm" />
      </div>
    </div>

    <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-x-auto">
      <div v-if="chargement" class="p-10 flex justify-center">
        <Icon name="i-lucide-loader-2" class="w-6 h-6 animate-spin text-green-600" />
      </div>
      <table v-else class="min-w-full text-sm">
        <thead class="bg-slate-50 text-[11px] font-bold text-slate-600 uppercase tracking-wider text-left">
          <tr>
            <th scope="col" class="px-4 py-3">Mois</th>
            <th scope="col" class="px-4 py-3">Bulletins validés</th>
            <th scope="col" class="px-4 py-3 text-right">Effectif</th>
            <th scope="col" class="px-4 py-3 text-right">Masse salariale</th>
            <th scope="col" class="px-4 py-3 text-right">Cotisations</th>
            <th scope="col" class="px-4 py-3 text-right">Payé</th>
            <th scope="col" class="px-4 py-3">Statut</th>
            <th scope="col" class="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="ligne in lignesMois" :key="ligne.mois" :class="moisOuvert === ligne.mois ? 'bg-green-50/60' : ''">
            <td class="px-4 py-3 font-semibold text-navy-900">{{ MOIS[ligne.mois - 1] }}</td>
            <td class="px-4 py-3 text-xs" :class="ligne.bulletins && ligne.bulletins_valides < ligne.bulletins ? 'text-yellow-700' : 'text-slate-600'">
              {{ ligne.bulletins ? `${ligne.bulletins_valides} / ${ligne.bulletins}` : '—' }}
            </td>
            <td class="px-4 py-3 text-right font-mono">{{ ligne.declaration?.effectif ?? '—' }}</td>
            <td class="px-4 py-3 text-right font-mono">{{ ligne.declaration ? formatFcfa(ligne.declaration.masse_salariale) : '—' }}</td>
            <td class="px-4 py-3 text-right font-mono">{{ ligne.declaration ? formatFcfa(ligne.declaration.total_cotisations) : '—' }}</td>
            <td class="px-4 py-3 text-right">
              <template v-if="ligne.declaration">
                <span class="font-mono">{{ formatFcfa(ligne.declaration.montant_paye) }}</span>
                <span class="block text-[10px] font-bold uppercase"
                      :class="{ 'text-green-700': ligne.declaration.statut_paiement === 'paye', 'text-yellow-700': ligne.declaration.statut_paiement === 'partiel', 'text-slate-400': ligne.declaration.statut_paiement === 'non_paye' }">
                  {{ { paye: 'Soldée', partiel: `Reste ${formatFcfa(ligne.declaration.reste_a_payer)}`, non_paye: 'Non payée' }[ligne.declaration.statut_paiement] }}
                </span>
              </template>
              <span v-else class="text-slate-400">—</span>
            </td>
            <td class="px-4 py-3">
              <span v-if="!ligne.declaration" class="text-xs text-slate-400">À déclarer</span>
              <span v-else-if="ligne.declaration.statut === 'deposee'" class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-green-50 text-green-700 border border-green-200">
                Déposée le {{ dateFr(ligne.declaration.date_depot) }}<template v-if="ligne.declaration.reference_depot"> · n° {{ ligne.declaration.reference_depot }}</template>
              </span>
              <span v-else class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-navy-50 text-navy-700 border border-navy-200">Générée</span>
              <p v-if="ligne.declaration?.ecart_bulletins" class="mt-1 text-[11px] text-yellow-700">Les bulletins ont changé depuis la génération.</p>
            </td>
            <td class="px-4 py-3">
              <div class="flex justify-end flex-wrap gap-1.5">
                <button v-if="ligne.declaration?.statut !== 'deposee'" type="button" class="px-2.5 py-1 text-xs font-semibold border border-slate-300 rounded-lg hover:bg-slate-50" @click="ouvrirApercu(ligne.mois)">
                  {{ ligne.declaration ? 'Regénérer' : 'Préparer' }}
                </button>
                <button v-if="ligne.declaration" type="button" class="px-2.5 py-1 text-xs font-semibold border border-slate-300 rounded-lg hover:bg-slate-50 inline-flex items-center gap-1" @click="telecharger(ligne.declaration)">
                  <Icon name="i-lucide-download" class="w-3.5 h-3.5" /> Fichier e-CNPS
                </button>
                <button v-if="ligne.declaration?.statut === 'generee'" type="button" class="px-2.5 py-1 text-xs font-semibold bg-green-600 hover:bg-green-700 text-white rounded-lg" @click="ouvrirDepot(ligne.declaration)">
                  Marquer déposée
                </button>
                <button v-if="ligne.declaration" type="button" class="px-2.5 py-1 text-xs font-semibold border border-slate-300 rounded-lg hover:bg-slate-50 inline-flex items-center gap-1" @click="ouvrirPaiements(ligne.declaration)">
                  <Icon name="i-lucide-wallet" class="w-3.5 h-3.5" /> Paiements
                </button>
                <button v-if="ligne.declaration?.statut === 'deposee'" type="button" class="px-2.5 py-1 text-xs font-semibold text-red-700 border border-red-200 rounded-lg hover:bg-red-50" @click="annulerDepot(ligne.declaration)">
                  Annuler le dépôt
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Aperçu du mois -->
    <section v-if="moisOuvert" class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4" aria-labelledby="titre-apercu-dsn">
      <div class="flex items-center justify-between gap-3">
        <h3 id="titre-apercu-dsn" class="text-sm font-bold text-navy-900 uppercase tracking-wider">
          {{ MOIS[moisOuvert - 1] }} {{ annee }} — aperçu de la déclaration
        </h3>
        <button type="button" class="text-slate-400 hover:text-slate-600" aria-label="Fermer l'aperçu" @click="moisOuvert = null">
          <Icon name="i-lucide-x" class="w-5 h-5" />
        </button>
      </div>

      <div v-if="apercuEnCours" class="py-8 flex justify-center">
        <Icon name="i-lucide-loader-2" class="w-6 h-6 animate-spin text-green-600" />
      </div>
      <template v-else-if="apercu">
        <ul v-if="apercu.anomalies.length" class="space-y-1">
          <li v-for="(a, i) in [...anomaliesBloquantes, ...alertes]" :key="i"
              class="text-xs px-3 py-1.5 rounded border"
              :class="a.niveau === 'bloquant' ? 'bg-red-50 border-red-200 text-red-800' : 'bg-yellow-50 border-yellow-200 text-yellow-800'">
            <strong>{{ a.niveau === 'bloquant' ? 'Bloquant' : 'Alerte' }} — {{ a.salarie }} :</strong> {{ a.message }}
          </li>
        </ul>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div class="p-3 bg-slate-50 rounded-lg"><p class="text-slate-500">Effectif</p><p class="font-bold font-mono text-navy-900">{{ apercu.effectif }}</p></div>
          <div class="p-3 bg-slate-50 rounded-lg"><p class="text-slate-500">Masse salariale</p><p class="font-bold font-mono text-navy-900">{{ formatFcfa(apercu.masse_salariale) }}</p></div>
          <div v-for="(montant, cle) in apercu.totaux.cotisations || {}" :key="cle" class="p-3 bg-slate-50 rounded-lg">
            <p class="text-slate-500">{{ LIBELLES_COTISATIONS[cle] || cle }}</p>
            <p class="font-bold font-mono text-navy-900">{{ formatFcfa(montant) }}</p>
          </div>
          <div class="p-3 bg-navy-900 text-white rounded-lg"><p class="opacity-80">Total cotisations</p><p class="font-bold font-mono">{{ formatFcfa(apercu.total_cotisations) }}</p></div>
        </div>

        <div v-if="apercu.lignes.length" class="overflow-x-auto border border-slate-200 rounded-lg">
          <table class="min-w-full text-xs">
            <thead class="bg-slate-50 text-slate-600 font-bold uppercase text-[10px] tracking-wider text-left">
              <tr>
                <th scope="col" class="px-3 py-2">N° CNPS</th>
                <th scope="col" class="px-3 py-2">Nom et prénoms</th>
                <th scope="col" class="px-3 py-2">Naissance</th>
                <th scope="col" class="px-3 py-2">Embauche</th>
                <th scope="col" class="px-3 py-2">Départ</th>
                <th scope="col" class="px-3 py-2">Type</th>
                <th scope="col" class="px-3 py-2 text-right">Durée</th>
                <th scope="col" class="px-3 py-2 text-right">Salaire brut</th>
                <th scope="col" class="px-3 py-2">Branches</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="l in apercu.lignes" :key="l.ordre">
                <td class="px-3 py-2 font-mono">{{ l.numero_cnps || '—' }}</td>
                <td class="px-3 py-2">{{ l.nom }} {{ l.prenoms }}</td>
                <td class="px-3 py-2">{{ dateFr(l.date_naissance) }}</td>
                <td class="px-3 py-2">{{ dateFr(l.date_embauche) }}</td>
                <td class="px-3 py-2">{{ dateFr(l.date_depart) }}</td>
                <td class="px-3 py-2">{{ l.type_salarie }}</td>
                <td class="px-3 py-2 text-right font-mono">{{ l.duree_travaillee }}</td>
                <td class="px-3 py-2 text-right font-mono">{{ formatFcfa(l.salaire_brut) }}</td>
                <td class="px-3 py-2 font-mono">{{ l.branches }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex items-center justify-end gap-3 border-t border-slate-200 pt-4">
          <p v-if="apercu.bloquee" class="text-xs text-red-700 mr-auto">Corrigez les anomalies bloquantes (bulletins à valider, N° CNPS…) pour générer la déclaration.</p>
          <p v-else-if="declarationOuverte" class="text-xs text-slate-500 mr-auto">La déclaration existante sera remplacée par ce calcul.</p>
          <button type="button" :disabled="apercu.bloquee || generationEnCours" class="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white text-sm font-semibold rounded-lg inline-flex items-center gap-2" @click="generer">
            <Icon :name="generationEnCours ? 'i-lucide-loader-2' : 'i-lucide-file-check'" class="w-4 h-4" :class="{ 'animate-spin': generationEnCours }" />
            {{ declarationOuverte ? 'Regénérer la déclaration' : 'Générer la déclaration' }}
          </button>
        </div>
      </template>
    </section>

    <!-- Paiements d'une déclaration -->
    <div v-if="paiementsOuverts" class="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center p-4">
      <div class="bg-white rounded-xl shadow-xl border border-slate-200 max-w-2xl w-full p-6 space-y-4" role="dialog" aria-modal="true" aria-labelledby="titre-paiements-dsn">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h3 id="titre-paiements-dsn" class="text-sm font-bold text-navy-900 uppercase tracking-wider">
              Paiements — {{ MOIS[paiementsOuverts.mois - 1] }} {{ paiementsOuverts.annee }}
            </h3>
            <p class="text-xs text-slate-500 mt-1">
              Dû {{ formatFcfa(paiementsOuverts.total_cotisations) }} · payé {{ formatFcfa(paiementsOuverts.montant_paye) }} ·
              reste <strong>{{ formatFcfa(paiementsOuverts.reste_a_payer) }}</strong>
            </p>
          </div>
          <button type="button" class="text-slate-400 hover:text-slate-600" aria-label="Fermer" @click="paiementsOuverts = null">
            <Icon name="i-lucide-x" class="w-5 h-5" />
          </button>
        </div>

        <table v-if="paiementsOuverts.paiements.length" class="w-full text-xs border border-slate-200 rounded-lg">
          <thead class="bg-slate-50 text-slate-600 font-bold uppercase text-[10px] tracking-wider text-left">
            <tr>
              <th scope="col" class="px-3 py-2">Date</th>
              <th scope="col" class="px-3 py-2 text-right">Montant</th>
              <th scope="col" class="px-3 py-2">Mode</th>
              <th scope="col" class="px-3 py-2">Référence</th>
              <th scope="col" class="px-3 py-2"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="p in paiementsOuverts.paiements" :key="p.id">
              <td class="px-3 py-2">{{ dateFr(p.date_paiement) }}</td>
              <td class="px-3 py-2 text-right font-mono">{{ formatFcfa(p.montant) }}</td>
              <td class="px-3 py-2">{{ libelleMode(p.mode) }}</td>
              <td class="px-3 py-2">{{ p.reference || '—' }}</td>
              <td class="px-3 py-2 text-right">
                <button type="button" class="text-red-600 hover:text-red-800" :aria-label="`Supprimer le paiement du ${dateFr(p.date_paiement)}`" @click="supprimerPaiement(p)">
                  <Icon name="i-lucide-trash" class="w-4 h-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="text-xs text-slate-500">Aucun paiement enregistré.</p>

        <form class="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end border-t border-slate-200 pt-4" @submit.prevent="ajouterPaiement">
          <div>
            <label for="dsn-paiement-date" class="block text-xs font-semibold text-slate-500">Date</label>
            <InputText id="dsn-paiement-date" v-model="nouveauPaiement.date_paiement" type="date" required class="mt-1 w-full text-sm" />
          </div>
          <div>
            <label for="dsn-paiement-montant" class="block text-xs font-semibold text-slate-500">Montant (F CFA)</label>
            <InputText id="dsn-paiement-montant" v-model="nouveauPaiement.montant" type="number" min="1" required class="mt-1 w-full text-sm" />
          </div>
          <div>
            <label for="dsn-paiement-mode" class="block text-xs font-semibold text-slate-500">Mode</label>
            <Select v-model="nouveauPaiement.mode" input-id="dsn-paiement-mode" :options="MODES_PAIEMENT" option-label="label" option-value="value" class="mt-1 w-full text-sm" />
          </div>
          <div>
            <label for="dsn-paiement-reference" class="block text-xs font-semibold text-slate-500">Référence</label>
            <InputText id="dsn-paiement-reference" v-model="nouveauPaiement.reference" class="mt-1 w-full text-sm" />
          </div>
          <div class="sm:col-span-4 flex justify-end">
            <button type="submit" :disabled="enregistrementPaiement" class="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white rounded-lg text-sm font-semibold">
              Ajouter le paiement
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Saisie du dépôt -->
    <div v-if="depotOuvert" class="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center p-4">
      <form class="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4" role="dialog" aria-modal="true" aria-labelledby="titre-depot-dsn" @submit.prevent="enregistrerDepot">
        <h3 id="titre-depot-dsn" class="text-sm font-bold text-navy-900 uppercase tracking-wider">
          Dépôt sur e-CNPS — {{ MOIS[depotOuvert.mois - 1] }} {{ depotOuvert.annee }}
        </h3>
        <div>
          <label for="dsn-date-depot" class="block text-xs font-semibold text-slate-500">Date de dépôt</label>
          <InputText id="dsn-date-depot" v-model="depot.date_depot" type="date" required class="mt-1 w-full text-sm" />
        </div>
        <div>
          <label for="dsn-reference" class="block text-xs font-semibold text-slate-500">N° de dossier du reçu (facultatif)</label>
          <InputText id="dsn-reference" v-model="depot.reference_depot" placeholder="ex. 6025432" class="mt-1 w-full text-sm" />
        </div>
        <p class="text-xs text-slate-500">Une fois déposée, la déclaration est verrouillée : il faut annuler le dépôt pour la modifier.</p>
        <div class="flex justify-end gap-2">
          <button type="button" class="px-4 py-2 border border-slate-200 rounded-lg text-sm font-semibold text-slate-700 hover:bg-slate-50" @click="depotOuvert = null">Annuler</button>
          <button type="submit" class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-semibold">Enregistrer le dépôt</button>
        </div>
      </form>
    </div>
  </div>
</template>
