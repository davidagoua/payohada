<script setup>
/**
 * Onglet « Infos » d'un établissement : identification, CNPS, DGI/DFE,
 * adresses, banque, paramètres de paie et caisses de cotisation.
 * Émet `refresh` après chaque enregistrement pour que la page recharge.
 */
const props = defineProps({
  etab: { type: Object, required: true },
  caisses: { type: Array, required: true }
})
const emit = defineEmits(['refresh'])
const { caisses } = toRefs(props)
const etabId = props.etab.id

const { get, put, post, delete: apiDelete, extractFieldErrors } = useApi()
const toast = useToast()
const fieldErrors = ref({})

const selectedCaisses = ref([])

const allCaissesSelected = computed({
  get: () => caisses.value.length > 0 && selectedCaisses.value.length === caisses.value.length,
  set: (val) => {
    if (val) {
      selectedCaisses.value = caisses.value.map(c => c.id)
    } else {
      selectedCaisses.value = []
    }
  }
})

const handleBulkDeleteCaisses = async () => {
  if (selectedCaisses.value.length === 0) return
  if (!confirm(`Voulez-vous vraiment détacher les ${selectedCaisses.value.length} caisses de cotisation sélectionnées ?`)) return
  try {
    let successCount = 0
    for (const caisseId of selectedCaisses.value) {
      try {
        await apiDelete(`/caisses/${caisseId}`)
        successCount++
      } catch (e) {
        console.error(`Error deleting caisse ${caisseId}:`, e)
      }
    }
    toast.add({
      title: 'Action terminée',
      description: `${successCount} caisse(s) détachée(s) avec succès.`,
      color: 'success'
    })
    selectedCaisses.value = []
    emit('refresh')
  } catch (e) {
    console.error(e)
  } finally {
  }
}

// Etablissement Form Fields
const etabCode = ref('')
const etabNom = ref('')
const etabPrincipal = ref(false)
const etabSecteurId = ref(null)
const secteurs = ref([])

const fetchSecteurs = async () => {
  try {
    secteurs.value = await get('/secteurs') || []
  } catch (e) {
    console.error("Error loading secteurs:", e)
  }
}

// CNPS Fields
const cnpsMatricule = ref('')
const cnpsCodeActivite = ref('')
const cnpsCodeAgence = ref('')
const cnpsCodeEtablissement = ref('')
const cnpsAgenceRattachement = ref('')
const cnpsPeriodicitePaiement = ref('Mensuelle')
const cmuPeriodicitePaiement = ref('Mensuelle')

// DGI Fields
const dgiCompteContribuable = ref('')
const dgiCentreImpots = ref('')
const dgiPeriodiciteDeclaration = ref('Mensuelle')
const dgiRegimeFiscal = ref('Régime général')

// DFE — Document Fiscal d'Entreprise
const dfeCodeCdi = ref('')
const dfeCodeActivite = ref('')
const dfeRegimeImposition = ref('')
const dfeEstEmployeur = ref(false)
const dfeObligations = ref([])

/** Obligations fiscales cochables sur le DFE. */
const OBLIGATIONS_FISCALES = [
  { code: 'PATENTE', libelle: 'Patente' },
  { code: 'BIC_BA', libelle: 'Impôt BIC/BA' },
  { code: 'BNC', libelle: 'Impôt BNC' },
  { code: 'TVA', libelle: 'TVA' },
  { code: 'TOB', libelle: 'TOB' },
  { code: 'BOIS_GRUMES', libelle: 'Taxe sur les ventes de bois en grumes' }
]

// Identification supplémentaire
const etabSigle = ref('')
const etabNumeroRccm = ref('')
const etabDateCreation = ref('')

// Adresse physique détaillée
const etabAdressePays = ref("COTE D'IVOIRE")
const etabAdresseCommune = ref('')
const etabAdresseQuartier = ref('')
const etabAdresseRue = ref('')
const etabAdresseIlot = ref('')
const etabAdresseLot = ref('')
const etabAdresseLocalisation = ref('')

// Contacts
const etabAdressePostale = ref('')
const etabTelephone = ref('')
const etabFax = ref('')
const etabEmail = ref('')
const etabSiteWeb = ref('')

// Edition de paie
const etabAdresseBulletinPaie = ref('')

// Paramètres de paie & RH
const etabModeDecompteAnciennete = ref("Date anniversaire de la date d'entrée")
const etabCongesPeriodeReferenceMois = ref(12)
const etabCongesModeGestionSolde = ref('Jours calendaires')

// Configuration de la génération des matricules salariés
const etabMatriculeGenerationAuto = ref(true)
const etabMatriculePrefixe = ref('')
const etabMatriculeSuffixe = ref('')
const etabMatriculeNumeroSequentiel = ref('001')

// Address Form Fields
const addrVoie = ref('')
const addrVoie2 = ref('')
const addrComp = ref('')
const addrCode = ref('')
const addrVille = ref('')
const addrPays = ref('')

// Bank Form Fields
const bankVirement = ref(false)
const bankIban = ref('')
const bankBic = ref('')

// Cotisation Caisse Modal & Fields
const caisseModalOpen = ref(false)
const caisseNom = ref('')
const caisseType = ref('urssaf')
const caisseDsn = ref('')
const caisseAffiliation = ref('')
const caisseIban = ref('')
const caisseBic = ref('')

/** Recopie la fiche établissement dans les champs du formulaire. */
const remplirFormulaire = (data) => {
    // Populate Main
    etabCode.value = data.code || ''
    etabNom.value = data.raison_sociale || ''
    etabPrincipal.value = data.etablissement_principal || false
    etabSecteurId.value = data.secteur_id || null

    // Populate CNPS
    cnpsMatricule.value = data.cnps_matricule || ''
    cnpsCodeActivite.value = data.cnps_code_activite || ''
    cnpsCodeAgence.value = data.cnps_code_agence || ''
    cnpsCodeEtablissement.value = data.cnps_code_etablissement || ''
    cnpsAgenceRattachement.value = data.cnps_agence_rattachement || ''
    cnpsPeriodicitePaiement.value = data.cnps_periodicite_paiement || 'Mensuelle'
    cmuPeriodicitePaiement.value = data.cmu_periodicite_paiement || 'Mensuelle'

    // Populate DGI
    dgiCompteContribuable.value = data.dgi_compte_contribuable || ''
    dgiCentreImpots.value = data.dgi_centre_impots || ''
    dgiPeriodiciteDeclaration.value = data.dgi_periodicite_declaration || 'Mensuelle'
    dgiRegimeFiscal.value = data.dgi_regime_fiscal || 'Régime général'

    // Populate DFE
    dfeCodeCdi.value = data.dfe_code_cdi || ''
    dfeCodeActivite.value = data.dfe_code_activite || ''
    dfeRegimeImposition.value = data.dfe_regime_imposition || ''
    dfeEstEmployeur.value = data.dfe_est_employeur || false
    dfeObligations.value = (data.dfe_obligations_fiscales || '')
      .split(',')
      .map(code => code.trim())
      .filter(Boolean)

    // Populate Identification supplémentaire
    etabSigle.value = data.sigle || ''
    etabNumeroRccm.value = data.numero_rccm || ''
    etabDateCreation.value = data.date_creation ? data.date_creation.substring(0, 10) : ''

    // Populate Detailed Physical Address
    etabAdressePays.value = data.adresse_pays || "COTE D'IVOIRE"
    etabAdresseCommune.value = data.adresse_commune || ''
    etabAdresseQuartier.value = data.adresse_quartier || ''
    etabAdresseRue.value = data.adresse_rue || ''
    etabAdresseIlot.value = data.adresse_ilot || ''
    etabAdresseLot.value = data.adresse_lot || ''
    etabAdresseLocalisation.value = data.adresse_localisation || ''

    // Populate Contacts
    etabAdressePostale.value = data.adresse_postale || ''
    etabTelephone.value = data.telephone || ''
    etabFax.value = data.fax || ''
    etabEmail.value = data.email || ''
    etabSiteWeb.value = data.site_web || ''

    // Populate Edition de paie
    etabAdresseBulletinPaie.value = data.adresse_bulletin_paie || ''

    // Populate Paramètres de paie & RH
    etabModeDecompteAnciennete.value = data.mode_decompte_anciennete || "Date anniversaire de la date d'entrée"
    etabCongesPeriodeReferenceMois.value = data.conges_periode_reference_mois ?? 12
    etabCongesModeGestionSolde.value = data.conges_mode_gestion_solde || 'Jours calendaires'

    // Populate Configuration matricules
    etabMatriculeGenerationAuto.value = data.matricule_generation_auto ?? true
    etabMatriculePrefixe.value = data.matricule_prefixe || ''
    etabMatriculeSuffixe.value = data.matricule_suffixe || ''
    etabMatriculeNumeroSequentiel.value = data.matricule_numero_sequentiel || '001'

    // Populate Address
    if (data.adresse) {
      addrVoie.value = data.adresse.adresse_postale || ''
      addrVoie2.value = data.adresse.adresse_postale2 || ''
      addrComp.value = data.adresse.complement_adresse || ''
      addrCode.value = data.adresse.code_postal || ''
      addrVille.value = data.adresse.ville || ''
      addrPays.value = data.adresse.pays || ''
    }

    // Populate Bank
    if (data.banque) {
      bankVirement.value = data.banque.virement || false
      bankIban.value = data.banque.iban || ''
      bankBic.value = data.banque.code_bic || ''
    }
}

remplirFormulaire(props.etab)

const handleUpdateEtab = async () => {
  fieldErrors.value = {}
  try {
    const payload = {
      raison_sociale: etabNom.value,
      code: etabCode.value,
      secteur_id: etabSecteurId.value ? Number(etabSecteurId.value) : null,
      siret: null,
      ape: null,
      ccn: null,
      etablissement_principal: etabPrincipal.value,
      adresse: {
        adresse_postale: addrVoie.value || null,
        adresse_postale2: addrVoie2.value || null,
        complement_adresse: addrComp.value || null,
        code_postal: addrCode.value || null,
        ville: addrVille.value || null,
        pays: addrPays.value || null
      },
      banque: {
        virement: bankVirement.value,
        iban: bankIban.value || null,
        code_bic: bankBic.value || null
      },
      cnps_matricule: cnpsMatricule.value || null,
      cnps_code_activite: cnpsCodeActivite.value || null,
      cnps_code_agence: cnpsCodeAgence.value || null,
      cnps_code_etablissement: cnpsCodeEtablissement.value || null,
      cnps_agence_rattachement: cnpsAgenceRattachement.value || null,
      cnps_periodicite_paiement: cnpsPeriodicitePaiement.value || null,
      cmu_periodicite_paiement: cmuPeriodicitePaiement.value || null,
      dgi_compte_contribuable: dgiCompteContribuable.value || null,
      dgi_centre_impots: dgiCentreImpots.value || null,
      dgi_periodicite_declaration: dgiPeriodiciteDeclaration.value || null,
      dgi_regime_fiscal: dgiRegimeFiscal.value || null,
      dfe_code_cdi: dfeCodeCdi.value || null,
      dfe_code_activite: dfeCodeActivite.value || null,
      dfe_regime_imposition: dfeRegimeImposition.value || null,
      dfe_est_employeur: dfeEstEmployeur.value,
      dfe_obligations_fiscales: dfeObligations.value.length ? dfeObligations.value.join(',') : null,
      sigle: etabSigle.value || null,
      numero_rccm: etabNumeroRccm.value || null,
      date_creation: etabDateCreation.value || null,
      adresse_pays: etabAdressePays.value || null,
      adresse_commune: etabAdresseCommune.value || null,
      adresse_quartier: etabAdresseQuartier.value || null,
      adresse_rue: etabAdresseRue.value || null,
      adresse_ilot: etabAdresseIlot.value || null,
      adresse_lot: etabAdresseLot.value || null,
      adresse_localisation: etabAdresseLocalisation.value || null,
      adresse_postale: etabAdressePostale.value || null,
      telephone: etabTelephone.value || null,
      fax: etabFax.value || null,
      email: etabEmail.value || null,
      site_web: etabSiteWeb.value || null,
      adresse_bulletin_paie: etabAdresseBulletinPaie.value || null,
      mode_decompte_anciennete: etabModeDecompteAnciennete.value || null,
      conges_periode_reference_mois: etabCongesPeriodeReferenceMois.value !== null ? Number(etabCongesPeriodeReferenceMois.value) : 12,
      conges_mode_gestion_solde: etabCongesModeGestionSolde.value || null,
      matricule_generation_auto: etabMatriculeGenerationAuto.value,
      matricule_prefixe: etabMatriculePrefixe.value || null,
      matricule_suffixe: etabMatriculeSuffixe.value || null,
      matricule_numero_sequentiel: etabMatriculeNumeroSequentiel.value || null
    }

    const res = await put(`/etablissements/${etabId}`, payload)
    if (res) {
      toast.add({
        title: 'Succès',
        description: 'Établissement mis à jour avec succès.',
        color: 'success'
      })
      emit('refresh')
    }
  } catch (e) {
    console.error(e)
    if (e.status === 422) {
      fieldErrors.value = extractFieldErrors(e)
    }
  }
}

const handleCreateCaisse = async () => {
  if (!caisseNom.value) {
    toast.add({
      title: 'Validation',
      description: 'Le nom de la caisse de cotisation est obligatoire.',
      color: 'warning'
    })
    return
  }

  try {
    const payload = {
      nom_caisse: caisseNom.value,
      type_cotisation: caisseType.value,
      code_dsn: caisseDsn.value || null,
      numero_affiliation: caisseAffiliation.value || null,
      iban: caisseIban.value || null,
      bic: caisseBic.value || null
    }

    const res = await post(`/etablissements/${etabId}/caisses`, payload)
    if (res) {
      toast.add({
        title: 'Caisse ajoutée',
        description: 'La caisse de cotisation a été créée avec succès.',
        color: 'success'
      })
      caisseModalOpen.value = false
      // Reset Form
      caisseNom.value = ''
      caisseType.value = 'urssaf'
      caisseDsn.value = ''
      caisseAffiliation.value = ''
      caisseIban.value = ''
      caisseBic.value = ''

      emit('refresh')
    }
  } catch (e) {
    console.error(e)
  }
}

const handleDeleteCaisse = async (caisseId) => {
  if (!confirm('Voulez-vous supprimer cette caisse de cotisation ?')) return
  try {
    await apiDelete(`/caisses/${caisseId}`)
    toast.add({
      title: 'Caisse supprimée',
      description: 'La caisse a été détachée de l\'établissement.',
      color: 'success'
    })
    emit('refresh')
  } catch (e) {
    console.error(e)
  }
}

onMounted(fetchSecteurs)
</script>

<template>
  <div class="space-y-6">
      <form @submit.prevent="handleUpdateEtab" class="space-y-6">

        <!-- Main Form -->
        <div class="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-flat space-y-4 border-t-4 border-t-navy-900">
          <h3 class="text-sm font-bold text-navy-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Profil Établissement</h3>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Établissement</label>
              <input v-model="etabCode" type="text" disabled class="mt-1 block w-full px-3 py-2 border border-slate-200 rounded-lg text-sm font-mono bg-slate-50 text-slate-450 cursor-not-allowed focus:outline-none" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Raison Sociale</label>
              <input
                v-model="etabNom"
                type="text"
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm transition-colors focus:ring-green-500 focus:border-green-500 bg-white',
                  fieldErrors.raison_sociale ? 'border-red-300 bg-red-50/30' : 'border-slate-350'
                ]"
              />
              <p v-if="fieldErrors.raison_sociale" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.raison_sociale }}</p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Secteur d'activité</label>
              <select
                v-model="etabSecteurId"
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 w-full"
              >
                <option :value="null">-- Aucun secteur sélectionné --</option>
                <option v-for="s in secteurs" :key="s.id" :value="s.id">{{ s.nom }}</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Sigle</label>
              <input
                v-model="etabSigle"
                type="text"
                placeholder="Ex: ACME"
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">N° RCCM</label>
              <input
                v-model="etabNumeroRccm"
                type="text"
                placeholder="Ex: CI-ABJ-01-202X-B12..."
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Date de création</label>
              <input
                v-model="etabDateCreation"
                type="date"
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
          </div>

          <div class="flex items-center space-x-2 pt-2">
            <input id="is-principal" v-model="etabPrincipal" type="checkbox" class="rounded-lg border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
            <label for="is-principal" class="text-sm font-bold text-slate-700 uppercase tracking-wider">Établissement Principal du dossier</label>
          </div>
        </div>

        <!-- Address Sub-form -->
        <div class="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-flat space-y-4 border-t-4 border-t-navy-900">
          <h3 class="text-sm font-bold text-navy-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Adresse de l'Établissement</h3>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="md:col-span-2">
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Voie / Rue</label>
              <input v-model="addrVoie" type="text" placeholder="Ex: 15 Rue de la Paix" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Complément d'adresse</label>
              <input v-model="addrVoie2" type="text" placeholder="Bâtiment, escalier..." class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Postal</label>
              <input v-model="addrCode" type="text" placeholder="75001" class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Ville</label>
              <input v-model="addrVille" type="text" placeholder="Paris" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Pays</label>
              <input v-model="addrPays" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>
        </div>

        <!-- Detailed Physical Address & Contacts Section -->
        <div class="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-flat space-y-4 border-t-4 border-t-navy-900">
          <h3 class="text-sm font-bold text-navy-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Adresse physique détaillée & Contacts (Côte d'Ivoire / Local)</h3>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Pays d'adresse</label>
              <input
                v-model="etabAdressePays"
                type="text"
                placeholder="Ex: COTE D'IVOIRE"
                class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Commune</label>
              <input
                v-model="etabAdresseCommune"
                type="text"
                placeholder="Ex: Cocody"
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Quartier</label>
              <input
                v-model="etabAdresseQuartier"
                type="text"
                placeholder="Ex: Angré"
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Rue</label>
              <input
                v-model="etabAdresseRue"
                type="text"
                placeholder="Ex: Rue des Banques"
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Îlot</label>
              <input
                v-model="etabAdresseIlot"
                type="text"
                placeholder="Ex: 12"
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Lot</label>
              <input
                v-model="etabAdresseLot"
                type="text"
                placeholder="Ex: 45"
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Localisation détaillée / Indications</label>
            <textarea
              v-model="etabAdresseLocalisation"
              rows="2"
              placeholder="Ex: Non loin du rond-point, face à la pharmacie..."
              class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white"
            ></textarea>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Boîte Postale / Adresse postale</label>
              <input
                v-model="etabAdressePostale"
                type="text"
                placeholder="Ex: BP 123 Abidjan"
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Téléphone</label>
              <input
                v-model="etabTelephone"
                type="text"
                placeholder="Ex: +225 07 00 00 00 00"
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Fax</label>
              <input
                v-model="etabFax"
                type="text"
                placeholder="Ex: +225 27 00 00 00 00"
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">E-mail</label>
              <input
                v-model="etabEmail"
                type="email"
                placeholder="Ex: contact@entreprise.com"
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Site Web</label>
              <input
                v-model="etabSiteWeb"
                type="url"
                placeholder="Ex: https://www.entreprise.com"
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
          </div>
        </div>

        <!-- Bank Sub-form -->
        <div class="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-flat space-y-4 border-t-4 border-t-navy-900">
          <h3 class="text-sm font-bold text-navy-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Informations Bancaires de l'Établissement</h3>

          <div class="flex items-center space-x-2 pb-2">
            <input id="bank-virement" v-model="bankVirement" type="checkbox" class="rounded-lg border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
            <label for="bank-virement" class="text-sm font-bold text-slate-700 uppercase tracking-wider">Autoriser le virement SEPA</label>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">IBAN</label>
              <input v-model="bankIban" type="text" placeholder="FR76..." class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code BIC (Swift)</label>
              <input v-model="bankBic" type="text" placeholder="Ex: UBAFRPP..." class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>
        </div>

        <!-- CNPS Sub-form -->
        <div class="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-flat space-y-4 border-t-4 border-t-navy-900">
          <h3 class="text-sm font-bold text-navy-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Caisse Nationale de prévoyance sociale - CNPS</h3>

          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Matricule employeur</label>
              <input
                v-model="cnpsMatricule"
                type="text"
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white transition-colors',
                  fieldErrors.cnps_matricule ? 'border-red-300 bg-red-50/30' : 'border-slate-350'
                ]"
              />
              <p v-if="fieldErrors.cnps_matricule" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.cnps_matricule }}</p>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code activité</label>
              <input
                v-model="cnpsCodeActivite"
                type="text"
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white transition-colors',
                  fieldErrors.cnps_code_activite ? 'border-red-300 bg-red-50/30' : 'border-slate-350'
                ]"
              />
              <p v-if="fieldErrors.cnps_code_activite" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.cnps_code_activite }}</p>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code agence</label>
              <input
                v-model="cnpsCodeAgence"
                type="text"
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white transition-colors',
                  fieldErrors.cnps_code_agence ? 'border-red-300 bg-red-50/30' : 'border-slate-350'
                ]"
              />
              <p v-if="fieldErrors.cnps_code_agence" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.cnps_code_agence }}</p>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code établissement</label>
              <input
                v-model="cnpsCodeEtablissement"
                type="text"
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white transition-colors',
                  fieldErrors.cnps_code_etablissement ? 'border-red-300 bg-red-50/30' : 'border-slate-350'
                ]"
              />
              <p v-if="fieldErrors.cnps_code_etablissement" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.cnps_code_etablissement }}</p>
            </div>
          </div>

          <div>
            <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Agence de rattachement</label>
            <input
              v-model="cnpsAgenceRattachement"
              type="text"
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white transition-colors',
                fieldErrors.cnps_agence_rattachement ? 'border-red-300 bg-red-50/30' : 'border-slate-350'
              ]"
            />
            <p v-if="fieldErrors.cnps_agence_rattachement" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.cnps_agence_rattachement }}</p>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Périodicité de paiement - CNPS</label>
              <select v-model="cnpsPeriodicitePaiement" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white select">
                <option value="Mensuelle">Mensuelle</option>
                <option value="Trimestrielle">Trimestrielle</option>
                <option value="Annuelle">Annuelle</option>
              </select>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Périodicité de paiement - CMU</label>
              <select v-model="cmuPeriodicitePaiement" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white select">
                <option value="Mensuelle">Mensuelle</option>
                <option value="Trimestrielle">Trimestrielle</option>
                <option value="Annuelle">Annuelle</option>
              </select>
            </div>
          </div>
        </div>

        <!-- DGI Sub-form -->
        <div class="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-flat space-y-4 border-t-4 border-t-navy-900">
          <h3 class="text-sm font-bold text-navy-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Direction générale des impôts - DGI</h3>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">N° de Compte contribuable</label>
              <input
                v-model="dgiCompteContribuable"
                type="text"
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white transition-colors',
                  fieldErrors.dgi_compte_contribuable ? 'border-red-300 bg-red-50/30' : 'border-slate-350'
                ]"
              />
              <p v-if="fieldErrors.dgi_compte_contribuable" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.dgi_compte_contribuable }}</p>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Centre des impôts</label>
              <input
                v-model="dgiCentreImpots"
                type="text"
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white transition-colors',
                  fieldErrors.dgi_centre_impots ? 'border-red-300 bg-red-50/30' : 'border-slate-350'
                ]"
              />
              <p v-if="fieldErrors.dgi_centre_impots" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.dgi_centre_impots }}</p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Périodicité des déclarations</label>
              <select v-model="dgiPeriodiciteDeclaration" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white select">
                <option value="Mensuelle">Mensuelle</option>
                <option value="Trimestrielle">Trimestrielle</option>
                <option value="Annuelle">Annuelle</option>
              </select>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Régime fiscal par défaut</label>
              <select v-model="dgiRegimeFiscal" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white select">
                <option value="Régime général">Régime général</option>
                <option value="Régime simplifié">Régime simplifié</option>
                <option value="Impôt synthétique">Impôt synthétique</option>
              </select>
            </div>
          </div>
        </div>

        <!-- DFE : Document Fiscal d'Entreprise -->
        <div class="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-flat space-y-4 border-t-4 border-t-navy-900">
          <h3 class="text-sm font-bold text-navy-900 border-b border-slate-200 pb-2 uppercase tracking-wider">DFE — Document Fiscal d'Entreprise</h3>
          <p class="text-xs text-slate-500">
            Repris de la liasse DGI. Le n° de compte contribuable se saisit plus haut, dans les informations DGI.
          </p>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code CDI</label>
              <input v-model="dfeCodeCdi" type="text" maxlength="10" placeholder="Ex : 611"
                     class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono bg-white" />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code activité (DFE)</label>
              <input v-model="dfeCodeActivite" type="text" maxlength="20" placeholder="Ex : CCE0802"
                     class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono bg-white" />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Régime d'imposition</label>
              <select v-model="dfeRegimeImposition" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white select">
                <option value="">-- Non précisé --</option>
                <option value="RNI">RNI</option>
                <option value="RSI">RSI</option>
                <option value="IM">IM</option>
                <option value="TEE">TEE</option>
              </select>
            </div>
          </div>

          <div class="flex items-center space-x-2">
            <input id="edit-dfe-employeur" v-model="dfeEstEmployeur" type="checkbox" class="rounded-lg border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
            <label for="edit-dfe-employeur" class="text-sm font-semibold text-slate-700 uppercase tracking-wider">Employeur</label>
          </div>

          <div>
            <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Obligations fiscales</label>
            <div class="mt-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              <label v-for="obligation in OBLIGATIONS_FISCALES" :key="obligation.code" class="flex items-center gap-2 text-sm text-slate-700">
                <input v-model="dfeObligations" type="checkbox" :value="obligation.code"
                       class="rounded-lg border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                {{ obligation.libelle }}
              </label>
            </div>
          </div>
        </div>

        <!-- Payroll, HR & Matricule Settings Section -->
        <div class="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-flat space-y-4 border-t-4 border-t-navy-900">
          <h3 class="text-sm font-bold text-navy-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Paramètres de Paie, RH & Matricules</h3>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Adresse d'édition (sur le bulletin de paie)</label>
            <textarea
              v-model="etabAdresseBulletinPaie"
              rows="2"
              placeholder="Ex: Siège Social - Abidjan, Cocody..."
              class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white focus:ring-green-500 focus:border-green-500"
            ></textarea>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Mode de décompte ancienneté</label>
              <select v-model="etabModeDecompteAnciennete" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white select focus:ring-green-500 focus:border-green-500">
                <option value="Date anniversaire de la date d'entrée">Date anniversaire de la date d'entrée</option>
                <option value="Année civile">Année civile</option>
              </select>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Période de référence congés (mois)</label>
              <input
                v-model="etabCongesPeriodeReferenceMois"
                type="number"
                min="1"
                max="12"
                class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white focus:ring-green-500 focus:border-green-500"
              />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Mode de gestion du solde congés</label>
              <select v-model="etabCongesModeGestionSolde" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white select focus:ring-green-500 focus:border-green-500">
                <option value="Jours calendaires">Jours calendaires</option>
                <option value="Jours ouvrables">Jours ouvrables</option>
                <option value="Jours ouvrés">Jours ouvrés</option>
              </select>
            </div>
          </div>

          <div class="space-y-4 pt-2">
            <div class="flex items-center space-x-2">
              <input id="edit-matricule-auto" v-model="etabMatriculeGenerationAuto" type="checkbox" class="rounded-lg border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
              <label for="edit-matricule-auto" class="text-sm font-bold text-slate-700 uppercase tracking-wider">Génération automatique des matricules salariés</label>
            </div>

            <div v-if="etabMatriculeGenerationAuto" class="grid grid-cols-1 md:grid-cols-3 gap-6 bg-slate-50 p-4 border border-slate-200 rounded-lg">
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Préfixe matricule</label>
                <input
                  v-model="etabMatriculePrefixe"
                  type="text"
                  placeholder="Ex: EMP-"
                  class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white"
                />
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Suffixe matricule</label>
                <input
                  v-model="etabMatriculeSuffixe"
                  type="text"
                  placeholder="Ex: -CI"
                  class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white"
                />
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Numéro séquentiel de départ</label>
                <input
                  v-model="etabMatriculeNumeroSequentiel"
                  type="text"
                  placeholder="Ex: 001"
                  class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm bg-white"
                />
              </div>
            </div>
          </div>
        </div>

        <div class="flex justify-end">
          <button type="submit" class="px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
            Enregistrer toutes les modifications
          </button>
        </div>
      </form>

      <!-- Caisses de Cotisation Section (Fused at the bottom of General Info) -->
      <div class="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-flat border-t-4 border-t-navy-900">
        <div class="flex justify-between items-center border-b border-slate-200 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-navy-900 uppercase tracking-wider">Caisses de Cotisation</h3>
            <p class="text-xs text-slate-500">Caisses de cotisations sociales rattachées à cet établissement (CNPS, Retraite...).</p>
          </div>
          <button
            @click="caisseModalOpen = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-flat uppercase tracking-wider cursor-pointer"
          >
            <UIcon name="i-lucide-plus" class="w-3.5 h-3.5" />
            Ajouter une Caisse
          </button>
        </div>

        <!-- Bulk Actions Bar -->
        <div v-if="selectedCaisses.length > 0" class="bg-slate-100 border border-slate-300 p-3 mb-4 flex items-center justify-between text-xs transition-all">
          <div class="font-bold text-slate-700">
            {{ selectedCaisses.length }} caisse(s) sélectionnée(s)
          </div>
          <button
            @click="handleBulkDeleteCaisses"
            class="p-1.5 bg-red-650 hover:bg-red-755 text-white transition-colors shadow-flat cursor-pointer flex items-center justify-center"
            title="Détacher la sélection"
          >
            <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
          </button>
        </div>

        <!-- Caisses Table -->
        <div v-if="caisses.length === 0" class="text-center py-12 text-slate-500 italic text-sm">
          Aucune caisse rattachée pour le moment.
        </div>
        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left w-10">
                  <input type="checkbox" v-model="allCaissesSelected" class="rounded-lg border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </th>
                <th scope="col" class="px-6 py-3 text-left">Type</th>
                <th scope="col" class="px-6 py-3 text-left">Nom de la Caisse</th>
                <th scope="col" class="px-6 py-3 text-left">Code Organisme</th>
                <th scope="col" class="px-6 py-3 text-left">N° Affiliation</th>
                <th scope="col" class="px-6 py-3 text-left">IBAN / BIC</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="c in caisses" :key="c.id" class="hover:bg-slate-50">
                <td class="px-4 py-4" @click.stop>
                  <input type="checkbox" :value="c.id" v-model="selectedCaisses" class="rounded-lg border-slate-350 text-green-600 focus:ring-green-500 h-4 w-4" />
                </td>
                <td class="px-6 py-4">
                  <span class="px-2 py-0.5 rounded-lg text-xs font-bold bg-navy-50 text-navy-700 border border-navy-200 uppercase">
                    {{ c.type_cotisation }}
                  </span>
                </td>
                <td class="px-6 py-4 font-semibold text-slate-700">{{ c.nom_caisse }}</td>
                <td class="px-6 py-4 font-mono text-slate-500">{{ c.code_dsn || '-' }}</td>
                <td class="px-6 py-4 font-mono text-slate-500">{{ c.numero_affiliation || '-' }}</td>
                <td class="px-6 py-4 text-xs text-slate-500 font-mono">
                  <p v-if="c.iban">IBAN : {{ c.iban }}</p>
                  <p v-if="c.bic">BIC : {{ c.bic }}</p>
                  <span v-if="!c.iban && !c.bic">-</span>
                </td>
                <td class="px-6 py-4 text-right">
                  <button
                    @click="handleDeleteCaisse(c.id)"
                    class="text-red-650 hover:text-red-750 cursor-pointer flex items-center justify-end w-full"
                    title="Détacher la caisse"
                  >
                    <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    <UModal v-model:open="caisseModalOpen" title="Rattacher une Caisse de Cotisation">
      <template #content>
        <div class="p-6 space-y-4 rounded-xl bg-white border border-slate-200">
          <h2 class="text-lg font-bold text-navy-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Nouvelle Caisse</h2>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Type de cotisation</label>
              <select v-model="caisseType" class="mt-1 block w-full px-3 py-2 border border-slate-355 rounded-lg text-sm bg-white select">
                <option value="urssaf">CNPS (Sécurité Sociale)</option>
                <option value="retraite_complementaire">Retraite Complémentaire</option>
                <option value="prevoyance">Prévoyance / Mutuelle</option>
                <option value="autre">Autre</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom de la Caisse <span class="text-red-500">*</span></label>
              <input v-model="caisseNom" type="text" placeholder="Ex: URSSAF IDF" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Organisme</label>
              <input v-model="caisseDsn" type="text" placeholder="Ex: CNPS-01" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Numéro d'Affiliation</label>
              <input v-model="caisseAffiliation" type="text" placeholder="Ex: AFF12345" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4 border-t border-slate-200 pt-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">IBAN de Règlement</label>
              <input v-model="caisseIban" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">BIC</label>
              <input v-model="caisseBic" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-lg text-sm font-mono focus:ring-green-500 focus:border-green-500 bg-white" />
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button type="button" @click="caisseModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-sm font-bold rounded-lg hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
              Annuler
            </button>
            <button type="button" @click="handleCreateCaisse" class="px-4 py-2 text-sm font-bold bg-green-600 hover:bg-green-700 text-white rounded-lg shadow-flat transition-colors uppercase tracking-wider cursor-pointer">
              Rattacher la caisse
            </button>
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>

<style scoped>
.select {
  appearance: none;
  background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236B7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='m6 8 4 4 4-4'/%3E%3C/svg%3E");
  background-position: right 0.5rem center;
  background-repeat: no-repeat;
  background-size: 1.25em 1.25em;
  padding-right: 2.5rem;
}
</style>
