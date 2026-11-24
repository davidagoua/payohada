<script setup>
/**
 * Départ d'un salarié, en deux étapes :
 *  1. la déclaration du départ (motif codifié, dates, préavis…), enregistrée
 *     par `POST`/`PUT /contrats/{id}/depart` ;
 *  2. le solde de tout compte, calculé une fois le départ déclaré.
 *
 * Les simulations libres se font dans la boîte à outils de l'établissement.
 *
 * L'aperçu est calculé par les simulateurs (`/calculs/...`, sans écriture) :
 * barème 30/35/40 % du décret n° 2017-210, frais funéraires, indemnité de
 * fin de CDD, gratification annuelle et congés payés. L'enregistrement passe
 * par `/solde-tout-compte/complet`, qui fige le détail du calcul.
 */
import { MOTIFS_SORTIE, TYPES_PREAVIS, libelleMotifSortie, motifCalcul } from '~/utils/departSalarie'

definePageMeta({ layout: 'default' })

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { get, post, put, delete: apiDelete } = useApi()

const dossierId = route.params.dossierId
const etabId = route.params.etabId
const salarieId = route.params.salarieId
const contratId = route.params.contratId

const contrat = ref(null)
const salarie = ref(null)
const departExistant = ref(null)
const stcExistant = ref(null)

const MOTIFS = [
  { valeur: 'licenciement', libelle: 'Licenciement', icone: 'i-lucide-user-minus' },
  { valeur: 'retraite', libelle: 'Départ à la retraite', icone: 'i-lucide-armchair' },
  { valeur: 'deces', libelle: 'Décès', icone: 'i-lucide-heart-crack' },
  { valeur: 'fin_cdd', libelle: 'Fin de CDD', icone: 'i-lucide-file-x' },
  { valeur: 'demission', libelle: 'Démission', icone: 'i-lucide-log-out' },
  { valeur: 'rupture', libelle: 'Rupture conventionnelle', icone: 'i-lucide-handshake' }
]

const SOUS_MOTIFS_CDD = [
  { valeur: 'terme_normal_sans_cdi', libelle: 'Terme normal, sans conclusion d\'un CDI', due: true },
  { valeur: 'refus_cdi_equivalent', libelle: 'Refus d\'un CDI équivalent', due: false },
  { valeur: 'rupture_initiative_salarie', libelle: 'Rupture à l\'initiative du salarié', due: false },
  { valeur: 'faute_lourde', libelle: 'Faute lourde', due: false },
  { valeur: 'cdi_conclu', libelle: 'Un CDI a été conclu à l\'issue', due: false },
  { valeur: 'autre', libelle: 'Autre situation — à vérifier', due: false }
]

const MOIS_LABELS = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
]

// ── Saisie ────────────────────────────────────────────────────────────
const form = ref({
  motif_fin_contrat: 'licenciement',
  sous_motif_fin_cdd: 'terme_normal_sans_cdi',
  date_sortie: '',
  anciennete_mois: null,
  smhc_mensuel: null,
  faute_lourde: false,
  conditions_retraite_remplies: false,
  saisie_salaires: false,
  salaires_12_mois: Array.from({ length: 12 }, () => null),
  gratification_annee: new Date().getFullYear(),
  gratification_active: true,
  gratification_jours_service: null,
  gratification_taux_entreprise: 0,
  conges_mois_service: null,
  conges_jours_pris: 0,
  conges_jours_supplementaires: 0,
  conges_methode: 'conventionnelle',
  conges_montant_manuel: null,
  indemnite_preavis: 0,
  indemnite_autre: 0
})

// ── Étape 1 : déclaration du départ ──────────────────────────────────
const declarationVide = () => ({
  date_sortie: '',
  motif_sortie: null,
  date_notification_rupture: '',
  date_notification_signature: '',
  date_engagement_procedure: '',
  preavis: [1, 2, 3].map(() => ({ type: null, du: '', au: '' })),
  maintien_affiliation: false,
  transaction_en_cours: false,
  dernier_jour_travaille: ''
})
const declaration = ref(declarationVide())
const enregistrementDepart = ref(false)

const optionsMotifs = MOTIFS_SORTIE.map(m => ({ label: libelleMotifSortie(m), value: m.code }))
const optionsPreavis = [
  { label: '-', value: null },
  ...TYPES_PREAVIS.map(t => ({ label: t.libelle, value: t.code }))
]

const remplirDeclaration = (depart) => {
  const v = declarationVide()
  if (!depart) {
    declaration.value = v
    return
  }
  const date = (x) => (x || '').slice(0, 10)
  declaration.value = {
    date_sortie: date(depart.date_sortie),
    motif_sortie: depart.motif_sortie ?? null,
    date_notification_rupture: date(depart.date_notification_rupture),
    date_notification_signature: date(depart.date_notification_signature),
    date_engagement_procedure: date(depart.date_engagement_procedure),
    preavis: ['01', '02', '03'].map(n => ({
      type: depart[`type_paiement_preavis${n}`] ?? null,
      du: date(depart[`preavis_de${n}`]),
      au: date(depart[`preavis_au${n}`])
    })),
    maintien_affiliation: !!depart.maintien_affiliation,
    transaction_en_cours: !!depart.transaction_en_cours,
    dernier_jour_travaille: date(depart.dernier_jour_travaille)
  }
}

const enregistrerDepart = async () => {
  const d = declaration.value
  if (!d.date_sortie || !d.motif_sortie) {
    toast.add({ title: 'Champs requis', description: 'La date et le motif de sortie sont obligatoires.', color: 'warning' })
    return
  }
  const vide = (x) => x || null
  const payload = {
    date_sortie: d.date_sortie,
    motif_sortie: d.motif_sortie,
    date_notification_rupture: vide(d.date_notification_rupture),
    date_notification_signature: vide(d.date_notification_signature),
    date_engagement_procedure: vide(d.date_engagement_procedure),
    maintien_affiliation: d.maintien_affiliation,
    transaction_en_cours: d.transaction_en_cours,
    dernier_jour_travaille: vide(d.dernier_jour_travaille)
  }
  d.preavis.forEach((p, i) => {
    const n = `0${i + 1}`
    payload[`type_paiement_preavis${n}`] = p.type
    payload[`preavis_de${n}`] = vide(p.du)
    payload[`preavis_au${n}`] = vide(p.au)
  })
  enregistrementDepart.value = true
  try {
    if (departExistant.value) {
      await put(`${urlBase.value}/depart`, payload)
    } else {
      await post(`${urlBase.value}/depart`, payload)
    }
    toast.add({ title: 'Départ enregistré', description: 'Vous pouvez établir le solde de tout compte.', color: 'success' })
    await charger()
    await simuler()
  } catch (e) {
    console.error('Enregistrement du départ impossible :', e)
  } finally {
    enregistrementDepart.value = false
  }
}

// Le motif de sortie choisi pilote le motif des calculs du solde, s'il le précise.
watch(() => declaration.value.motif_sortie, (code) => {
  const calcul = motifCalcul(code)
  if (calcul) form.value.motif_fin_contrat = calcul
  if (code === 25) form.value.faute_lourde = true
})

const apercuRupture = ref(null)
const apercuDeces = ref(null)
const apercuFinCdd = ref(null)
const apercuGratification = ref(null)
const apercuConges = ref(null)
const calculEnCours = ref(false)
const enregistrement = ref(false)

const anneeCourante = new Date().getFullYear()
const anneesDisponibles = Array.from({ length: 6 }, (_, i) => anneeCourante - i)

// Un champ numérique vidé par l'utilisateur vaut `''` avec `v-model.number` :
// on le ramène à `null` pour ne pas envoyer une chaîne vide à l'API.
const nombre = (v) => (v === '' || v === null || v === undefined ? null : Number(v))
const nombreOuZero = (v) => Number(nombre(v)) || 0

const formatFcfa = (v) => `${Math.round(Number(v) || 0).toLocaleString('fr-FR')} F`
const urlBase = computed(() => `/contrats/${contratId}`)

const besoinRemunerations = computed(() =>
  ['licenciement', 'retraite', 'deces'].includes(form.value.motif_fin_contrat)
)
const besoinSousMotifCdd = computed(() => form.value.motif_fin_contrat === 'fin_cdd')

/** Ancienneté déduite des dates du contrat. */
const ancienneteCalculee = computed(() => {
  const debut = contrat.value?.date_debut_contrat
  if (!debut || !form.value.date_sortie) return null
  const d = new Date(debut)
  const f = new Date(form.value.date_sortie)
  if (Number.isNaN(d.getTime()) || Number.isNaN(f.getTime()) || f < d) return null
  let mois = (f.getFullYear() - d.getFullYear()) * 12 + (f.getMonth() - d.getMonth())
  if (f.getDate() < d.getDate()) mois -= 1
  return Math.max(0, mois)
})

const ancienneteRetenue = computed(() =>
  form.value.anciennete_mois ?? ancienneteCalculee.value ?? 0
)

const totalSolde = computed(() => {
  let total = nombreOuZero(form.value.indemnite_preavis)
  total += nombreOuZero(form.value.indemnite_autre)
  if (apercuRupture.value && form.value.motif_fin_contrat !== 'deces') {
    total += apercuRupture.value.montant || 0
  }
  if (apercuDeces.value) total += apercuDeces.value.total || 0
  if (apercuFinCdd.value) total += apercuFinCdd.value.indemnite_due || 0
  if (apercuGratification.value) total += apercuGratification.value.gratification_retenue || 0
  if (apercuConges.value) total += apercuConges.value.montant_retenu || 0
  return total
})

// ── Chargement ────────────────────────────────────────────────────────
const charger = async () => {
  try {
    contrat.value = await get(`/contrats/${contratId}`)
    salarie.value = await get(`/salaries/${salarieId}`)
    form.value.smhc_mensuel = contrat.value?.smhc_mensuel || contrat.value?.poste_salaire?.salaire_mensuel_fcfa || null

    departExistant.value = await get(`${urlBase.value}/depart`)
    remplirDeclaration(departExistant.value)
    if (!departExistant.value) {
      // Fin de CDD : la date de fin prévue propose la date de sortie.
      const finPrevue = (contrat.value?.date_fin_previsionnelle_contrat || '').slice(0, 10)
      declaration.value.date_sortie = finPrevue
      declaration.value.dernier_jour_travaille = finPrevue
    }
    if (departExistant.value) {
      form.value.date_sortie = (departExistant.value.date_sortie || '').slice(0, 10)
      if (departExistant.value.motif_fin_contrat) {
        form.value.motif_fin_contrat = departExistant.value.motif_fin_contrat
      }
      if (departExistant.value.sous_motif_fin_cdd) {
        form.value.sous_motif_fin_cdd = departExistant.value.sous_motif_fin_cdd
      }
      form.value.conditions_retraite_remplies = !!departExistant.value.conditions_retraite_remplies
    }

    stcExistant.value = await get(`${urlBase.value}/solde-tout-compte`)
    if (stcExistant.value) {
      form.value.indemnite_preavis = stcExistant.value.indemnite_preavis || 0
      form.value.indemnite_autre = stcExistant.value.indemnite_autre || 0
    }
  } catch (e) {
    console.error('Erreur de chargement:', e)
  }
}

/** Paramètres communs aux simulateurs. */
const parametresCommuns = () => {
  const params = {
    date_sortie: form.value.date_sortie || null,
    anciennete_mois: nombre(form.value.anciennete_mois) ?? ancienneteCalculee.value ?? null
  }
  if (form.value.saisie_salaires) {
    params.salaires_12_mois = form.value.salaires_12_mois.map((v) => nombre(v))
  }
  return params
}

const simuler = async () => {
  calculEnCours.value = true
  apercuRupture.value = null
  apercuDeces.value = null
  apercuFinCdd.value = null
  apercuGratification.value = null
  apercuConges.value = null

  try {
    const motif = form.value.motif_fin_contrat

    if (motif === 'licenciement' || motif === 'retraite') {
      apercuRupture.value = await post(`${urlBase.value}/calculs/rupture`, {
        ...parametresCommuns(),
        faute_lourde: !!form.value.faute_lourde,
        depart_retraite: motif === 'retraite'
      })
    } else if (motif === 'deces') {
      apercuDeces.value = await post(`${urlBase.value}/calculs/deces`, {
        ...parametresCommuns(),
        smhc_mensuel: nombre(form.value.smhc_mensuel),
        conditions_retraite_remplies: !!form.value.conditions_retraite_remplies
      })
    } else if (motif === 'fin_cdd') {
      apercuFinCdd.value = await post(`${urlBase.value}/calculs/fin-cdd`, {
        sous_motif_fin_cdd: form.value.sous_motif_fin_cdd
      })
    }

    if (form.value.gratification_active && form.value.gratification_annee) {
      const params = {
        annee: form.value.gratification_annee,
        taux_entreprise: nombreOuZero(form.value.gratification_taux_entreprise)
      }
      const smhc = nombre(form.value.smhc_mensuel)
      if (smhc) params.smhc_mensuel = smhc
      const joursGrat = nombre(form.value.gratification_jours_service)
      if (joursGrat !== null) params.jours_service = joursGrat
      apercuGratification.value = await get(`${urlBase.value}/calculs/gratification`, { params })
    }

    const moisConges = nombre(form.value.conges_mois_service) ?? ancienneteRetenue.value
    if (moisConges > 0) {
      const paramsConges = {
        mois_service: moisConges,
        jours_pris: nombreOuZero(form.value.conges_jours_pris),
        jours_supplementaires: nombreOuZero(form.value.conges_jours_supplementaires),
        methode: form.value.conges_methode
      }
      const manuel = nombre(form.value.conges_montant_manuel)
      if (manuel !== null) paramsConges.montant_manuel = manuel
      apercuConges.value = await get(`${urlBase.value}/calculs/conges`, { params: paramsConges })
    }
  } catch (e) {
    console.error('Erreur de simulation:', e)
    toast.add({
      title: 'Calcul impossible',
      description: e?.data?.detail || 'Vérifiez les informations saisies.',
      color: 'error'
    })
  } finally {
    calculEnCours.value = false
  }
}

const enregistrer = async () => {
  if (!form.value.date_sortie) {
    toast.add({ title: 'Date manquante', description: 'La date de sortie est obligatoire.', color: 'warning' })
    return
  }
  enregistrement.value = true
  try {
    const payload = {
      motif_fin_contrat: form.value.motif_fin_contrat,
      sous_motif_fin_cdd: besoinSousMotifCdd.value ? form.value.sous_motif_fin_cdd : null,
      date_sortie: form.value.date_sortie,
      anciennete_mois: nombre(form.value.anciennete_mois) ?? ancienneteCalculee.value ?? null,
      faute_lourde: !!form.value.faute_lourde,
      conditions_retraite_remplies: !!form.value.conditions_retraite_remplies,
      smhc_mensuel: nombre(form.value.smhc_mensuel),
      indemnite_preavis: nombreOuZero(form.value.indemnite_preavis),
      indemnite_autre: nombreOuZero(form.value.indemnite_autre),
      conges_mois_service: nombre(form.value.conges_mois_service) ?? ancienneteRetenue.value,
      conges_jours_pris: nombreOuZero(form.value.conges_jours_pris),
      conges_jours_supplementaires: nombreOuZero(form.value.conges_jours_supplementaires),
      conges_methode: form.value.conges_methode
    }
    const manuel = nombre(form.value.conges_montant_manuel)
    if (manuel !== null) payload.conges_montant_manuel = manuel
    if (form.value.saisie_salaires) {
      payload.salaires_12_mois = form.value.salaires_12_mois.map((v) => nombre(v))
    }
    if (form.value.gratification_active && form.value.gratification_annee) {
      payload.gratification_annee = form.value.gratification_annee
      payload.gratification_taux_entreprise = nombreOuZero(form.value.gratification_taux_entreprise)
      const joursGrat = nombre(form.value.gratification_jours_service)
      if (joursGrat !== null) payload.gratification_jours_service = joursGrat
    }

    const resultat = await post(`${urlBase.value}/solde-tout-compte/complet`, payload)
    toast.add({
      title: 'Solde de tout compte enregistré',
      description: `Total : ${formatFcfa(resultat.total)}`,
      color: 'success'
    })
    await charger()
    await router.push(
      `/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/${contratId}/depart/print-stc`
    )
  } catch (e) {
    console.error('Erreur d\'enregistrement:', e)
    toast.add({
      title: 'Enregistrement impossible',
      description: e?.data?.detail || 'Une erreur est survenue.',
      color: 'error'
    })
  } finally {
    enregistrement.value = false
  }
}

const annulerDepart = async () => {
  if (!confirm('Annuler le départ ? Le contrat sera réactivé et le solde de tout compte supprimé.')) return
  try {
    await apiDelete(`${urlBase.value}/depart`)
    toast.add({ title: 'Départ annulé', color: 'success' })
    await charger()
  } catch (e) {
    console.error(e)
  }
}

const imprimer = (document) => {
  router.push(
    `/dossiers/${dossierId}/etablissements/${etabId}/salaries/${salarieId}/contrats/${contratId}/depart/print-${document}`
  )
}

onMounted(async () => {
  await charger()
  if (departExistant.value) await simuler()
})
</script>

<template>
  <div class="p-4 sm:p-6 max-w-7xl mx-auto space-y-6">
    <!-- En-tête -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
      <div>
        <button class="text-xs font-semibold text-slate-500 hover:text-navy-700 inline-flex items-center gap-1.5 mb-1" @click="router.back()">
          <Icon name="i-lucide-arrow-left" class="w-3.5 h-3.5" />
          Retour au contrat
        </button>
        <h1 class="text-lg font-bold text-navy-900">
          Départ salarié<template v-if="salarie"> — {{ salarie.matricule }} — {{ salarie.nom?.toUpperCase() }} {{ salarie.prenom }}</template>
        </h1>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button class="px-3 py-2 border border-slate-300 text-slate-700 text-xs font-bold rounded-lg inline-flex items-center gap-1.5 hover:bg-slate-50" @click="imprimer('stc')">
          <Icon name="i-lucide-receipt" class="w-4 h-4" /> Reçu STC
        </button>
        <button class="px-3 py-2 border border-slate-300 text-slate-700 text-xs font-bold rounded-lg inline-flex items-center gap-1.5 hover:bg-slate-50" @click="imprimer('certificat')">
          <Icon name="i-lucide-file-badge" class="w-4 h-4" /> Certificat
        </button>
        <button class="px-3 py-2 border border-slate-300 text-slate-700 text-xs font-bold rounded-lg inline-flex items-center gap-1.5 hover:bg-slate-50" @click="imprimer('attestation')">
          <Icon name="i-lucide-file-text" class="w-4 h-4" /> Attestation
        </button>
        <button v-if="departExistant" class="px-3 py-2 border border-red-200 text-red-600 text-xs font-bold rounded-lg hover:bg-red-50" @click="annulerDepart">
          Annuler le départ
        </button>
      </div>
    </div>

    <!-- ═══ Étape 1 : déclaration du départ ═══ -->
    <form class="bg-white border border-slate-200 rounded-xl p-5 sm:p-6" @submit.prevent="enregistrerDepart">
      <div class="flex items-center justify-between gap-3 border-b border-slate-200 pb-3 mb-5">
        <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider">1. Déclaration du départ</h2>
        <span v-if="departExistant" class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-green-50 text-green-700 border border-green-200 rounded">Enregistré</span>
      </div>

      <div class="space-y-3 depart-lignes">
        <div class="depart-ligne">
          <label for="dep-date-sortie">Date de sortie *</label>
          <InputText id="dep-date-sortie" v-model="declaration.date_sortie" type="date" required class="w-full text-sm" />
        </div>
        <div class="depart-ligne">
          <label for="dep-motif">Motif de sortie *</label>
          <Select v-model="declaration.motif_sortie" input-id="dep-motif" :options="optionsMotifs" option-label="label" option-value="value" placeholder="Choisir un motif" filter class="w-full text-sm" />
        </div>
        <div class="depart-ligne">
          <label for="dep-notif-rupture">Date de notification de la rupture de contrat</label>
          <InputText id="dep-notif-rupture" v-model="declaration.date_notification_rupture" type="date" class="w-full text-sm" />
        </div>
        <div class="depart-ligne">
          <label for="dep-notif-convention">Date de notification de signature de la convention de rupture</label>
          <InputText id="dep-notif-convention" v-model="declaration.date_notification_signature" type="date" class="w-full text-sm" />
        </div>
        <div class="depart-ligne">
          <label for="dep-engagement">Date d'engagement de la procédure de licenciement</label>
          <InputText id="dep-engagement" v-model="declaration.date_engagement_procedure" type="date" class="w-full text-sm" />
        </div>
        <div v-for="(preavis, i) in declaration.preavis" :key="i" class="depart-ligne">
          <label :for="`dep-preavis-${i}`">Préavis {{ i + 1 }}</label>
          <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,2fr)_auto_minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 sm:gap-3">
            <Select v-model="preavis.type" :input-id="`dep-preavis-${i}`" :options="optionsPreavis" option-label="label" option-value="value" placeholder="-" class="w-full text-sm" />
            <label :for="`dep-preavis-du-${i}`" class="sm:text-right">Du</label>
            <InputText :id="`dep-preavis-du-${i}`" v-model="preavis.du" type="date" :disabled="!preavis.type" class="w-full text-sm" />
            <label :for="`dep-preavis-au-${i}`" class="sm:text-right">Au</label>
            <InputText :id="`dep-preavis-au-${i}`" v-model="preavis.au" type="date" :disabled="!preavis.type" class="w-full text-sm" />
          </div>
        </div>
        <div class="depart-ligne">
          <label for="dep-affiliation">Maintien de l'affiliation du salarié au contrat collectif</label>
          <Checkbox v-model="declaration.maintien_affiliation" input-id="dep-affiliation" binary />
        </div>
        <div class="depart-ligne">
          <label for="dep-transaction">Transaction en cours</label>
          <Checkbox v-model="declaration.transaction_en_cours" input-id="dep-transaction" binary />
        </div>
        <div class="depart-ligne">
          <label for="dep-dernier-jour">Dernier jour travaillé et payé au salaire habituel</label>
          <InputText id="dep-dernier-jour" v-model="declaration.dernier_jour_travaille" type="date" class="w-full text-sm" />
        </div>
      </div>

      <div class="flex justify-end gap-2 border-t border-slate-200 pt-4 mt-5">
        <button type="submit" :disabled="enregistrementDepart" class="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white text-sm font-bold rounded-lg inline-flex items-center gap-2">
          <Icon :name="enregistrementDepart ? 'i-lucide-loader-2' : 'i-lucide-save'" class="w-4 h-4" :class="{ 'animate-spin': enregistrementDepart }" />
          {{ departExistant ? 'Mettre à jour le départ' : 'Enregistrer le départ' }}
        </button>
      </div>
    </form>

    <!-- ═══ Étape 2 : solde de tout compte ═══ -->
    <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider pt-2">2. Solde de tout compte</h2>
    <div v-if="!departExistant" class="p-4 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 flex items-start gap-2">
      <Icon name="i-lucide-lock" class="w-4 h-4 shrink-0 mt-0.5 text-slate-400" />
      <span>Enregistrez d'abord le départ : le solde de tout compte se calcule à partir de sa date et de son motif.</span>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Colonne saisie -->
      <div class="lg:col-span-2 space-y-5">
        <!-- Motif -->
        <section class="bg-white border border-slate-200 rounded-xl p-5">
          <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider mb-1">Motif retenu pour le calcul</h2>
          <p class="text-[11px] text-slate-500 mb-4">Déduit du motif de sortie ; à préciser pour une fin de période d'essai ou un autre motif.</p>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
            <button
              v-for="motif in MOTIFS"
              :key="motif.valeur"
              :class="[
                'px-3 py-3 border-2 rounded-xl text-left transition-colors',
                form.motif_fin_contrat === motif.valeur
                  ? 'border-green-500 bg-green-50'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
              ]"
              @click="form.motif_fin_contrat = motif.valeur"
            >
              <Icon :name="motif.icone" class="w-4 h-4 mb-1" :class="form.motif_fin_contrat === motif.valeur ? 'text-green-700' : 'text-slate-400'" />
              <div class="text-xs font-bold" :class="form.motif_fin_contrat === motif.valeur ? 'text-green-900' : 'text-slate-700'">
                {{ motif.libelle }}
              </div>
            </button>
          </div>

          <div v-if="besoinSousMotifCdd" class="mt-4">
            <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">
              Situation de fin de CDD (art. 15.8)
            </label>
            <Select
              v-model="form.sous_motif_fin_cdd"
              class="w-full text-sm"
              :options="[
                ...SOUS_MOTIFS_CDD.map(sous => ({ label: `${sous.libelle}${sous.due ? ' — indemnité due' : ' — indemnité non due'}`, value: sous.valeur }))
              ]"
              option-label="label"
              option-value="value"
            />
          </div>

          <div class="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">
                Ancienneté (mois)
              </label>
              <InputText v-model.number="form.anciennete_mois" type="number" min="0" :placeholder="String(ancienneteCalculee ?? '')" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
              <p class="text-[10px] text-slate-400 mt-1">
                <span v-if="ancienneteCalculee !== null">Calculée : {{ ancienneteCalculee }} mois — </span>
                laisser vide pour l'utiliser
              </p>
            </div>
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">
                SMHC mensuel (F)
              </label>
              <InputText v-model.number="form.smhc_mensuel" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
              <p class="text-[10px] text-slate-400 mt-1">Base de la gratification et des frais funéraires</p>
            </div>
          </div>

          <div class="mt-4 flex flex-wrap gap-4">
            <label v-if="form.motif_fin_contrat === 'licenciement'" class="flex items-center gap-2 cursor-pointer">
              <Checkbox v-model="form.faute_lourde" binary />
              <span class="text-xs font-semibold text-slate-700">Faute lourde retenue (supprime l'indemnité)</span>
            </label>
            <label v-if="form.motif_fin_contrat === 'deces'" class="flex items-center gap-2 cursor-pointer">
              <Checkbox v-model="form.conditions_retraite_remplies" binary />
              <span class="text-xs font-semibold text-slate-700">Conditions de départ à la retraite remplies</span>
            </label>
          </div>
        </section>

        <!-- Rémunérations de référence -->
        <section v-if="besoinRemunerations" class="bg-white border border-slate-200 rounded-xl p-5">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider">Rémunérations de référence</h2>
            <label class="flex items-center gap-2 cursor-pointer">
              <Checkbox v-model="form.saisie_salaires" binary />
              <span class="text-[11px] font-semibold text-slate-600">Saisir manuellement</span>
            </label>
          </div>
          <p v-if="!form.saisie_salaires" class="text-xs text-slate-500">
            Les <strong>12 derniers bulletins</strong> du contrat servent de base au salaire global mensuel moyen
            (décret n° 2017-210, art. 4). Cochez « Saisir manuellement » pour écarter un mois atypique
            ou renseigner un historique absent.
          </p>
          <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            <div v-for="(_, index) in form.salaires_12_mois" :key="index">
              <label class="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-0.5">
                M-{{ 12 - index }}
              </label>
              <InputText v-model.number="form.salaires_12_mois[index]" type="number" min="0" placeholder="—" class="w-full px-2 py-1.5 border border-slate-300 rounded-lg text-xs" />
            </div>
          </div>
        </section>

        <!-- Gratification -->
        <section class="bg-white border border-slate-200 rounded-xl p-5">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider">Gratification annuelle</h2>
            <label class="flex items-center gap-2 cursor-pointer">
              <Checkbox v-model="form.gratification_active" binary />
              <span class="text-[11px] font-semibold text-slate-600">Inclure</span>
            </label>
          </div>
          <div v-if="form.gratification_active" class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Année</label>
              <Select
                v-model.number="form.gratification_annee"
                class="w-full text-sm"
                :options="[
                  ...anneesDisponibles.map(a => ({ label: `${a}`, value: a }))
                ]"
                option-label="label"
                option-value="value"
              />
            </div>
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Jours de service</label>
              <InputText v-model.number="form.gratification_jours_service" type="number" min="0" max="360" placeholder="auto (360 j)" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
              <p class="text-[10px] text-slate-400 mt-1">Base 360 jours, calculée depuis les dates si vide</p>
            </div>
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Taux entreprise</label>
              <InputText v-model.number="form.gratification_taux_entreprise" type="number" min="0" max="5" step="0.05" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
              <p class="text-[10px] text-slate-400 mt-1">0 = minimum conventionnel de 75 %</p>
            </div>
          </div>
          <p v-else class="text-xs text-slate-500">Gratification non incluse dans ce solde.</p>
        </section>

        <!-- Congés payés -->
        <section class="bg-white border border-slate-200 rounded-xl p-5">
          <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider mb-4">Congés payés</h2>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Mois de service</label>
              <InputText v-model.number="form.conges_mois_service" type="number" min="0" :placeholder="String(ancienneteRetenue)" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Jours déjà pris</label>
              <InputText v-model.number="form.conges_jours_pris" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Jours supplémentaires</label>
              <InputText v-model.number="form.conges_jours_supplementaires" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
              <p class="text-[10px] text-slate-400 mt-1">Ancienneté, charges de famille…</p>
            </div>
            <div class="sm:col-span-2">
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Méthode de valorisation</label>
              <Select
                v-model="form.conges_methode"
                class="w-full text-sm"
                :options="[
                  { label: `Conventionnelle — art. 71-72 (journalier × jours calendaires)`, value: 'conventionnelle' },
                  { label: `Décret n° 98-39 — allocation principale 1/12`, value: 'decret' }
                ]"
                option-label="label"
                option-value="value"
              />
            </div>
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Montant manuel</label>
              <InputText v-model.number="form.conges_montant_manuel" type="number" min="0" placeholder="—" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
        </section>

        <!-- Éléments complémentaires -->
        <section class="bg-white border border-slate-200 rounded-xl p-5">
          <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider mb-4">Éléments complémentaires</h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Indemnité compensatrice de préavis</label>
              <InputText v-model.number="form.indemnite_preavis" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1">Autres indemnités</label>
              <InputText v-model.number="form.indemnite_autre" type="number" min="0" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
        </section>
      </div>

      <!-- Colonne résultat -->
      <div class="lg:col-span-1">
        <div class="lg:sticky lg:top-4 space-y-4">
          <div class="bg-white border-2 border-navy-900 rounded-xl overflow-hidden">
            <div class="bg-navy-900 px-4 py-3 flex items-center justify-between">
              <h2 class="text-xs font-bold text-white uppercase tracking-wider">Solde estimé</h2>
              <button :disabled="calculEnCours" class="text-[10px] font-bold text-slate-200 hover:text-white inline-flex items-center gap-1" @click="simuler">
                <Icon :name="calculEnCours ? 'i-lucide-loader-2' : 'i-lucide-refresh-cw'" class="w-3.5 h-3.5" :class="{ 'animate-spin': calculEnCours }" />
                Recalculer
              </button>
            </div>

            <div class="p-4 space-y-2 text-xs">
              <!-- Rupture -->
              <template v-if="apercuRupture">
                <div class="flex justify-between">
                  <span class="text-slate-600">Indemnité de {{ form.motif_fin_contrat === 'retraite' ? 'retraite' : 'licenciement' }}</span>
                  <span class="font-mono">{{ formatFcfa(apercuRupture.montant) }}</span>
                </div>
                <p v-if="!apercuRupture.eligible" class="text-[11px] px-2.5 py-2 bg-amber-50 border border-amber-200 rounded-lg text-amber-800">
                  {{ apercuRupture.motif_ineligibilite }}
                </p>
              </template>

              <!-- Décès -->
              <template v-if="apercuDeces">
                <div class="flex justify-between">
                  <span class="text-slate-600">Indemnité de décès</span>
                  <span class="font-mono">{{ formatFcfa(apercuDeces.indemnite_rupture) }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-slate-600">Frais funéraires ({{ apercuDeces.multiplicateur_frais_funeraires }} × SMHC)</span>
                  <span class="font-mono">{{ formatFcfa(apercuDeces.frais_funeraires) }}</span>
                </div>
                <p v-if="!apercuDeces.eligible" class="text-[11px] px-2.5 py-2 bg-amber-50 border border-amber-200 rounded-lg text-amber-800">
                  {{ apercuDeces.motif_eligibilite }} — frais funéraires dus.
                </p>
              </template>

              <!-- Fin de CDD -->
              <template v-if="apercuFinCdd">
                <div class="flex justify-between">
                  <span class="text-slate-600">Indemnité de fin de CDD (3 %)</span>
                  <span class="font-mono">{{ formatFcfa(apercuFinCdd.indemnite_due) }}</span>
                </div>
                <p class="text-[10px] text-slate-500">{{ apercuFinCdd.motif }} — base {{ formatFcfa(apercuFinCdd.total_brut_cdd) }}</p>
              </template>

              <!-- Gratification -->
              <div v-if="apercuGratification" class="flex justify-between">
                <span class="text-slate-600">
                  Gratification {{ apercuGratification.jours_service }}/360
                </span>
                <span class="font-mono">{{ formatFcfa(apercuGratification.gratification_retenue) }}</span>
              </div>

              <!-- Congés payés -->
              <template v-if="apercuConges">
                <div class="flex justify-between">
                  <span class="text-slate-600">
                    Congés payés ({{ apercuConges.solde_jours_ouvrables }} j ouvrables)
                  </span>
                  <span class="font-mono">{{ formatFcfa(apercuConges.montant_retenu) }}</span>
                </div>
                <p class="text-[10px] text-slate-500">
                  Conventionnelle {{ formatFcfa(apercuConges.montant_conventionnel) }} ·
                  décret {{ formatFcfa(apercuConges.montant_decret) }} — {{ apercuConges.comparaison }}
                </p>
              </template>

              <div v-if="nombreOuZero(form.indemnite_preavis)" class="flex justify-between">
                <span class="text-slate-600">Préavis</span>
                <span class="font-mono">{{ formatFcfa(form.indemnite_preavis) }}</span>
              </div>
              <div v-if="nombreOuZero(form.indemnite_autre)" class="flex justify-between">
                <span class="text-slate-600">Autres indemnités</span>
                <span class="font-mono">{{ formatFcfa(form.indemnite_autre) }}</span>
              </div>

              <div class="flex justify-between font-bold text-green-800 bg-green-50 -mx-4 px-4 py-3 mt-2 text-sm">
                <span>TOTAL</span>
                <span class="font-mono">{{ formatFcfa(totalSolde) }}</span>
              </div>

              <div v-if="apercuRupture?.tranches?.length" class="pt-2">
                <p class="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">Détail du barème</p>
                <table class="w-full text-[10px]">
                  <tbody>
                    <tr v-for="tranche in apercuRupture.tranches" :key="tranche.libelle" class="border-b border-slate-100">
                      <td class="py-1 text-slate-600">{{ tranche.libelle }}</td>
                      <td class="py-1 text-right text-slate-500">{{ tranche.mois_retenus }} mois</td>
                      <td class="py-1 text-right text-slate-500">{{ Math.round(tranche.taux * 100) }} %</td>
                      <td class="py-1 text-right font-mono">{{ formatFcfa(tranche.montant) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div v-if="apercuGratification?.alertes?.length || apercuConges?.alertes?.length" class="space-y-1.5 pt-2">
                <p v-for="(alerte, i) in [...(apercuGratification?.alertes || []), ...(apercuConges?.alertes || [])]" :key="i"
                   class="text-[11px] px-2.5 py-2 bg-amber-50 border border-amber-200 rounded-lg text-amber-800">
                  {{ alerte }}
                </p>
              </div>
            </div>
          </div>

          <button
            :disabled="enregistrement || !form.date_sortie"
            class="w-full px-4 py-3 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white text-sm font-bold rounded-xl inline-flex items-center justify-center gap-2"
            @click="enregistrer"
          >
            <Icon :name="enregistrement ? 'i-lucide-loader-2' : 'i-lucide-save'" class="w-4 h-4" :class="{ 'animate-spin': enregistrement }" />
            {{ enregistrement ? 'Enregistrement…' : 'Calculer et enregistrer le STC' }}
          </button>
          <p class="text-[10px] text-slate-400 text-center">
            Le contrat passera au statut « terminé » et le détail du calcul sera conservé.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Formulaire de départ : libellé à gauche, champ à droite (pleine largeur sur mobile). */
.depart-ligne {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.25rem;
  align-items: center;
}
@media (min-width: 640px) {
  .depart-ligne {
    grid-template-columns: 17rem minmax(0, 1fr);
    gap: 1.5rem;
  }
  .depart-ligne > label {
    text-align: right;
  }
}
.depart-ligne > label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #334155;
  margin: 0;
}
</style>
