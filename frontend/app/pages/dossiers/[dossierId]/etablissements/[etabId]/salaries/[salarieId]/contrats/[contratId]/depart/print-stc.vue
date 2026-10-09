<script setup>
/**
 * Reçu pour solde de tout compte + annexe détaillant le calcul.
 *
 * L'annexe reprend le détail figé lors de l'enregistrement (`details`), ce qui
 * permet de justifier chaque montant auprès du salarié et en cas de contrôle.
 */
definePageMeta({ layout: 'blank' })

const route = useRoute()
const router = useRouter()
const { get } = useApi()

const dossierId = route.params.dossierId
const etabId = route.params.etabId
const salarieId = route.params.salarieId
const contratId = route.params.contratId

const contrat = ref(null)
const salarie = ref(null)
const etab = ref(null)
const dossier = ref(null)
const departSalarie = ref(null)
const soldeToutCompte = ref(null)
const loading = ref(true)

const MOTIFS_LIBELLES = {
  licenciement: 'Licenciement',
  retraite: 'Départ à la retraite',
  deces: 'Décès',
  fin_cdd: 'Fin de contrat à durée déterminée',
  demission: 'Démission',
  rupture: 'Rupture conventionnelle'
}

//: Motifs historiques (codes numériques encore présents sur d'anciens dossiers).
const MOTIFS_HISTORIQUES = {
  10: 'Démission', 20: 'Licenciement', 30: 'Rupture conventionnelle',
  40: 'Fin de CDD', 50: 'Retraite', 60: 'Décès', 70: 'Force majeure',
  99: 'Autre motif'
}

const fetchPrintData = async () => {
  loading.value = true
  try {
    const [c, s, e, d] = await Promise.all([
      get(`/contrats/${contratId}`),
      get(`/salaries/${salarieId}`),
      get(`/etablissements/${etabId}`),
      get(`/dossiers/${dossierId}`)
    ])
    contrat.value = c
    salarie.value = s
    etab.value = e
    dossier.value = d
    departSalarie.value = await get(`/contrats/${contratId}/depart`)
    soldeToutCompte.value = await get(`/contrats/${contratId}/solde-tout-compte`)
  } catch (err) {
    console.error('Error loading print data:', err)
  } finally {
    loading.value = false
  }
}

const details = computed(() => soldeToutCompte.value?.details || null)

const motifLabel = computed(() => {
  const motif = departSalarie.value?.motif_fin_contrat
  if (motif) return MOTIFS_LIBELLES[motif] || motif
  const code = departSalarie.value?.motif_sortie
  return MOTIFS_HISTORIQUES[code] || 'Non spécifié'
})

const dateSortie = computed(() =>
  departSalarie.value?.date_sortie
  || contrat.value?.date_fin_previsionnelle_contrat
  || 'la date prévue'
)

/**
 * Lignes du récapitulatif : seules les composantes non nulles sont imprimées,
 * afin que le reçu reste lisible.
 */
const lignesSolde = computed(() => {
  const stc = soldeToutCompte.value
  if (!stc) return []
  const candidates = [
    { cle: 'indemnite_licenciement', libelle: 'Indemnité de licenciement' },
    { cle: 'indemnite_fin_cdd', libelle: 'Indemnité de fin de contrat (3 % — art. 15.8)' },
    { cle: 'indemnite_deces', libelle: 'Indemnité de décès (droits des ayants droit)' },
    { cle: 'frais_funeraires', libelle: 'Participation aux frais funéraires' },
    { cle: 'gratification', libelle: 'Gratification annuelle (prime de fin d\'année)' },
    { cle: 'indemnite_conges_payes', libelle: 'Indemnité compensatrice de congés payés' },
    { cle: 'indemnite_preavis', libelle: 'Indemnité compensatrice de préavis' },
    { cle: 'indemnite_autre', libelle: 'Autres indemnités' }
  ]
  return candidates
    .map((l) => ({ ...l, montant: Number(stc[l.cle]) || 0 }))
    .filter((l) => l.montant !== 0)
})

const formatFcfa = (v) => `${Math.round(Number(v) || 0).toLocaleString('fr-FR')} F CFA`
const formatNombre = (v, decimales = 2) =>
  Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: decimales })

const printPage = () => window.print()

onMounted(fetchPrintData)
</script>

<template>
  <div v-if="loading" class="flex flex-col items-center justify-center min-h-screen space-y-4">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement du document…</span>
  </div>

  <div v-else-if="contrat && salarie" class="max-w-3xl mx-auto p-8 bg-white min-h-screen text-slate-900">

    <!-- Barre d'actions (masquée à l'impression) -->
    <div class="no-print mb-8 p-4 bg-slate-50 border border-slate-200 rounded-lg flex justify-between items-center shadow-sm">
      <button class="px-3 py-1.5 border border-slate-200 text-slate-700 font-semibold rounded-lg text-xs hover:bg-slate-100 inline-flex items-center gap-1" @click="router.back()">
        <UIcon name="i-lucide-arrow-left" class="w-4 h-4" />
        Retour
      </button>
      <div class="flex items-center gap-2">
        <button class="px-3 py-1.5 border border-slate-200 text-slate-700 font-semibold rounded-lg text-xs hover:bg-slate-100" @click="fetchPrintData">
          <UIcon name="i-lucide-refresh-cw" class="w-4 h-4" />
        </button>
        <button class="px-4 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs inline-flex items-center gap-1.5 shadow" @click="printPage">
          <UIcon name="i-lucide-printer" class="w-4 h-4" />
          Imprimer
        </button>
      </div>
    </div>

    <!-- ══════════════ REÇU ══════════════ -->
    <div class="flex flex-col justify-between min-h-[240mm]">
      <div class="space-y-6">
        <!-- En-tête -->
        <div class="flex justify-between items-start border-b border-slate-200 pb-6">
          <div class="space-y-1.5">
            <h2 class="text-lg font-bold text-slate-800 uppercase">{{ etab?.raison_sociale || etab?.nom || dossier?.nom_dossier }}</h2>
            <p class="text-xs text-slate-500">
              Établissement {{ etab?.code || '—' }}<br>
              NIF/RCCM : {{ etab?.nif || etab?.numero_contribuable || 'Non spécifié' }}
            </p>
          </div>
          <div class="text-right text-xs text-slate-500">
            <p class="font-mono">Fait à {{ etab?.ville || dossier?.ville || '………………' }}, le {{ new Date().toLocaleDateString('fr-FR') }}</p>
          </div>
        </div>

        <div class="text-center py-6">
          <h1 class="text-xl font-extrabold uppercase tracking-wider text-slate-900 border-2 border-slate-900 py-2.5 px-4 inline-block">
            Reçu pour solde de tout compte
          </h1>
        </div>

        <!-- Corps -->
        <div class="space-y-4 text-sm leading-relaxed text-slate-800">
          <p>
            Je soussigné(e), <strong>{{ salarie.prenom }} {{ salarie.nom }}</strong>,
            matricule <strong>{{ salarie.matricule }}</strong>,
            demeurant au {{ salarie.adresse || '…………………………………' }},
            reconnais avoir reçu de la société
            <strong>{{ dossier?.nom_dossier }} (établissement {{ etab?.raison_sociale || etab?.nom }})</strong>
            la somme totale nette de :
          </p>

          <div class="bg-slate-50 border border-slate-200 p-4 rounded-lg">
            <div class="text-center text-lg font-bold text-green-700 border-b border-slate-200 pb-2 mb-3">
              {{ formatFcfa(soldeToutCompte?.total) }}
            </div>
            <table class="w-full text-xs">
              <tbody>
                <tr v-for="ligne in lignesSolde" :key="ligne.cle" class="border-b border-slate-100">
                  <td class="py-1.5 text-slate-700">{{ ligne.libelle }}</td>
                  <td class="py-1.5 text-right font-mono text-slate-900 whitespace-nowrap">{{ formatFcfa(ligne.montant) }}</td>
                </tr>
                <tr v-if="!lignesSolde.length">
                  <td class="py-2 text-slate-400" colspan="2">Aucune indemnité enregistrée.</td>
                </tr>
                <tr class="font-bold text-slate-900">
                  <td class="pt-2 border-t border-slate-300">Total</td>
                  <td class="pt-2 text-right font-mono border-t border-slate-300">{{ formatFcfa(soldeToutCompte?.total) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <p>
            Cette somme m'est versée en règlement de tout compte, pour solde de tout salaire et
            indemnités de toutes natures dues au titre de l'exécution et de la cessation de mon
            contrat de travail, lequel a pris fin le <strong>{{ dateSortie }}</strong>
            pour le motif suivant : <strong>{{ motifLabel }}</strong>.
          </p>

          <p class="text-justify">
            Le présent reçu pour solde de tout compte est établi en double exemplaire, dont un m'a été
            remis. Je reconnais avoir été informé(e) que je dispose d'un délai de six (6) mois à
            compter de la signature de ce document pour le dénoncer par lettre recommandée ; passé
            ce délai, le reçu devient libératoire pour l'employeur pour les sommes qui y sont portées.
          </p>
        </div>
      </div>

      <!-- Signatures -->
      <div class="grid grid-cols-2 gap-12 pt-16 border-t border-slate-100">
        <div class="space-y-12">
          <p class="text-xs font-semibold text-slate-500 uppercase">Le salarié</p>
          <p class="text-xs text-slate-400 italic">
            (Faire précéder de la mention manuscrite<br>« Bon pour solde de tout compte »)
          </p>
        </div>
        <div class="space-y-12 text-right">
          <p class="text-xs font-semibold text-slate-500 uppercase">L'employeur</p>
          <p class="text-xs text-slate-400 italic">
            (Signature et cachet de l'entreprise)
          </p>
        </div>
      </div>
    </div>

    <!-- ══════════════ ANNEXE : DÉTAIL DU CALCUL ══════════════ -->
    <div v-if="details" class="page-break pt-10 mt-10 border-t-2 border-slate-300">
      <h2 class="text-sm font-bold uppercase tracking-wider text-slate-900 mb-4">
        Annexe — détail du calcul
      </h2>

      <!-- Repères généraux -->
      <table class="w-full text-xs mb-6">
        <tbody>
          <tr class="border-b border-slate-100">
            <td class="py-1.5 text-slate-600">Motif de fin de contrat</td>
            <td class="py-1.5 text-right font-semibold">{{ details.motif || motifLabel }}</td>
          </tr>
          <tr class="border-b border-slate-100">
            <td class="py-1.5 text-slate-600">Date de sortie</td>
            <td class="py-1.5 text-right font-mono">{{ details.date_sortie || dateSortie }}</td>
          </tr>
          <tr class="border-b border-slate-100">
            <td class="py-1.5 text-slate-600">Ancienneté retenue</td>
            <td class="py-1.5 text-right font-mono">{{ details.anciennete_mois }} mois complets</td>
          </tr>
          <tr class="border-b border-slate-100">
            <td class="py-1.5 text-slate-600">Salaire minimum conventionnel (SMHC)</td>
            <td class="py-1.5 text-right font-mono">{{ formatFcfa(details.smhc_mensuel) }}</td>
          </tr>
          <tr v-if="details.nombre_salaires_retenus" class="border-b border-slate-100">
            <td class="py-1.5 text-slate-600">Mois de référence retenus</td>
            <td class="py-1.5 text-right font-mono">{{ details.nombre_salaires_retenus }}</td>
          </tr>
        </tbody>
      </table>

      <!-- Indemnité de rupture -->
      <div v-if="details.rupture" class="mb-6">
        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
          Indemnité de rupture — décret n° 2017-210, art. 4
        </h3>
        <p class="text-xs text-slate-600 mb-2">
          Salaire global mensuel moyen des 12 derniers mois :
          <strong class="font-mono">{{ formatFcfa(details.rupture.salaire_global_moyen) }}</strong>
          <span v-if="details.rupture.eligible" class="text-emerald-700 font-semibold"> · éligible</span>
          <span v-else class="text-amber-700 font-semibold"> · non éligible</span>
        </p>
        <p v-if="details.rupture.motif_ineligibilite" class="text-xs px-2.5 py-2 bg-amber-50 border border-amber-200 rounded text-amber-800 mb-2">
          {{ details.rupture.motif_ineligibilite }}
        </p>
        <table v-if="details.rupture.tranches?.length" class="w-full text-xs border border-slate-200">
          <thead class="bg-slate-50 text-slate-600 uppercase tracking-wider text-[10px]">
            <tr>
              <th class="text-left px-2 py-1.5 border-b border-slate-200">Tranche</th>
              <th class="text-right px-2 py-1.5 border-b border-slate-200">Mois</th>
              <th class="text-right px-2 py-1.5 border-b border-slate-200">Années</th>
              <th class="text-right px-2 py-1.5 border-b border-slate-200">Taux</th>
              <th class="text-right px-2 py-1.5 border-b border-slate-200">Montant</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tranche in details.rupture.tranches" :key="tranche.libelle" class="border-b border-slate-100">
              <td class="px-2 py-1.5">{{ tranche.libelle }}</td>
              <td class="px-2 py-1.5 text-right font-mono">{{ tranche.mois_retenus }}</td>
              <td class="px-2 py-1.5 text-right font-mono">{{ formatNombre(tranche.annees_equivalentes, 4) }}</td>
              <td class="px-2 py-1.5 text-right font-mono">{{ Math.round(tranche.taux * 100) }} %</td>
              <td class="px-2 py-1.5 text-right font-mono">{{ formatFcfa(tranche.montant) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Décès -->
      <div v-if="details.deces" class="mb-6">
        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
          Droits des ayants droit
        </h3>
        <p class="text-xs text-slate-600">
          {{ details.deces.motif_eligibilite }} · frais funéraires
          <strong class="font-mono">{{ details.deces.multiplicateur_frais_funeraires }} × SMHC</strong>
        </p>
      </div>

      <!-- Fin de CDD -->
      <div v-if="details.fin_cdd" class="mb-6">
        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
          Indemnité de fin de CDD — art. 15.8 du Code du travail
        </h3>
        <table class="w-full text-xs">
          <tbody>
            <tr class="border-b border-slate-100">
              <td class="py-1.5 text-slate-600">Total des rémunérations brutes du contrat</td>
              <td class="py-1.5 text-right font-mono">{{ formatFcfa(details.fin_cdd.total_brut_cdd) }}</td>
            </tr>
            <tr class="border-b border-slate-100">
              <td class="py-1.5 text-slate-600">Taux légal appliqué</td>
              <td class="py-1.5 text-right font-mono">{{ formatNombre(details.fin_cdd.taux * 100, 0) }} %</td>
            </tr>
            <tr class="border-b border-slate-100">
              <td class="py-1.5 text-slate-600">Situation</td>
              <td class="py-1.5 text-right">{{ details.fin_cdd.motif }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Gratification -->
      <div v-if="details.gratification" class="mb-6">
        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
          Gratification annuelle — art. 53 de la convention collective
        </h3>
        <table class="w-full text-xs">
          <tbody>
            <tr class="border-b border-slate-100">
              <td class="py-1.5 text-slate-600">Salaire minimum conventionnel mensuel</td>
              <td class="py-1.5 text-right font-mono">{{ formatFcfa(details.gratification.smhc_mensuel) }}</td>
            </tr>
            <tr class="border-b border-slate-100">
              <td class="py-1.5 text-slate-600">Temps de service retenu (base 360 jours)</td>
              <td class="py-1.5 text-right font-mono">{{ formatNombre(details.gratification.jours_service, 0) }} jours · prorata {{ formatNombre(details.gratification.prorata, 4) }}</td>
            </tr>
            <tr class="border-b border-slate-100">
              <td class="py-1.5 text-slate-600">Minimum conventionnel à temps plein (75 %)</td>
              <td class="py-1.5 text-right font-mono">{{ formatFcfa(details.gratification.minimum_annuel_temps_plein) }}</td>
            </tr>
            <tr class="border-b border-slate-100">
              <td class="py-1.5 text-slate-600">Minimum proratisé</td>
              <td class="py-1.5 text-right font-mono">{{ formatFcfa(details.gratification.minimum_conventionnel_proratise) }}</td>
            </tr>
            <tr v-if="details.gratification.meilleur_montant_entreprise" class="border-b border-slate-100">
              <td class="py-1.5 text-slate-600">Disposition d'entreprise plus favorable</td>
              <td class="py-1.5 text-right font-mono">{{ formatFcfa(details.gratification.meilleur_montant_entreprise) }}</td>
            </tr>
            <tr class="font-semibold">
              <td class="py-1.5 text-slate-800">Montant retenu</td>
              <td class="py-1.5 text-right font-mono">{{ formatFcfa(details.gratification.gratification_retenue) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Congés payés -->
      <div v-if="details.conges" class="mb-6">
        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
          Congés payés — art. 25.1/25.2, 71-72 et décret n° 98-39
        </h3>
        <table class="w-full text-xs">
          <tbody>
            <tr class="border-b border-slate-100">
              <td class="py-1.5 text-slate-600">Droits acquis (2,2 jours ouvrables par mois)</td>
              <td class="py-1.5 text-right font-mono">{{ formatNombre(details.conges.jours_principaux_acquis, 2) }} jours</td>
            </tr>
            <tr class="border-b border-slate-100">
              <td class="py-1.5 text-slate-600">Solde de jours ouvrables / calendaires</td>
              <td class="py-1.5 text-right font-mono">
                {{ formatNombre(details.conges.solde_jours_ouvrables, 2) }} j ·
                {{ formatNombre(details.conges.solde_jours_calendaires, 2) }} j calendaires
              </td>
            </tr>
            <tr class="border-b border-slate-100">
              <td class="py-1.5 text-slate-600">Salaire journalier moyen (mensuel / 30)</td>
              <td class="py-1.5 text-right font-mono">{{ formatFcfa(details.conges.salaire_journalier) }}</td>
            </tr>
            <tr class="border-b border-slate-100">
              <td class="py-1.5 text-slate-600">Méthode conventionnelle (art. 71-72)</td>
              <td class="py-1.5 text-right font-mono">{{ formatFcfa(details.conges.montant_conventionnel) }}</td>
            </tr>
            <tr class="border-b border-slate-100">
              <td class="py-1.5 text-slate-600">Méthode du décret n° 98-39 (1/12)</td>
              <td class="py-1.5 text-right font-mono">{{ formatFcfa(details.conges.montant_decret) }}</td>
            </tr>
            <tr class="border-b border-slate-100">
              <td class="py-1.5 text-slate-600">Comparaison des méthodes</td>
              <td class="py-1.5 text-right">{{ details.conges.comparaison }}</td>
            </tr>
            <tr class="font-semibold">
              <td class="py-1.5 text-slate-800">Méthode retenue</td>
              <td class="py-1.5 text-right">{{ details.conges.methode_retenue }} — <span class="font-mono">{{ formatFcfa(soldeToutCompte?.indemnite_conges_payes) }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="text-[10px] text-slate-400 italic mt-6">
        Détail produit par PayOHADA à partir des textes en vigueur (décret n° 2017-210,
        Code du travail, convention collective interprofessionnelle, décret n° 98-39,
        note de service DGI du 08/07/2024). À conserver avec le dossier du salarié.
      </p>
    </div>

    <div v-else class="no-print mt-8 p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-500">
      Aucun détail de calcul n'est disponible : le solde de tout compte a été saisi
      manuellement ou enregistré avant la mise en place des calculateurs.
    </div>
  </div>

  <div v-else class="text-center py-20 text-red-500">
    Une erreur s'est produite lors du chargement des données.
  </div>
</template>

<style scoped>
@media print {
  .no-print {
    display: none !important;
  }
  .page-break {
    break-before: page;
    page-break-before: always;
  }
}
</style>
