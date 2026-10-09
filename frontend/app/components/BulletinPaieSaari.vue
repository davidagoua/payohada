<script setup>
/**
 * Bulletin de paie — présentation « Sage Saari ».
 *
 * Reproduit la structure du bulletin officiel utilisé en Côte d'Ivoire :
 * en-tête employeur, bloc salarié, tableau des rubriques ventilé en
 * Code / Désignation / Base / Taux / Gain / Retenue avec les charges
 * patronales en regard, totaux, **cadre des cumuls** (mensuel et annuel),
 * état des congés et zones de signature.
 *
 * Composant purement présentationnel : il reçoit les objets déjà chargés et ne
 * fait aucun appel réseau, afin d'être réutilisable en impression unitaire
 * comme en impression par lot.
 */
const props = defineProps({
  bulletin: { type: Object, required: true },
  contrat: { type: Object, default: null },
  salarie: { type: Object, default: null },
  etablissement: { type: Object, default: null },
  dossier: { type: Object, default: null },
  //: Numéro d'ordre lorsqu'un lot de bulletins est imprimé.
  rang: { type: Number, default: null },
  total: { type: Number, default: null }
})

const MOIS_LABELS = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
]

// Codes classés en cotisations et retenues, alignés sur le reste de l'application.
const CODES_COTISATIONS = [
  'IBS', 'RICF', 'CNPS_RETRAITE', 'CMU_S', 'CN', 'TA', 'TFC',
  'CNPS_PF', 'CNPS_AT', 'CNPS_MATERNITE', 'CMU_P'
]
const CODES_NET = [
  'TRANSPORT', 'TELEPHONE', 'ACOMPTE', 'FRAIS_PROFESSIONNELS', 'AUTRE_RETENUE'
]

const lignes = computed(() => props.bulletin?.lignes || [])

const estCotisation = (code) => CODES_COTISATIONS.includes(String(code).toUpperCase())
const estLigneNet = (code) => {
  const c = String(code).toUpperCase()
  return CODES_NET.includes(c) || c.startsWith('RET_')
}

const elementsBrut = computed(() => lignes.value.filter((l) => !estCotisation(l.code) && !estLigneNet(l.code)))
const cotisations = computed(() => lignes.value.filter((l) => estCotisation(l.code)))
const retenuesDiverses = computed(() => lignes.value.filter((l) => estLigneNet(l.code)))

const periode = computed(() => {
  const mois = props.bulletin?.mois
  const annee = props.bulletin?.annee
  if (!mois) return '-'
  return `${MOIS_LABELS[Number(mois) - 1]} ${annee}`
})

const cumulMensuel = computed(() => props.bulletin?.cumuls?.mensuel || null)
const cumulAnnuel = computed(() => props.bulletin?.cumuls?.annuel || null)

/** Lignes du cadre de cumuls : libellé + accès mensuel/annuel. */
const LIGNES_CUMULS = [
  { libelle: 'Heures / jours travaillés', cle: 'heures_jours' },
  { libelle: 'Heures supplémentaires', cle: 'heures_supp' },
  { libelle: "Jours d'absence", cle: 'jours_absences' },
  { libelle: 'Salaire brut', cle: 'salaire_brut' },
  { libelle: 'Brut imposable (ITS)', cle: 'brut_imposable' },
  { libelle: 'Brut CNPS', cle: 'brut_cnps' },
  { libelle: 'Base congés payés', cle: 'brut_conges' },
  { libelle: 'Impôt sur salaires (ITS)', cle: 'ibs' },
  { libelle: 'RICF', cle: 'ricf' },
  { libelle: 'CMU', cle: 'cmu' },
  { libelle: 'Retraite CNPS', cle: 'cot_retraite' },
  { libelle: 'Congés acquis', cle: 'conges_acquis' },
  { libelle: 'Congés pris', cle: 'conges_pris' },
  { libelle: 'Solde de congés', cle: 'conges_solde' }
]

//: Les lignes de cumuls sont réparties sur deux colonnes, comme dans le PDF.
const moitieCumuls = computed(() => Math.ceil(LIGNES_CUMULS.length / 2))
const lignesCumulsGauche = computed(() => LIGNES_CUMULS.slice(0, moitieCumuls.value))
const lignesCumulsDroite = computed(() => LIGNES_CUMULS.slice(moitieCumuls.value))

const montantCumul = (source, cle) => {
  const v = source?.[cle]
  return v === null || v === undefined || v === '' ? null : Number(v)
}

// ── Formatage ────────────────────────────────────────────────────────
const formatXOF = (v) => {
  if (v === null || v === undefined || v === '') return '-'
  const n = Number(v)
  if (!n) return '-'
  return n.toLocaleString('fr-FR', { maximumFractionDigits: 0 })
}

const formatNombre = (v) => {
  if (v === null || v === undefined || v === '') return '-'
  const n = Number(v)
  return n ? n.toLocaleString('fr-FR', { maximumFractionDigits: 2 }) : '-'
}

/**
 * Met en forme la colonne « Taux ».
 *
 * La sémantique de `taux_s` dépend de la ligne : un pourcentage pour les
 * cotisations et retenues (6,3 %), mais un taux horaire ou journalier **en
 * francs** pour les lignes de rémunération (1 730,80 F/h). Sans cette
 * distinction, le salaire de base s'affichait « 1 730,8 % ».
 */
const formatTaux = (v, estPourcentage = true) => {
  if (v === null || v === undefined || v === '') return '-'
  const n = Number(v)
  if (!n) return '-'
  if (!estPourcentage) return n.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
  const taux = n > 0 && n < 1 ? n * 100 : n
  return `${pourcentage(taux)} %`
}

const pourcentage = (v) => Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 3 })

const dateFr = (v) => {
  if (!v) return '-'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleDateString('fr-FR')
}

const adresseEtablissement = computed(() => {
  const a = props.etablissement?.adresse
  if (!a) return []
  if (typeof a === 'string') return [a]
  return [
    a.adresse_postale,
    a.adresse_postale2,
    [a.code_postal, a.ville].filter(Boolean).join(' '),
    a.pays
  ].filter(Boolean)
})

const libelleTypeContrat = computed(() => {
  const codes = { 10: 'CDI', 20: 'CDD', 29: 'CDD', 30: 'CDD', 40: 'Stage', 50: 'Apprentissage' }
  return codes[props.contrat?.type_contrat_travail] || '—'
})

const categorieEchelon = computed(() => {
  const p = props.contrat?.poste_salaire
  if (!p) return '—'
  return [p.categorie_professionnelle, p.echelon_categorie].filter(Boolean).join(' / ') || '—'
})

const estExpatrie = computed(() => !!props.salarie?.expatrie)
</script>

<template>
  <article class="bulletin-saari">
    <!-- ═══════════ EN-TÊTE ═══════════ -->
    <header class="entete">
      <div class="entete-employeur">
        <div class="raison-sociale">{{ etablissement?.raison_sociale || dossier?.nom_dossier || '—' }}</div>
        <div v-for="(ligne, i) in adresseEtablissement" :key="i">{{ ligne }}</div>
        <div v-if="etablissement?.activite">{{ etablissement.activite }}</div>
        <table class="identifiants">
          <tbody>
            <tr>
              <td>NIF / RCCM</td>
              <td>{{ etablissement?.siret || '—' }}</td>
              <td>Code établissement</td>
              <td>{{ etablissement?.code || '—' }}</td>
            </tr>
            <tr>
              <td>N° employeur CNPS</td>
              <td>{{ etablissement?.numero_cotisant || '—' }}</td>
              <td>Code activité</td>
              <td>{{ etablissement?.ape || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="entete-titre">
        <h1>Bulletin de paie</h1>
        <div class="periode">{{ periode }}</div>
        <table class="entete-meta">
          <tbody>
            <tr><td>Payé le</td><td>{{ dateFr(bulletin.date_paiement) }}</td></tr>
            <tr><td>Règlement</td><td>Virement bancaire</td></tr>
            <tr v-if="rang"><td>Bulletin</td><td>{{ rang }} / {{ total }}</td></tr>
          </tbody>
        </table>
      </div>
    </header>

    <!-- ═══════════ BLOC SALARIÉ ═══════════ -->
    <section class="bloc-salarie">
      <table>
        <tbody>
          <tr>
            <th>Matricule</th>
            <td class="mono">{{ salarie?.matricule || '—' }}</td>
            <th>Nom et prénoms</th>
            <td colspan="3" class="fort">
              {{ salarie?.nom?.toUpperCase() || '' }} {{ salarie?.prenom || '' }}
            </td>
          </tr>
          <tr>
            <th>Emploi</th>
            <td colspan="3">{{ contrat?.emploi || '—' }}</td>
            <th>Catégorie / échelon</th>
            <td>{{ categorieEchelon }}</td>
          </tr>
          <tr>
            <th>Type de contrat</th>
            <td>{{ libelleTypeContrat }}</td>
            <th>Date d'entrée</th>
            <td class="mono">{{ dateFr(contrat?.date_debut_contrat) }}</td>
            <th>Base de temps</th>
            <td>
              {{ contrat?.unite_temps === 'Jours'
                ? '30,00 jours / mois'
                : `${formatNombre(contrat?.horaires?.horaire_travail || 173.33)} heures / mois` }}
            </td>
          </tr>
          <tr>
            <th>Situation familiale</th>
            <td>{{ salarie?.situation_matrimoniale || '—' }}</td>
            <th>Enfants à charge</th>
            <td>{{ salarie?.enfants_charge ?? 0 }}</td>
            <th>N° CNPS salarié</th>
            <td class="mono">{{ salarie?.numero_securite_sociale || '—' }}</td>
          </tr>
          <tr>
            <th>Nationalité</th>
            <td>{{ salarie?.nationalite || '—' }}</td>
            <th>Date de naissance</th>
            <td class="mono">{{ dateFr(salarie?.date_naissance) }}</td>
            <th>Régime</th>
            <td>{{ estExpatrie ? 'Expatrié' : 'Local' }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- ═══════════ TABLEAU DES RUBRIQUES ═══════════ -->
    <table class="rubriques">
      <thead>
        <tr class="groupes">
          <th rowspan="2" class="col-code">Code</th>
          <th rowspan="2" class="col-libelle">Désignation</th>
          <th colspan="4">Part salariale</th>
          <th colspan="3" class="pat">Part patronale</th>
        </tr>
        <tr class="colonnes">
          <th>Base</th>
          <th>Taux</th>
          <th class="num">Gain</th>
          <th class="num">Retenue</th>
          <th class="pat">Base</th>
          <th class="pat">Taux</th>
          <th class="pat num">Montant</th>
        </tr>
      </thead>
      <tbody>
        <!-- 1. Éléments de salaire brut -->
        <tr class="section">
          <td colspan="9">1 — Éléments de salaire brut</td>
        </tr>
        <tr v-for="ligne in elementsBrut" :key="`b-${ligne.id || ligne.code}`">
          <td class="mono code">{{ ligne.code }}</td>
          <td>{{ ligne.libelle || ligne.code }}</td>
          <td class="mono">{{ formatNombre(ligne.base_s) }}</td>
          <td class="mono">{{ formatTaux(ligne.taux_s, estCotisation(ligne.code)) }}</td>
          <td class="mono num">{{ formatXOF(ligne.montant_pr) }}</td>
          <td class="mono num"></td>
          <td class="mono pat">{{ formatNombre(ligne.base_p) }}</td>
          <td class="mono pat">{{ formatTaux(ligne.taux_p, true) }}</td>
          <td class="mono pat num">{{ formatXOF(ligne.montant_cp) }}</td>
        </tr>
        <tr class="total">
          <td colspan="4">Total salaire brut</td>
          <td class="mono num">{{ formatXOF(bulletin.salaire_brut) }}</td>
          <td></td>
          <td colspan="2" class="pat"></td>
          <td class="mono pat num">{{ formatXOF(bulletin.cotisations_patronales) }}</td>
        </tr>

        <!-- 2. Cotisations et retenues -->
        <tr class="section">
          <td colspan="9">2 — Cotisations et retenues</td>
        </tr>
        <tr v-for="ligne in cotisations" :key="`c-${ligne.id || ligne.code}`">
          <td class="mono code">{{ ligne.code }}</td>
          <td>{{ ligne.libelle || ligne.code }}</td>
          <td class="mono">{{ formatNombre(ligne.base_s) }}</td>
          <td class="mono">{{ formatTaux(ligne.taux_s, estCotisation(ligne.code)) }}</td>
          <td class="mono num"></td>
          <td class="mono num">{{ formatXOF(ligne.montant_cs) }}</td>
          <td class="mono pat">{{ formatNombre(ligne.base_p) }}</td>
          <td class="mono pat">{{ formatTaux(ligne.taux_p, true) }}</td>
          <td class="mono pat num">{{ formatXOF(ligne.montant_cp) }}</td>
        </tr>

        <!-- 3. Indemnités et retenues diverses -->
        <tr class="section">
          <td colspan="9">3 — Indemnités et retenues diverses</td>
        </tr>
        <tr v-for="ligne in retenuesDiverses" :key="`n-${ligne.id || ligne.code}`">
          <td class="mono code">{{ ligne.code }}</td>
          <td>{{ ligne.libelle || ligne.code }}</td>
          <td class="mono">{{ formatNombre(ligne.base_s) }}</td>
          <td class="mono">{{ formatTaux(ligne.taux_s, estCotisation(ligne.code)) }}</td>
          <td class="mono num">{{ formatXOF(ligne.montant_pr) }}</td>
          <td class="mono num">{{ formatXOF(ligne.montant_cs) }}</td>
          <td class="mono pat">{{ formatNombre(ligne.base_p) }}</td>
          <td class="mono pat">{{ formatTaux(ligne.taux_p, true) }}</td>
          <td class="mono pat num">{{ formatXOF(ligne.montant_cp) }}</td>
        </tr>
        <tr v-if="!retenuesDiverses.length" class="vide">
          <td colspan="9">Néant</td>
        </tr>
      </tbody>
      <tfoot>
        <tr class="total">
          <td colspan="4">Total des retenues salariales</td>
          <td></td>
          <td class="mono num">{{ formatXOF(bulletin.cotisations_salariales) }}</td>
          <td colspan="3" class="pat"></td>
        </tr>
        <tr class="synthese">
          <td colspan="4">Net imposable (ITS)</td>
          <td colspan="2" class="mono num">{{ formatXOF(bulletin.net_imposable) }}</td>
          <td colspan="3" class="pat"></td>
        </tr>
        <tr class="net">
          <td colspan="4">NET À PAYER</td>
          <td colspan="2" class="mono num">{{ formatXOF(bulletin.net_a_payer) }}</td>
          <td colspan="3" class="pat"></td>
        </tr>
      </tfoot>
    </table>

    <!-- ═══════════ CADRE DES CUMULS ═══════════ -->
    <!--
      Cumuls présentés en deux blocs côte à côte : empiler les quatorze lignes
      fait déborder le bulletin sur une seconde page, alors qu'un mois courant
      doit tenir sur une seule. Le gabarit PDF suit la même disposition, les
      deux rendus devant rester identiques.
    -->
    <section class="cadre-cumuls">
      <div class="titre-cadre">Cumuls</div>
      <table>
        <thead>
          <tr>
            <th class="col-libelle">Libellé</th>
            <th>Mensuel</th>
            <th>Annuel</th>
            <th class="col-libelle">Libellé</th>
            <th>Mensuel</th>
            <th>Annuel</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(ligne, index) in lignesCumulsGauche" :key="ligne.cle">
            <td>{{ ligne.libelle }}</td>
            <td class="mono">{{ formatNombre(montantCumul(cumulMensuel, ligne.cle)) }}</td>
            <td class="mono">{{ formatNombre(montantCumul(cumulAnnuel, ligne.cle)) }}</td>
            <template v-if="lignesCumulsDroite[index]">
              <td>{{ lignesCumulsDroite[index].libelle }}</td>
              <td class="mono">
                {{ formatNombre(montantCumul(cumulMensuel, lignesCumulsDroite[index].cle)) }}
              </td>
              <td class="mono">
                {{ formatNombre(montantCumul(cumulAnnuel, lignesCumulsDroite[index].cle)) }}
              </td>
            </template>
            <td v-else colspan="3" class="cumul-vide"></td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- ═══════════ CONGÉS ET SIGNATURES ═══════════ -->
    <footer class="pied">
      <div class="conges">
        <span class="titre-cadre">Congés payés</span>
        <table>
          <tbody>
            <tr>
              <th>Acquis</th>
              <td class="mono">{{ formatNombre(cumulMensuel?.conges_acquis) }} j</td>
              <th>Pris</th>
              <td class="mono">{{ formatNombre(cumulMensuel?.conges_pris) }} j</td>
              <th>Solde</th>
              <td class="mono fort">{{ formatNombre(cumulMensuel?.conges_solde) }} j</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="signatures">
        <div>
          <span>Le salarié</span>
          <small>(Signature)</small>
        </div>
        <div>
          <span>L'employeur</span>
          <small>(Signature et cachet)</small>
        </div>
      </div>

      <p class="mentions">
        Bulletin à conserver sans limitation de durée. Les cotisations sociales sont
        calculées sur la base des taux en vigueur ; l'impôt sur les traitements et
        salaires est calculé selon le barème progressif et le réduit d'impôt pour
        charges de famille.
      </p>
    </footer>
  </article>
</template>

<style scoped>
.bulletin-saari {
  /* Présentation sobre, proche d'un état imprimé administratif. */
  font-family: Arial, Helvetica, sans-serif;
  font-size: 8.5px;
  line-height: 1.35;
  color: #000;
  background: #fff;
  width: 100%;
  max-width: 210mm;
  margin: 0 auto;
}

/* ── En-tête ─────────────────────────────────────────── */
.entete {
  display: flex;
  justify-content: space-between;
  gap: 8mm;
  border: 1px solid #000;
  padding: 3mm;
  margin-bottom: 2mm;
}
.entete-employeur { flex: 1 1 58%; }
.entete-titre { flex: 1 1 42%; text-align: right; }
.raison-sociale { font-weight: bold; font-size: 11px; text-transform: uppercase; }
.entete-titre h1 {
  font-size: 12px;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin: 0 0 1mm;
}
.periode {
  font-weight: bold;
  font-size: 10px;
  text-transform: uppercase;
  border: 1px solid #000;
  padding: 0.6mm 2mm;
  display: inline-block;
  margin-bottom: 1.5mm;
}
.identifiants,
.entete-meta { width: 100%; border-collapse: collapse; margin-top: 1.5mm; }
.identifiants td,
.entete-meta td { padding: 0.3mm 0; vertical-align: top; }
.identifiants td:nth-child(odd),
.entete-meta td:first-child { color: #444; padding-right: 2mm; }
.identifiants td:nth-child(even),
.entete-meta td:last-child { font-weight: bold; }
.entete-meta td:last-child { text-align: right; }

/* ── Bloc salarié ────────────────────────────────────── */
.bloc-salarie { border: 1px solid #000; margin-bottom: 2mm; }
.bloc-salarie table { width: 100%; border-collapse: collapse; }
.bloc-salarie th,
.bloc-salarie td {
  border: 1px solid #999;
  padding: 0.8mm 1.5mm;
  text-align: left;
  vertical-align: top;
}
.bloc-salarie th {
  background: #f0f0f0;
  font-weight: normal;
  color: #333;
  white-space: nowrap;
  width: 1%;
}
.fort { font-weight: bold; }

/* ── Tableau des rubriques ───────────────────────────── */
.rubriques { width: 100%; border-collapse: collapse; margin-bottom: 2mm; }
.rubriques th,
.rubriques td {
  border: 1px solid #999;
  padding: 0.7mm 1.2mm;
  vertical-align: top;
}
.rubriques thead th {
  background: #e8e8e8;
  text-align: center;
  font-weight: bold;
  text-transform: uppercase;
  font-size: 7.5px;
}
.rubriques thead .pat { background: #f4f4f4; }
.rubriques .col-code { width: 12mm; }
.rubriques .col-libelle { text-align: left; }
.rubriques .code { font-size: 7.5px; }
.num { text-align: right; }
.pat { background: #fafafa; }
.mono { font-family: "Courier New", Courier, monospace; }
.rubriques tr.section td {
  background: #dcdcdc;
  font-weight: bold;
  text-transform: uppercase;
  font-size: 7.5px;
  letter-spacing: 0.3px;
}
.rubriques tr.vide td { color: #666; font-style: italic; }
.rubriques tr.total td { background: #f0f0f0; font-weight: bold; }
.rubriques tr.synthese td { background: #f7f7f7; font-weight: bold; }
.rubriques tr.net td {
  background: #000;
  color: #fff;
  font-weight: bold;
  font-size: 10px;
  text-transform: uppercase;
}

/* ── Cadre des cumuls ────────────────────────────────── */
.cadre-cumuls { border: 1px solid #000; margin-bottom: 2mm; }
.titre-cadre {
  display: block;
  background: #dcdcdc;
  font-weight: bold;
  text-transform: uppercase;
  font-size: 7.5px;
  letter-spacing: 0.3px;
  padding: 0.8mm 1.5mm;
  border-bottom: 1px solid #000;
}
.cadre-cumuls table { width: 100%; border-collapse: collapse; }
.cadre-cumuls th,
.cadre-cumuls td { border: 1px solid #999; padding: 0.6mm 1.5mm; text-align: left; }
.cadre-cumuls thead th { background: #f0f0f0; text-align: center; }
.cadre-cumuls td:not(:first-child) { text-align: right; width: 32mm; }
.cadre-cumuls .col-libelle { text-align: left; }
/* Cellule de remplissage lorsque la colonne de droite n'a plus de ligne. */
.cadre-cumuls .cumul-vide { border: 0; background: transparent; }

/* ── Pied ────────────────────────────────────────────── */
.pied { border: 1px solid #000; padding: 2mm; }
.conges { margin-bottom: 3mm; }
.conges table { width: 100%; border-collapse: collapse; }
.conges th {
  background: #f0f0f0;
  font-weight: normal;
  color: #333;
  border: 1px solid #999;
  padding: 0.6mm 1.5mm;
  text-align: left;
  white-space: nowrap;
}
.conges td { border: 1px solid #999; padding: 0.6mm 1.5mm; text-align: right; }
.signatures {
  display: flex;
  justify-content: space-between;
  gap: 10mm;
  margin: 6mm 0 3mm;
}
.signatures div { flex: 1; text-align: center; }
.signatures span { display: block; font-weight: bold; text-transform: uppercase; font-size: 7.5px; }
.signatures small { color: #444; font-size: 7px; }
.mentions { font-size: 7px; color: #333; text-align: justify; margin: 0; }

/* ── Impression ──────────────────────────────────────── */
@media print {
  .bulletin-saari {
    max-width: none;
    width: 100%;
    page-break-after: always;
    break-after: page;
  }
  .bulletin-saari:last-child { page-break-after: auto; break-after: auto; }
  .rubriques tr.net td {
    background: #000 !important;
    color: #fff !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .rubriques thead th,
  .rubriques tr.section td,
  .titre-cadre,
  .bloc-salarie th,
  .cadres th {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
}

@page {
  size: A4 portrait;
  margin: 8mm;
}
</style>
