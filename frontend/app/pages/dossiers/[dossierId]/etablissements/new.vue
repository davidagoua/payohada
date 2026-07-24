<script setup>
const route = useRoute()
const router = useRouter()
const { get, post, extractFieldErrors } = useApi()
const toast = useToast()

const dossierId = route.params.dossierId

// Form fields
const etabNom = ref('')
const etabCode = ref('Génération en cours...')
const fieldErrors = ref({})

const secteurs = ref([])
const etabSecteurId = ref(null)

const fetchSecteurs = async () => {
  try {
    secteurs.value = await get('/secteurs') || []
  } catch (e) {
    console.error("Error fetching secteurs:", e)
  }
}

const fetchNextCode = async () => {
  try {
    const res = await get(`/dossiers/${dossierId}/etablissements/next-code`)
    etabCode.value = res.code
  } catch (e) {
    console.error(e)
    etabCode.value = 'ETAB00000000'
  }
}

// CNPS fields
const cnpsMatricule = ref('')
const cnpsCodeActivite = ref('')
const cnpsCodeAgence = ref('')
const cnpsCodeEtablissement = ref('')
const cnpsAgenceRattachement = ref('')
const cnpsPeriodicitePaiement = ref('Mensuelle')
const cmuPeriodicitePaiement = ref('Mensuelle')

// DGI fields
const dgiCompteContribuable = ref('')
const dgiCentreImpots = ref('')
const dgiPeriodiciteDeclaration = ref('Mensuelle')
const dgiRegimeFiscal = ref('Régime général')

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

const loadingDossier = ref(true)
const currentDossier = useState('current-dossier')

const fetchDossierContext = async () => {
  loadingDossier.value = true
  try {
    if (!currentDossier.value) {
      const data = await get(`/dossiers/${dossierId}`)
      currentDossier.value = data
    }
  } catch (e) {
    console.error(e)
    router.push('/dossiers')
  } finally {
    loadingDossier.value = false
  }
}

const handleCreateEtablissement = async () => {
  fieldErrors.value = {}
  if (!etabNom.value || !etabCode.value) {
    toast.add({
      title: 'Validation',
      description: 'Le nom et le code de l\'établissement sont requis.',
      color: 'warning'
    })
    return
  }

  try {
    const payload = {
      code: etabCode.value,
      raison_sociale: etabNom.value,
      secteur_id: etabSecteurId.value ? Number(etabSecteurId.value) : null,
      siret: null,
      ape: null,
      ccn: null,
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

    const res = await post(`/dossiers/${dossierId}/etablissements`, payload)
    if (res) {
      toast.add({
        title: 'Établissement créé',
        description: `L'établissement ${res.raison_sociale} a été créé avec succès.`,
        color: 'success'
      })
      router.push(`/dossiers/${dossierId}`)
    }
  } catch (e) {
    console.error(e)
    if (e.status === 422) {
      fieldErrors.value = extractFieldErrors(e)
    }
  }
}

onMounted(async () => {
  await fetchDossierContext()
  await fetchNextCode()
  await fetchSecteurs()
})
</script>

<template>
  <div v-if="loadingDossier" class="flex flex-col items-center justify-center py-20 space-y-4">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement du contexte dossier...</span>
  </div>

  <div v-else class="max-w-2xl mx-auto space-y-6">
    <!-- Header Object page -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-50 text-green-700 rounded-lg flex items-center justify-center font-bold text-xl border border-green-200">
          <UIcon name="i-lucide-building" class="w-6 h-6" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-900 leading-tight">Nouvel Établissement</h1>
          <p class="text-xs text-slate-500 mt-1">Dossier client : {{ currentDossier?.nom_dossier }}</p>
        </div>
      </div>
    </div>

    <!-- Main Form -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <form @submit.prevent="handleCreateEtablissement" class="space-y-6">
        <div class="space-y-4">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Informations de l'Établissement</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Établissement <span class="text-red-500">*</span></label>
              <input 
                v-model="etabCode" 
                type="text" 
                required
                disabled
                placeholder="Génération en cours..." 
                class="mt-1 block w-full px-3 py-2 border border-slate-200 bg-slate-50 text-slate-450 rounded-lg focus:outline-none text-sm font-mono cursor-not-allowed"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom Établissement (Raison Sociale) <span class="text-red-500">*</span></label>
              <input 
                v-model="etabNom" 
                type="text" 
                required
                placeholder="Ex: Siège Social" 
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg focus:outline-none text-sm transition-colors',
                  fieldErrors.raison_sociale ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.raison_sociale" class="mt-1 text-xs text-red-650 font-medium">{{ fieldErrors.raison_sociale }}</p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Sigle</label>
              <input 
                v-model="etabSigle" 
                type="text" 
                placeholder="Ex: ACME" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">N° RCCM</label>
              <input 
                v-model="etabNumeroRccm" 
                type="text" 
                placeholder="Ex: CI-ABJ-01-202X-B12..." 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Date de création</label>
              <input 
                v-model="etabDateCreation" 
                type="date" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Secteur d'activité</label>
              <select 
                v-model="etabSecteurId" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 w-full"
              >
                <option :value="null">-- Aucun secteur sélectionné --</option>
                <option v-for="s in secteurs" :key="s.id" :value="s.id">{{ s.nom }}</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Detailed Physical Address & Contacts Section -->
        <div class="space-y-4 pt-4 border-t border-slate-100">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Adresse physique détaillée & Contacts</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Pays</label>
              <input 
                v-model="etabAdressePays" 
                type="text" 
                placeholder="Ex: COTE D'IVOIRE"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Commune</label>
              <input 
                v-model="etabAdresseCommune" 
                type="text" 
                placeholder="Ex: Cocody"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Quartier</label>
              <input 
                v-model="etabAdresseQuartier" 
                type="text" 
                placeholder="Ex: Angré"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
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
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Îlot</label>
              <input 
                v-model="etabAdresseIlot" 
                type="text" 
                placeholder="Ex: 12"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Lot</label>
              <input 
                v-model="etabAdresseLot" 
                type="text" 
                placeholder="Ex: 45"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Localisation détaillée / Indications</label>
            <textarea 
              v-model="etabAdresseLocalisation" 
              rows="2"
              placeholder="Ex: Non loin du rond-point, face à la pharmacie..."
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
            ></textarea>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Boîte Postale / Adresse postale</label>
              <input 
                v-model="etabAdressePostale" 
                type="text" 
                placeholder="Ex: BP 123 Abidjan"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Téléphone</label>
              <input 
                v-model="etabTelephone" 
                type="text" 
                placeholder="Ex: +225 07 00 00 00 00"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Fax</label>
              <input 
                v-model="etabFax" 
                type="text" 
                placeholder="Ex: +225 27 00 00 00 00"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
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
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Site Web</label>
              <input 
                v-model="etabSiteWeb" 
                type="url" 
                placeholder="Ex: https://www.entreprise.com"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
          </div>
        </div>

        <!-- Payroll, HR & Matricule Settings Section -->
        <div class="space-y-4 pt-4 border-t border-slate-100">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Paramètres de Paie, RH & Matricules</h3>
          
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Adresse d'édition (sur le bulletin de paie)</label>
            <textarea 
              v-model="etabAdresseBulletinPaie" 
              rows="2"
              placeholder="Ex: Siège Social - Abidjan, Cocody..."
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
            ></textarea>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Mode de décompte ancienneté</label>
              <select v-model="etabModeDecompteAnciennete" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500">
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
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm transition-colors focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white"
              />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Mode de gestion du solde congés</label>
              <select v-model="etabCongesModeGestionSolde" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500">
                <option value="Jours calendaires">Jours calendaires</option>
                <option value="Jours ouvrables">Jours ouvrables</option>
                <option value="Jours ouvrés">Jours ouvrés</option>
              </select>
            </div>
          </div>

          <div class="space-y-4 pt-2">
            <div class="flex items-center space-x-2">
              <input id="new-matricule-auto" v-model="etabMatriculeGenerationAuto" type="checkbox" class="rounded border-slate-300 text-green-600 focus:ring-green-500 h-4 w-4" />
              <label for="new-matricule-auto" class="text-sm font-semibold text-slate-700 uppercase tracking-wider">Génération automatique des matricules salariés</label>
            </div>

            <div v-if="etabMatriculeGenerationAuto" class="grid grid-cols-1 md:grid-cols-3 gap-6 bg-slate-50 p-4 rounded-lg border border-slate-200">
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Préfixe matricule</label>
                <input 
                  v-model="etabMatriculePrefixe" 
                  type="text" 
                  placeholder="Ex: EMP-"
                  class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm bg-white"
                />
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Suffixe matricule</label>
                <input 
                  v-model="etabMatriculeSuffixe" 
                  type="text" 
                  placeholder="Ex: -CI"
                  class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm bg-white"
                />
              </div>
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Numéro séquentiel de départ</label>
                <input 
                  v-model="etabMatriculeNumeroSequentiel" 
                  type="text" 
                  placeholder="Ex: 001"
                  class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none text-sm bg-white"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- CNPS Section -->
        <div class="space-y-4 pt-4 border-t border-slate-100">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Caisse Nationale de prévoyance sociale - CNPS</h3>
          
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Matricule employeur</label>
              <input 
                v-model="cnpsMatricule" 
                type="text" 
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm focus:outline-none font-mono transition-colors',
                  fieldErrors.cnps_matricule ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.cnps_matricule" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.cnps_matricule }}</p>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code activité</label>
              <input 
                v-model="cnpsCodeActivite" 
                type="text" 
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm focus:outline-none font-mono transition-colors',
                  fieldErrors.cnps_code_activite ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.cnps_code_activite" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.cnps_code_activite }}</p>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code agence</label>
              <input 
                v-model="cnpsCodeAgence" 
                type="text" 
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm focus:outline-none font-mono transition-colors',
                  fieldErrors.cnps_code_agence ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.cnps_code_agence" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.cnps_code_agence }}</p>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code établissement</label>
              <input 
                v-model="cnpsCodeEtablissement" 
                type="text" 
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm focus:outline-none font-mono transition-colors',
                  fieldErrors.cnps_code_etablissement ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.cnps_code_etablissement" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.cnps_code_etablissement }}</p>
            </div>
          </div>

          <div>
            <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Agence de rattachement</label>
            <input 
              v-model="cnpsAgenceRattachement" 
              type="text" 
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg text-sm focus:outline-none transition-colors',
                fieldErrors.cnps_agence_rattachement ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.cnps_agence_rattachement" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.cnps_agence_rattachement }}</p>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Périodicité de paiement - CNPS</label>
              <select v-model="cnpsPeriodicitePaiement" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500">
                <option value="Mensuelle">Mensuelle</option>
                <option value="Trimestrielle">Trimestrielle</option>
                <option value="Annuelle">Annuelle</option>
              </select>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Périodicité de paiement - CMU</label>
              <select v-model="cmuPeriodicitePaiement" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500">
                <option value="Mensuelle">Mensuelle</option>
                <option value="Trimestrielle">Trimestrielle</option>
                <option value="Annuelle">Annuelle</option>
              </select>
            </div>
          </div>
        </div>

        <!-- DGI Section -->
        <div class="space-y-4 pt-4 border-t border-slate-100">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Direction générale des impôts - DGI</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">N° de Compte contribuable</label>
              <input 
                v-model="dgiCompteContribuable" 
                type="text" 
                placeholder="Ex: 2401502E"
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm focus:outline-none font-mono transition-colors',
                  fieldErrors.dgi_compte_contribuable ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.dgi_compte_contribuable" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.dgi_compte_contribuable }}</p>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Centre des impôts</label>
              <input 
                v-model="dgiCentreImpots" 
                type="text" 
                placeholder="Ex: RIVIERA 2"
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg text-sm focus:outline-none transition-colors',
                  fieldErrors.dgi_centre_impots ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.dgi_centre_impots" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.dgi_centre_impots }}</p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Périodicité des déclarations</label>
              <select v-model="dgiPeriodiciteDeclaration" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500">
                <option value="Mensuelle">Mensuelle</option>
                <option value="Trimestrielle">Trimestrielle</option>
                <option value="Annuelle">Annuelle</option>
              </select>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Régime fiscal par défaut</label>
              <select v-model="dgiRegimeFiscal" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500">
                <option value="Régime général">Régime général</option>
                <option value="Régime simplifié">Régime simplifié</option>
                <option value="Impôt synthétique">Impôt synthétique</option>
              </select>
            </div>
          </div>
        </div>

        <div class="flex justify-end space-x-3 pt-4 border-t border-slate-100">
          <NuxtLink 
            :to="`/dossiers/${dossierId}`"
            class="px-4 py-2 border border-slate-200 text-sm font-semibold rounded-lg hover:bg-slate-50 text-slate-700 transition-colors"
          >
            Annuler
          </NuxtLink>
          <button 
            type="submit"
            class="px-4 py-2 text-sm font-semibold bg-green-600 hover:bg-green-700 text-white rounded-lg shadow transition-colors"
          >
            Créer l'établissement
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
