<script setup>
/**
 * Avantages en nature — barème fiscal DGI du 08/07/2024.
 *
 * Deux temps : la saisie est évaluée à la volée par le simulateur
 * (`/calculs/avantages-nature`, sans écriture), puis enregistrée pour le mois
 * (`/avantages-nature`) afin d'entrer dans le calcul du bulletin.
 */
definePageMeta({ layout: 'default' })

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { get, post, delete: apiDelete } = useApi()

const dossierId = route.params.dossierId
const etabId = route.params.etabId
const salarieId = route.params.salarieId
const contratId = route.params.contratId

const contrat = ref(null)
const salarie = ref(null)

const maintenant = new Date()
const mois = ref(maintenant.getMonth() + 1)
const annee = ref(String(maintenant.getFullYear()))

const MOIS_LABELS = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
]

const TYPES_VEHICULE = [
  { valeur: 'fonction_service', libelle: 'Véhicule de fonction / service', note: 'Non imposable fiscalement' },
  { valeur: 'transport_collectif_couts_reels', libelle: 'Transport collectif — coûts réels', note: 'Coût total ÷ bénéficiaires, exonéré à 30 000 F' },
  { valeur: 'transport_collectif_forfait', libelle: 'Transport collectif — forfait par salarié', note: 'Exonéré à 30 000 F' },
  { valeur: 'autre_taxable', libelle: 'Autre véhicule taxable', note: 'Évalué à la valeur réelle' }
]

const saisie = ref({
  logement_fourni: false,
  mobilier_fourni: false,
  electricite_prise_en_charge: false,
  eau_prise_en_charge: false,
  nombre_pieces: 3,
  nombre_climatiseurs: 0,
  piscine: false,
  nombre_gardiens: 0,
  nombre_employes_maison: 0,
  nombre_cuisiniers: 0,
  cout_mensuel_repas: 0,
  exoneration_repas_applicable: false,
  autres_avantages_cout_reel: 0,
  participation_salarie_hors_vehicule: 0,
  vehicule_type: null,
  vehicule_carburant: 0,
  vehicule_entretien: 0,
  vehicule_assurance: 0,
  vehicule_vignette: 0,
  vehicule_autres: 0,
  vehicule_nombre_beneficiaires: 1,
  vehicule_forfait_mensuel: 0,
  vehicule_valeur_reelle: 0,
  vehicule_participation: 0,
  vehicule_valeur_reelle_cnps: 0,
  valeur_reelle_hors_vehicule_cnps: null,
  est_persistant: false
})

const simulation = ref(null)
const periodes = ref([])
const calculEnCours = ref(false)
const enregistrement = ref(false)

// Le salaire mensuel du contrat est déjà le brut : le sursalaire y est compris.
const salaireBase = computed(() => contrat.value?.salaire_mensuel || 0)

// Un champ numérique vidé par l'utilisateur vaut `''` avec `v-model.number` :
// on le ramène à `null` pour ne pas envoyer une chaîne vide à l'API.
const nombre = (v) => (v === '' || v === null || v === undefined ? null : Number(v))
const nombreOuZero = (v) => Number(nombre(v)) || 0

const formatFcfa = (v) =>
  `${Math.round(Number(v) || 0).toLocaleString('fr-FR')} F`

const urlBase = computed(() => `/contrats/${contratId}`)

//: Champs numériques du formulaire, normalisés avant envoi.
const CHAMPS_NUMERIQUES = [
  'nombre_pieces', 'nombre_climatiseurs', 'nombre_gardiens',
  'nombre_employes_maison', 'nombre_cuisiniers', 'cout_mensuel_repas',
  'autres_avantages_cout_reel', 'participation_salarie_hors_vehicule',
  'vehicule_carburant', 'vehicule_entretien', 'vehicule_assurance',
  'vehicule_vignette', 'vehicule_autres', 'vehicule_nombre_beneficiaires',
  'vehicule_forfait_mensuel', 'vehicule_valeur_reelle',
  'vehicule_participation', 'vehicule_valeur_reelle_cnps',
  'valeur_reelle_hors_vehicule_cnps'
]

const construirePayload = () => {
  const payload = { mois: Number(mois.value), annee: String(annee.value), ...saisie.value }
  for (const cle of CHAMPS_NUMERIQUES) {
    const valeur = nombre(payload[cle])
    // `nombre_pieces` et le nombre de bénéficiaires ont des valeurs minimales.
    payload[cle] = valeur === null ? (cle === 'nombre_pieces' ? 1
      : cle === 'vehicule_nombre_beneficiaires' ? 1 : 0) : valeur
  }
  if (payload.nombre_pieces < 1) payload.nombre_pieces = 1
  if (payload.vehicule_nombre_beneficiaires < 1) payload.vehicule_nombre_beneficiaires = 1
  return payload
}

const charger = async () => {
  try {
    contrat.value = await get(`/contrats/${contratId}`)
    salarie.value = await get(`/salaries/${salarieId}`)
    await chargerPeriodes()
  } catch (e) {
    console.error('Erreur chargement:', e)
  }
}

const chargerPeriodes = async () => {
  try {
    periodes.value = (await get(`${urlBase.value}/avantages-nature`)) || []
  } catch (e) {
    console.error('Erreur chargement des périodes:', e)
    periodes.value = []
  }
}

/** Évaluation à la volée : aucune écriture en base. */
const simuler = async () => {
  calculEnCours.value = true
  try {
    simulation.value = await post(
      `${urlBase.value}/calculs/avantages-nature`, construirePayload()
    )
  } catch (e) {
    console.error('Erreur de simulation:', e)
    simulation.value = null
  } finally {
    calculEnCours.value = false
  }
}

const enregistrer = async () => {
  enregistrement.value = true
  try {
    simulation.value = await post(
      `${urlBase.value}/avantages-nature`, construirePayload()
    )
    toast.add({
      title: 'Avantages en nature enregistrés',
      description: `${MOIS_LABELS[mois.value - 1]} ${annee.value} — ${formatFcfa(simulation.value.avantage_imposable)} imposables.`,
      color: 'success'
    })
    await chargerPeriodes()
  } catch (e) {
    console.error('Erreur enregistrement:', e)
  } finally {
    enregistrement.value = false
  }
}

const chargerPeriode = (periode) => {
  mois.value = periode.mois
  annee.value = periode.annee
  // On ne réinjecte que les champs de saisie connus.
  for (const cle of Object.keys(saisie.value)) {
    if (cle in periode) saisie.value[cle] = periode[cle]
  }
  simuler()
}

const supprimerPeriode = async (periode) => {
  if (!confirm(`Supprimer les avantages en nature de ${MOIS_LABELS[periode.mois - 1]} ${periode.annee} ?`)) return
  try {
    await apiDelete(`${urlBase.value}/avantages-nature/${periode.mois}/${periode.annee}`)
    toast.add({ title: 'Période supprimée', color: 'success' })
    await chargerPeriodes()
  } catch (e) {
    console.error('Erreur suppression:', e)
  }
}

const vehiculeConcerne = computed(() => !!saisie.value.vehicule_type)
const transportCollectif = computed(() =>
  ['transport_collectif_couts_reels', 'transport_collectif_forfait'].includes(saisie.value.vehicule_type)
)

onMounted(async () => {
  await charger()
  await simuler()
})
</script>

<template>
  <div class="p-4 sm:p-6 max-w-7xl mx-auto space-y-6">
    <!-- En-tête -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
      <div>
        <button
          class="text-xs font-semibold text-slate-500 hover:text-emerald-700 inline-flex items-center gap-1.5 mb-1"
          @click="router.back()"
        >
          <UIcon name="i-lucide-arrow-left" class="w-3.5 h-3.5" />
          Retour au contrat
        </button>
        <h1 class="text-lg font-bold text-slate-900">Avantages en nature</h1>
        <p class="text-xs text-slate-500 mt-0.5">
          Barème fiscal DGI du 08/07/2024 —
          <span v-if="salarie">{{ salarie.prenom }} {{ salarie.nom }}</span>
          <span v-if="contrat"> · salaire et primes {{ formatFcfa(salaireBase) }}</span>
        </p>
      </div>
      <div class="flex items-center gap-2">
        <select v-model.number="mois" class="px-3 py-2 border border-slate-300 rounded-lg text-sm">
          <option v-for="(libelle, index) in MOIS_LABELS" :key="index" :value="index + 1">
            {{ libelle }}
          </option>
        </select>
        <input
          v-model="annee"
          type="text"
          maxlength="4"
          class="w-20 px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono"
        >
        <button
          :disabled="calculEnCours"
          class="px-3 py-2 bg-slate-800 hover:bg-slate-900 disabled:bg-slate-300 text-white text-xs font-bold rounded-lg inline-flex items-center gap-1.5"
          @click="simuler"
        >
          <UIcon :name="calculEnCours ? 'i-lucide-loader-2' : 'i-lucide-calculator'" class="w-4 h-4" :class="{ 'animate-spin': calculEnCours }" />
          Actualiser
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Saisie -->
      <div class="lg:col-span-2 space-y-5">
        <!-- Logement -->
        <section class="bg-white border border-slate-200 rounded-xl p-5">
          <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4 flex items-center gap-2">
            <UIcon name="i-lucide-house" class="w-4 h-4 text-emerald-600" />
            Logement et charges
          </h2>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <label v-for="champ in [
              { cle: 'logement_fourni', libelle: 'Logement fourni' },
              { cle: 'mobilier_fourni', libelle: 'Mobilier' },
              { cle: 'electricite_prise_en_charge', libelle: 'Électricité' },
              { cle: 'eau_prise_en_charge', libelle: 'Eau' }
            ]" :key="champ.cle"
              class="flex items-center gap-2 px-3 py-2.5 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-50"
            >
              <input v-model="saisie[champ.cle]" type="checkbox" class="accent-emerald-600">
              <span class="text-xs font-semibold text-slate-700">{{ champ.libelle }}</span>
            </label>
          </div>
          <div class="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Nombre de pièces</label>
              <input v-model.number="saisie.nombre_pieces" type="number" min="1" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
              <p class="text-[10px] text-slate-400 mt-1">7 = « 7 pièces et plus »</p>
            </div>
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Climatiseurs</label>
              <input v-model.number="saisie.nombre_climatiseurs" type="number" min="0" step="0.5" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
              <p class="text-[10px] text-slate-400 mt-1">20 000 F par unité</p>
            </div>
            <label class="flex items-end gap-2 px-3 py-2.5 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-50">
              <input v-model="saisie.piscine" type="checkbox" class="accent-emerald-600">
              <span class="text-xs font-semibold text-slate-700">Piscine (30 000 F)</span>
            </label>
          </div>
        </section>

        <!-- Domesticité -->
        <section class="bg-white border border-slate-200 rounded-xl p-5">
          <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4 flex items-center gap-2">
            <UIcon name="i-lucide-users" class="w-4 h-4 text-emerald-600" />
            Domesticité et autres avantages
          </h2>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Gardiens / jardiniers</label>
              <input v-model.number="saisie.nombre_gardiens" type="number" min="0" step="0.5" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
              <p class="text-[10px] text-slate-400 mt-1">50 000 F / personne</p>
            </div>
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Employés de maison</label>
              <input v-model.number="saisie.nombre_employes_maison" type="number" min="0" step="0.5" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
              <p class="text-[10px] text-slate-400 mt-1">60 000 F / personne</p>
            </div>
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Cuisiniers</label>
              <input v-model.number="saisie.nombre_cuisiniers" type="number" min="0" step="0.5" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
              <p class="text-[10px] text-slate-400 mt-1">90 000 F / personne</p>
            </div>
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Repas pris en charge</label>
              <input v-model.number="saisie.cout_mensuel_repas" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
            </div>
            <label class="flex items-end gap-2 px-3 py-2.5 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-50">
              <input v-model="saisie.exoneration_repas_applicable" type="checkbox" class="accent-emerald-600">
              <span class="text-xs font-semibold text-slate-700">Exonération 30 000 F</span>
            </label>
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Autres (coût réel)</label>
              <input v-model.number="saisie.autres_avantages_cout_reel" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
            </div>
          </div>
        </section>

        <!-- Véhicule -->
        <section class="bg-white border border-slate-200 rounded-xl p-5">
          <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4 flex items-center gap-2">
            <UIcon name="i-lucide-car" class="w-4 h-4 text-emerald-600" />
            Véhicule
          </h2>
          <select v-model="saisie.vehicule_type" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm mb-3">
            <option :value="null">Aucun véhicule</option>
            <option v-for="type in TYPES_VEHICULE" :key="type.valeur" :value="type.valeur">
              {{ type.libelle }} — {{ type.note }}
            </option>
          </select>

          <div v-if="vehiculeConcerne" class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <template v-if="saisie.vehicule_type === 'transport_collectif_couts_reels'">
              <div>
                <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Carburant</label>
                <input v-model.number="saisie.vehicule_carburant" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
              </div>
              <div>
                <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Entretien</label>
                <input v-model.number="saisie.vehicule_entretien" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
              </div>
              <div>
                <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Assurance</label>
                <input v-model.number="saisie.vehicule_assurance" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
              </div>
              <div>
                <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Vignette</label>
                <input v-model.number="saisie.vehicule_vignette" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
              </div>
              <div>
                <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Autres coûts</label>
                <input v-model.number="saisie.vehicule_autres" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
              </div>
              <div>
                <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Bénéficiaires</label>
                <input v-model.number="saisie.vehicule_nombre_beneficiaires" type="number" min="1" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
              </div>
            </template>
            <div v-if="saisie.vehicule_type === 'transport_collectif_forfait'">
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Forfait mensuel</label>
              <input v-model.number="saisie.vehicule_forfait_mensuel" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
            </div>
            <div v-if="saisie.vehicule_type === 'autre_taxable'">
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Valeur réelle mensuelle</label>
              <input v-model.number="saisie.vehicule_valeur_reelle" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
            </div>
            <div v-if="transportCollectif">
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Participation salarié</label>
              <input v-model.number="saisie.vehicule_participation" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
            </div>
          </div>
          <p v-else class="text-xs text-slate-500">
            Un véhicule de fonction ou de service n'est pas un avantage imposable.
          </p>
        </section>

        <!-- Participations et assiette sociale -->
        <section class="bg-white border border-slate-200 rounded-xl p-5">
          <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4 flex items-center gap-2">
            <UIcon name="i-lucide-scale" class="w-4 h-4 text-emerald-600" />
            Participations et assiette CNPS
          </h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">
                Participation du salarié (hors véhicule)
              </label>
              <input v-model.number="saisie.participation_salarie_hors_vehicule" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
            </div>
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">
                Valeur réelle hors véhicule (assiette CNPS)
              </label>
              <input v-model.number="saisie.valeur_reelle_hors_vehicule_cnps" type="number" min="0" placeholder="Vide = assiette fiscale" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm">
              <p class="text-[10px] text-slate-400 mt-1">
                Le fisc retient un forfait, la CNPS la valeur réelle : saisissez-la ici pour les distinguer.
              </p>
            </div>
          </div>
          <label class="mt-4 flex items-center gap-2 cursor-pointer">
            <input v-model="saisie.est_persistant" type="checkbox" class="accent-emerald-600">
            <span class="text-xs font-semibold text-slate-700">Avantage récurrent (reporté sur les mois suivants)</span>
          </label>
        </section>

        <!-- Périodes enregistrées -->
        <section class="bg-white border border-slate-200 rounded-xl p-5">
          <h2 class="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3 flex items-center gap-2">
            <UIcon name="i-lucide-history" class="w-4 h-4 text-emerald-600" />
            Périodes enregistrées
          </h2>
          <p v-if="!periodes.length" class="text-xs text-slate-500">
            Aucun avantage en nature enregistré pour ce contrat.
          </p>
          <table v-else class="w-full text-xs">
            <thead>
              <tr class="text-left text-slate-500 uppercase tracking-wider text-[10px] border-b border-slate-200">
                <th class="py-2">Période</th>
                <th class="py-2">Récurrent</th>
                <th class="py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="periode in periodes" :key="`${periode.annee}-${periode.mois}`" class="border-b border-slate-100">
                <td class="py-2 font-semibold text-slate-800">
                  {{ MOIS_LABELS[periode.mois - 1] }} {{ periode.annee }}
                </td>
                <td class="py-2">
                  <span v-if="periode.est_persistant" class="text-emerald-700 font-bold">Oui</span>
                  <span v-else class="text-slate-400">Non</span>
                </td>
                <td class="py-2 text-right space-x-2">
                  <button class="text-emerald-700 hover:underline font-semibold" @click="chargerPeriode(periode)">Charger</button>
                  <button class="text-red-600 hover:underline font-semibold" @click="supprimerPeriode(periode)">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>

      <!-- Résultat -->
      <div class="lg:col-span-1">
        <div class="lg:sticky lg:top-4 space-y-4">
          <div class="bg-white border-2 border-emerald-200 rounded-xl overflow-hidden">
            <div class="bg-emerald-600 px-4 py-3">
              <h2 class="text-xs font-bold text-white uppercase tracking-wider">
                Évaluation fiscale
              </h2>
            </div>
            <div v-if="simulation" class="p-4 space-y-3">
              <table class="w-full text-xs">
                <tbody>
                  <tr v-for="composante in simulation.composantes" :key="composante.code" class="border-b border-slate-100">
                    <td class="py-2">
                      <div class="font-semibold text-slate-800">{{ composante.libelle }}</div>
                      <div class="text-[10px] text-slate-400">{{ composante.base_calcul }}</div>
                    </td>
                    <td class="py-2 text-right font-mono text-slate-900 whitespace-nowrap">
                      {{ formatFcfa(composante.montant) }}
                    </td>
                  </tr>
                  <tr v-if="!simulation.composantes.length">
                    <td class="py-2 text-slate-400" colspan="2">Aucun avantage saisi.</td>
                  </tr>
                </tbody>
              </table>

              <div class="space-y-1.5 text-xs pt-2 border-t border-slate-200">
                <div class="flex justify-between">
                  <span class="text-slate-600">Total avantages</span>
                  <span class="font-mono">{{ formatFcfa(simulation.total_avant_participation) }}</span>
                </div>
                <div v-if="simulation.participation_salarie > 0" class="flex justify-between text-amber-700">
                  <span>Participation du salarié</span>
                  <span class="font-mono">−{{ formatFcfa(simulation.participation_salarie) }}</span>
                </div>
                <div class="flex justify-between font-bold text-slate-900 pt-1.5 border-t border-slate-200">
                  <span>Avantage imposable</span>
                  <span class="font-mono">{{ formatFcfa(simulation.avantage_imposable) }}</span>
                </div>
                <div class="flex justify-between text-emerald-800 font-bold bg-emerald-50 -mx-4 px-4 py-2 mt-2">
                  <span>Salaire brut imposable</span>
                  <span class="font-mono">{{ formatFcfa(simulation.salaire_brut_imposable) }}</span>
                </div>
                <div v-if="simulation.base_cnps_indicative" class="flex justify-between text-slate-600 pt-1">
                  <span>Base CNPS (valeur réelle)</span>
                  <span class="font-mono">{{ formatFcfa(simulation.base_cnps_indicative) }}</span>
                </div>
              </div>

              <div v-if="simulation.alertes?.length" class="space-y-1.5 pt-2">
                <p v-for="(alerte, i) in simulation.alertes" :key="i"
                   class="text-[11px] px-2.5 py-2 bg-amber-50 border border-amber-200 rounded-lg text-amber-800">
                  {{ alerte }}
                </p>
              </div>
            </div>
            <div v-else class="p-6 text-center text-xs text-slate-500">
              Renseignez les avantages puis actualisez l'évaluation.
            </div>
          </div>

          <button
            :disabled="enregistrement"
            class="w-full px-4 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white text-sm font-bold rounded-xl inline-flex items-center justify-center gap-2"
            @click="enregistrer"
          >
            <UIcon :name="enregistrement ? 'i-lucide-loader-2' : 'i-lucide-save'" class="w-4 h-4" :class="{ 'animate-spin': enregistrement }" />
            {{ enregistrement ? 'Enregistrement…' : `Enregistrer pour ${MOIS_LABELS[mois - 1]} ${annee}` }}
          </button>
          <p class="text-[10px] text-slate-400 text-center">
            L'avantage sera intégré au prochain calcul du bulletin : brut imposable,
            retenue compensatoire sur le net, assiette CNPS.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
