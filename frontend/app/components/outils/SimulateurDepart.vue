<script setup>
/**
 * Simulateur de départ (boîte à outils de l'établissement).
 *
 * Estime les indemnités de sortie à partir de valeurs saisies, sans passer par
 * le processus de départ : rien n'est enregistré (`POST /simulations/depart`).
 * Un contrat de l'établissement peut servir à pré-remplir la saisie.
 */
const props = defineProps({
  contracts: { type: Array, default: () => [] },
  salaries: { type: Array, default: () => [] }
})

const { post } = useApi()

const MOTIFS = [
  { valeur: 'licenciement', libelle: 'Licenciement' },
  { valeur: 'retraite', libelle: 'Départ à la retraite' },
  { valeur: 'deces', libelle: 'Décès' },
  { valeur: 'fin_cdd', libelle: 'Fin de CDD' },
  { valeur: 'demission', libelle: 'Démission' },
  { valeur: 'rupture', libelle: 'Rupture conventionnelle' }
]

const SOUS_MOTIFS_CDD = [
  { valeur: 'terme_normal_sans_cdi', libelle: 'Terme normal, sans conclusion d\'un CDI' },
  { valeur: 'refus_cdi_equivalent', libelle: 'Refus d\'un CDI équivalent' },
  { valeur: 'rupture_initiative_salarie', libelle: 'Rupture à l\'initiative du salarié' },
  { valeur: 'faute_lourde', libelle: 'Faute lourde' },
  { valeur: 'cdi_conclu', libelle: 'Un CDI a été conclu à l\'issue' },
  { valeur: 'autre', libelle: 'Autre situation — à vérifier' }
]

const aujourdhui = () => new Date().toISOString().slice(0, 10)

const formulaireVide = () => ({
  contrat_id: null,
  motif: 'licenciement',
  date_entree: '',
  date_sortie: aujourdhui(),
  salaire_mensuel_moyen: null,
  smhc_mensuel: null,
  faute_lourde: false,
  conditions_retraite_remplies: false,
  sous_motif_fin_cdd: 'terme_normal_sans_cdi',
  total_brut_cdd: null,
  gratification_active: true,
  gratification_taux_entreprise: 0,
  conges_mois_service: null,
  conges_jours_pris: 0,
  indemnite_preavis: 0,
  indemnite_autre: 0
})

const form = ref(formulaireVide())
const resultat = ref(null)
const enCours = ref(false)
const erreur = ref('')

const nomSalarie = (salarieId) => {
  const s = props.salaries.find(x => x.id === salarieId)
  return s ? `${s.nom?.toUpperCase() || ''} ${s.prenom || ''}`.trim() : `Salarié ${salarieId}`
}

const optionsContrats = computed(() => [
  { label: '— Saisie libre —', value: null },
  ...props.contracts.map(c => ({
    label: `${nomSalarie(c.salarie_id)} — ${c.numero_contrat || `contrat ${c.id}`}`,
    value: c.id
  }))
])

// Un contrat sert seulement à pré-remplir : chaque valeur reste modifiable.
watch(() => form.value.contrat_id, (id) => {
  const c = props.contracts.find(x => x.id === id)
  if (!c) return
  form.value.date_entree = (c.date_debut_contrat || '').slice(0, 10)
  form.value.salaire_mensuel_moyen = c.salaire_mensuel ?? null
  form.value.smhc_mensuel = c.smhc_reference ?? null
  if ([20, 29, 30].includes(Number(c.type_contrat_travail))) form.value.motif = 'fin_cdd'
})

const nombre = (v) => (v === '' || v === null || v === undefined ? null : Number(v))
const formatFcfa = (v) => `${Math.round(Number(v) || 0).toLocaleString('fr-FR')} F`

const lignesResultat = computed(() => {
  const r = resultat.value
  if (!r) return []
  const lignes = []
  if (r.rupture) {
    lignes.push({
      libelle: r.motif === 'retraite' ? 'Indemnité de départ à la retraite' : 'Indemnité de licenciement',
      montant: r.rupture.montant,
      detail: r.rupture.eligible
        ? `Salaire global moyen ${formatFcfa(r.rupture.salaire_global_moyen)}`
        : r.rupture.motif_ineligibilite
    })
  }
  if (r.deces) {
    lignes.push({ libelle: 'Indemnité de décès', montant: r.deces.indemnite_rupture, detail: r.deces.motif_eligibilite })
    lignes.push({
      libelle: 'Frais funéraires',
      montant: r.deces.frais_funeraires,
      detail: r.deces.multiplicateur_frais_funeraires ? `${r.deces.multiplicateur_frais_funeraires} × salaire minimum` : ''
    })
  }
  if (r.fin_cdd) {
    lignes.push({ libelle: 'Indemnité de fin de CDD (3 %)', montant: r.fin_cdd.indemnite_due, detail: r.fin_cdd.motif })
  }
  if (r.gratification) {
    lignes.push({ libelle: 'Gratification (prorata)', montant: r.gratification.gratification_retenue, detail: `${r.gratification.jours_service} jours de service` })
  }
  if (r.conges) {
    lignes.push({ libelle: 'Indemnité compensatrice de congés', montant: r.conges.montant_retenu, detail: `${r.conges.solde_jours_ouvrables} jours ouvrables` })
  }
  if (r.indemnite_preavis) lignes.push({ libelle: 'Indemnité de préavis', montant: r.indemnite_preavis, detail: 'Saisie' })
  if (r.indemnite_autre) lignes.push({ libelle: 'Autres sommes', montant: r.indemnite_autre, detail: 'Saisie' })
  return lignes
})

const simuler = async () => {
  erreur.value = ''
  if (!form.value.date_entree || !form.value.date_sortie || nombre(form.value.salaire_mensuel_moyen) === null) {
    erreur.value = 'Renseignez les dates d\'entrée et de sortie et le salaire mensuel moyen.'
    return
  }
  enCours.value = true
  try {
    const { contrat_id: _contrat, ...valeurs } = form.value
    resultat.value = await post('/simulations/depart', {
      ...valeurs,
      salaire_mensuel_moyen: nombre(valeurs.salaire_mensuel_moyen),
      smhc_mensuel: nombre(valeurs.smhc_mensuel),
      total_brut_cdd: nombre(valeurs.total_brut_cdd),
      conges_mois_service: nombre(valeurs.conges_mois_service),
      conges_jours_pris: nombre(valeurs.conges_jours_pris) || 0,
      gratification_taux_entreprise: nombre(valeurs.gratification_taux_entreprise) || 0,
      indemnite_preavis: nombre(valeurs.indemnite_preavis) || 0,
      indemnite_autre: nombre(valeurs.indemnite_autre) || 0
    })
  } catch (e) {
    console.error('Simulation de départ impossible :', e)
  } finally {
    enCours.value = false
  }
}

const reinitialiser = () => {
  form.value = formulaireVide()
  resultat.value = null
  erreur.value = ''
}
</script>

<template>
  <div class="grid grid-cols-1 xl:grid-cols-5 gap-6">
    <form class="xl:col-span-3 bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5" @submit.prevent="simuler">
      <div class="flex items-start gap-3 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
        <Icon name="i-lucide-info" class="w-4 h-4 mt-0.5 shrink-0 text-slate-500" />
        <p>Simulation indicative : rien n'est enregistré. Pour déclarer un départ, passez par le contrat du salarié.</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="md:col-span-2">
          <label for="sim-contrat" class="block text-xs font-semibold text-slate-500">Pré-remplir depuis un contrat (facultatif)</label>
          <Select v-model="form.contrat_id" input-id="sim-contrat" :options="optionsContrats" option-label="label" option-value="value" placeholder="— Saisie libre —" filter class="mt-1 w-full text-sm" />
        </div>
        <div>
          <label for="sim-motif" class="block text-xs font-semibold text-slate-500">Motif de départ</label>
          <Select v-model="form.motif" input-id="sim-motif" :options="MOTIFS" option-label="libelle" option-value="valeur" class="mt-1 w-full text-sm" />
        </div>
        <div>
          <label for="sim-salaire" class="block text-xs font-semibold text-slate-500">Salaire mensuel moyen (F CFA)</label>
          <InputText id="sim-salaire" v-model="form.salaire_mensuel_moyen" type="number" min="0" class="mt-1 w-full text-sm" />
        </div>
        <div>
          <label for="sim-entree" class="block text-xs font-semibold text-slate-500">Date d'entrée</label>
          <InputText id="sim-entree" v-model="form.date_entree" type="date" class="mt-1 w-full text-sm" />
        </div>
        <div>
          <label for="sim-sortie" class="block text-xs font-semibold text-slate-500">Date de sortie</label>
          <InputText id="sim-sortie" v-model="form.date_sortie" type="date" class="mt-1 w-full text-sm" />
        </div>
        <div>
          <label for="sim-smhc" class="block text-xs font-semibold text-slate-500">Salaire minimum de la catégorie (F CFA)</label>
          <InputText id="sim-smhc" v-model="form.smhc_mensuel" type="number" min="0" class="mt-1 w-full text-sm" />
          <p class="mt-1 text-[11px] text-slate-400">Sert aux frais funéraires et à la gratification.</p>
        </div>

        <div v-if="form.motif === 'fin_cdd'">
          <label for="sim-sous-motif" class="block text-xs font-semibold text-slate-500">Situation en fin de CDD</label>
          <Select v-model="form.sous_motif_fin_cdd" input-id="sim-sous-motif" :options="SOUS_MOTIFS_CDD" option-label="libelle" option-value="valeur" class="mt-1 w-full text-sm" />
        </div>
        <div v-if="form.motif === 'fin_cdd'">
          <label for="sim-total-cdd" class="block text-xs font-semibold text-slate-500">Total brut du CDD (facultatif)</label>
          <InputText id="sim-total-cdd" v-model="form.total_brut_cdd" type="number" min="0" class="mt-1 w-full text-sm" />
        </div>
        <div v-if="form.motif === 'licenciement'" class="flex items-center gap-2 md:col-span-2">
          <Checkbox v-model="form.faute_lourde" input-id="sim-faute" binary />
          <label for="sim-faute">Faute lourde (aucune indemnité de licenciement)</label>
        </div>
        <div v-if="form.motif === 'deces'" class="flex items-center gap-2 md:col-span-2">
          <Checkbox v-model="form.conditions_retraite_remplies" input-id="sim-retraite" binary />
          <label for="sim-retraite">Conditions de départ à la retraite remplies</label>
        </div>
      </div>

      <fieldset class="grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-slate-200 pt-4">
        <legend class="text-xs font-bold text-navy-900 uppercase tracking-wider pt-4">Congés, gratification et autres sommes</legend>
        <div>
          <label for="sim-conges-mois" class="block text-xs font-semibold text-slate-500">Mois de service depuis les derniers congés</label>
          <InputText id="sim-conges-mois" v-model="form.conges_mois_service" type="number" min="0" step="0.5" placeholder="Par défaut : ancienneté, 12 au plus" class="mt-1 w-full text-sm" />
        </div>
        <div>
          <label for="sim-conges-pris" class="block text-xs font-semibold text-slate-500">Jours de congés déjà pris</label>
          <InputText id="sim-conges-pris" v-model="form.conges_jours_pris" type="number" min="0" step="0.5" class="mt-1 w-full text-sm" />
        </div>
        <div class="flex items-center gap-2">
          <Checkbox v-model="form.gratification_active" input-id="sim-gratif" binary />
          <label for="sim-gratif">Inclure la gratification au prorata</label>
        </div>
        <div>
          <label for="sim-gratif-taux" class="block text-xs font-semibold text-slate-500">Taux de gratification d'entreprise (× salaire minimum)</label>
          <InputText id="sim-gratif-taux" v-model="form.gratification_taux_entreprise" type="number" min="0" max="5" step="0.05" class="mt-1 w-full text-sm" />
        </div>
        <div>
          <label for="sim-preavis" class="block text-xs font-semibold text-slate-500">Indemnité de préavis (F CFA)</label>
          <InputText id="sim-preavis" v-model="form.indemnite_preavis" type="number" min="0" class="mt-1 w-full text-sm" />
        </div>
        <div>
          <label for="sim-autre" class="block text-xs font-semibold text-slate-500">Autres sommes dues (F CFA)</label>
          <InputText id="sim-autre" v-model="form.indemnite_autre" type="number" min="0" class="mt-1 w-full text-sm" />
        </div>
      </fieldset>

      <p v-if="erreur" class="text-xs text-red-600 font-medium">{{ erreur }}</p>

      <div class="flex justify-end gap-3 border-t border-slate-200 pt-4">
        <button type="button" class="px-4 py-2 border border-slate-200 rounded-lg text-sm font-semibold text-slate-700 hover:bg-slate-50" @click="reinitialiser">
          Réinitialiser
        </button>
        <button type="submit" :disabled="enCours" class="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white rounded-lg text-sm font-semibold flex items-center gap-2">
          <Icon :name="enCours ? 'i-lucide-loader-2' : 'i-lucide-calculator'" class="w-4 h-4" :class="{ 'animate-spin': enCours }" />
          Calculer
        </button>
      </div>
    </form>

    <section class="xl:col-span-2 bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4" aria-live="polite" aria-labelledby="titre-resultat-depart">
      <h3 id="titre-resultat-depart" class="text-sm font-bold text-navy-900 uppercase tracking-wider">Résultat de la simulation</h3>
      <p v-if="!resultat" class="text-xs text-slate-500">Renseignez la situation puis cliquez sur « Calculer ».</p>
      <template v-else>
        <p class="text-xs text-slate-500">
          Ancienneté retenue : <span class="font-semibold text-slate-800">{{ Math.floor(resultat.anciennete_mois / 12) }} an(s) et {{ resultat.anciennete_mois % 12 }} mois</span>
        </p>
        <ul class="divide-y divide-slate-100 border-y border-slate-100">
          <li v-for="ligne in lignesResultat" :key="ligne.libelle" class="py-2.5 flex justify-between gap-4">
            <span>
              <span class="block text-sm text-slate-800">{{ ligne.libelle }}</span>
              <span v-if="ligne.detail" class="block text-[11px] text-slate-500">{{ ligne.detail }}</span>
            </span>
            <span class="text-sm font-mono font-semibold text-slate-900 whitespace-nowrap">{{ formatFcfa(ligne.montant) }}</span>
          </li>
          <li v-if="!lignesResultat.length" class="py-2.5 text-xs text-slate-500">Aucune somme due pour cette situation.</li>
        </ul>
        <div class="flex justify-between items-center p-3 bg-navy-900 text-white rounded-lg">
          <span class="text-sm font-bold uppercase tracking-wider">Total estimé</span>
          <span class="text-lg font-mono font-bold">{{ formatFcfa(resultat.total) }}</span>
        </div>
        <ul v-if="resultat.alertes?.length" class="space-y-1">
          <li v-for="alerte in resultat.alertes" :key="alerte" class="text-xs text-yellow-800 bg-yellow-50 border border-yellow-200 rounded px-2 py-1">
            {{ alerte }}
          </li>
        </ul>
      </template>
    </section>
  </div>
</template>
