<script setup>
const route = useRoute()
const router = useRouter()
const { get, put, post, delete: apiDelete } = useApi()
const toast = useToast()

const dossierId = route.params.dossierId
const etabId = route.params.id

const etab = ref(null)
const salaries = ref([])
const caisses = ref([])
const loading = ref(true)
const activeTab = ref('infos')

// Global State for breadcrumbs
const currentDossier = useState('current-dossier')

// Etablissement Form Fields
const etabCode = ref('')
const etabNom = ref('')
const etabPrincipal = ref(false)

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

const fetchEtabDetails = async () => {
  loading.value = true
  try {
    // Ensure parent dossier context is loaded
    if (!currentDossier.value) {
      const parentDossier = await get(`/dossiers/${dossierId}`)
      currentDossier.value = parentDossier
    }

    const data = await get(`/etablissements/${etabId}`)
    etab.value = data

    // Populate Main
    etabCode.value = data.code || ''
    etabNom.value = data.raison_sociale || ''
    etabPrincipal.value = data.etablissement_principal || false

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

    // Fetch Employees
    const sals = await get(`/etablissements/${etabId}/salaries`)
    salaries.value = sals || []

    // Fetch Caisses
    const cs = await get(`/etablissements/${etabId}/caisses`)
    caisses.value = cs || []

  } catch (e) {
    console.error(e)
    router.push(`/dossiers/${dossierId}`)
  } finally {
    loading.value = false
  }
}

const handleUpdateEtab = async () => {
  try {
    const payload = {
      raison_sociale: etabNom.value,
      code: etabCode.value,
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
      dgi_regime_fiscal: dgiRegimeFiscal.value || null
    }

    const res = await put(`/etablissements/${etabId}`, payload)
    if (res) {
      toast.add({
        title: 'Succès',
        description: 'Établissement mis à jour avec succès.',
        color: 'success'
      })
      await fetchEtabDetails()
    }
  } catch (e) {
    console.error(e)
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
      
      await fetchEtabDetails()
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
    await fetchEtabDetails()
  } catch (e) {
    console.error(e)
  }
}

const handleDeleteEtab = async () => {
  if (!confirm('Supprimer cet établissement ? Toutes les fiches salariés et contrats associés seront supprimés.')) return
  try {
    await apiDelete(`/etablissements/${etabId}`)
    toast.add({
      title: 'Supprimé',
      description: 'L\'établissement a été supprimé.',
      color: 'success'
    })
    router.push(`/dossiers/${dossierId}`)
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  fetchEtabDetails()
})
</script>

<template>
  <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Chargement de l'établissement...</span>
  </div>

  <div v-else-if="etab" class="space-y-6">
    <!-- Header Page -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-100 text-green-700 rounded-lg flex items-center justify-center font-bold text-lg">
          {{ etab.code }}
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-900 leading-tight">{{ etab.raison_sociale }}</h1>
        </div>
      </div>
      
      <div class="flex space-x-3">
        <button 
          @click="handleDeleteEtab"
          class="px-4 py-2 border border-red-200 text-sm font-semibold rounded-lg hover:bg-red-50 text-red-600 transition-colors flex items-center gap-1.5"
        >
          <UIcon name="i-lucide-trash-2" class="w-4 h-4" />
          Supprimer
        </button>
      </div>
    </div>

    <!-- SAP Fiori Tabs -->
    <div class="border-b border-slate-200">
      <nav class="flex space-x-8" aria-label="Tabs">
        <button 
          @click="activeTab = 'infos'"
          :class="[
            activeTab === 'infos' 
              ? 'border-green-600 text-green-700 font-bold' 
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all'
          ]"
        >
          Informations & Banque
        </button>
        <button 
          @click="activeTab = 'sals'"
          :class="[
            activeTab === 'sals' 
              ? 'border-green-600 text-green-700 font-bold' 
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all'
          ]"
        >
          Salariés ({{ salaries.length }})
        </button>
        <button 
          @click="activeTab = 'caisses'"
          :class="[
            activeTab === 'caisses' 
              ? 'border-green-600 text-green-700 font-bold' 
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all'
          ]"
        >
          Caisses de Cotisation ({{ caisses.length }})
        </button>
      </nav>
    </div>

    <!-- Tab 1: Info, Address & Bank -->
    <div v-show="activeTab === 'infos'" class="space-y-6">
      <form @submit.prevent="handleUpdateEtab" class="space-y-6">
        
        <!-- Main Form -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Profil Établissement</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Établissement</label>
              <input v-model="etabCode" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Raison Sociale</label>
              <input v-model="etabNom" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>

          <div class="flex items-center space-x-2 pt-2">
            <input id="is-principal" v-model="etabPrincipal" type="checkbox" class="rounded border-slate-300 text-green-600 focus:ring-green-500 h-4 w-4" />
            <label for="is-principal" class="text-sm font-medium text-slate-700">Établissement Principal du dossier</label>
          </div>
        </div>

        <!-- Address Sub-form -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Adresse de l'Établissement</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="md:col-span-2">
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Voie / Rue</label>
              <input v-model="addrVoie" type="text" placeholder="Ex: 15 Rue de la Paix" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Complément d'adresse</label>
              <input v-model="addrVoie2" type="text" placeholder="Bâtiment, escalier..." class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Postal</label>
              <input v-model="addrCode" type="text" placeholder="75001" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Ville</label>
              <input v-model="addrVille" type="text" placeholder="Paris" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Pays</label>
              <input v-model="addrPays" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
        </div>

        <!-- Bank Sub-form -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Informations Bancaires de l'Établissement</h3>
          
          <div class="flex items-center space-x-2 pb-2">
            <input id="bank-virement" v-model="bankVirement" type="checkbox" class="rounded border-slate-300 text-green-600 focus:ring-green-500 h-4 w-4" />
            <label for="bank-virement" class="text-sm font-medium text-slate-700">Autoriser le virement SEPA</label>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">IBAN</label>
              <input v-model="bankIban" type="text" placeholder="FR76..." class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code BIC (Swift)</label>
              <input v-model="bankBic" type="text" placeholder="Ex: UBAFRPP..." class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
          </div>
        </div>

        <!-- CNPS Sub-form -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Caisse Nationale de prévoyance sociale - CNPS</h3>
          
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Matricule employeur</label>
              <input v-model="cnpsMatricule" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code activité</label>
              <input v-model="cnpsCodeActivite" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code agence</label>
              <input v-model="cnpsCodeAgence" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code établissement</label>
              <input v-model="cnpsCodeEtablissement" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
          </div>

          <div>
            <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Agence de rattachement</label>
            <input v-model="cnpsAgenceRattachement" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Périodicité de paiement - CNPS</label>
              <select v-model="cnpsPeriodicitePaiement" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="Mensuelle">Mensuelle</option>
                <option value="Trimestrielle">Trimestrielle</option>
                <option value="Annuelle">Annuelle</option>
              </select>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Périodicité de paiement - CMU</label>
              <select v-model="cmuPeriodicitePaiement" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="Mensuelle">Mensuelle</option>
                <option value="Trimestrielle">Trimestrielle</option>
                <option value="Annuelle">Annuelle</option>
              </select>
            </div>
          </div>
        </div>

        <!-- DGI Sub-form -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Direction générale des impôts - DGI</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">N° de Compte contribuable</label>
              <input v-model="dgiCompteContribuable" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Centre des impôts</label>
              <input v-model="dgiCentreImpots" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Périodicité des déclarations</label>
              <select v-model="dgiPeriodiciteDeclaration" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="Mensuelle">Mensuelle</option>
                <option value="Trimestrielle">Trimestrielle</option>
                <option value="Annuelle">Annuelle</option>
              </select>
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Régime fiscal par défaut</label>
              <select v-model="dgiRegimeFiscal" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="Régime général">Régime général</option>
                <option value="Régime simplifié">Régime simplifié</option>
                <option value="Impôt synthétique">Impôt synthétique</option>
              </select>
            </div>
          </div>
        </div>

        <div class="flex justify-end">
          <button type="submit" class="px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow transition-colors">
            Enregistrer toutes les modifications
          </button>
        </div>
      </form>
    </div>

    <!-- Tab 2: Salariés -->
    <div v-show="activeTab === 'sals'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">Salariés de l'Établissement</h3>
            <p class="text-xs text-slate-500">Liste des fiches civiles des salariés déclarés dans cet établissement.</p>
          </div>
          <button 
            @click="router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/new`)"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-user-plus" class="w-3.5 h-3.5" />
            Ajouter un Salarié
          </button>
        </div>

        <!-- Employees Table -->
        <div v-if="salaries.length === 0" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun salarié enregistré dans cet établissement.
        </div>
        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Matricule</th>
                <th scope="col" class="px-6 py-3 text-left">Nom & Prénom</th>
                <th scope="col" class="px-6 py-3 text-left">N° Sécurité Sociale (NIR)</th>
                <th scope="col" class="px-6 py-3 text-left">Email</th>
                <th scope="col" class="px-6 py-3 text-left">Téléphone</th>
                <th scope="col" class="px-6 py-3 text-left">Statut</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr 
                v-for="sal in salaries" 
                :key="sal.id" 
                @click="router.push(`/dossiers/${dossierId}/etablissements/${etabId}/salaries/${sal.id}`)"
                class="hover:bg-slate-50 cursor-pointer group"
              >
                <td class="px-6 py-4 font-mono font-semibold text-slate-900">{{ sal.matricule }}</td>
                <td class="px-6 py-4 font-medium text-slate-700 group-hover:text-green-700 transition-colors">
                  {{ sal.nom.toUpperCase() }} {{ sal.prenom }}
                </td>
                <td class="px-6 py-4 font-mono text-slate-500">{{ sal.numero_securite_sociale || '-' }}</td>
                <td class="px-6 py-4 text-slate-500">{{ sal.email || '-' }}</td>
                <td class="px-6 py-4 text-slate-500 font-mono">{{ sal.telephone || '-' }}</td>
                <td class="px-6 py-4">
                  <span 
                    :class="[
                      sal.is_active ? 'bg-green-50 text-green-700 border-green-200' : 'bg-slate-100 text-slate-500 border-slate-200',
                      'px-2 py-0.5 rounded text-xs font-semibold border'
                    ]"
                  >
                    {{ sal.is_active ? 'Actif' : 'Inactif' }}
                  </span>
                </td>
                <td class="px-6 py-4 text-right">
                  <span class="text-green-600 group-hover:underline text-xs font-semibold flex items-center justify-end gap-1">
                    Fiche Salarié
                    <UIcon name="i-lucide-chevron-right" class="w-4 h-4" />
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>
    </div>

    <!-- Tab 3: Caisses de Cotisation -->
    <div v-show="activeTab === 'caisses'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">Caisses de Cotisation</h3>
            <p class="text-xs text-slate-500">Caisses de cotisations sociales rattachées à cet établissement (CNPS, Retraite...).</p>
          </div>
          <button 
            @click="caisseModalOpen = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-plus" class="w-3.5 h-3.5" />
            Ajouter une Caisse
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
                <td class="px-6 py-4">
                  <span class="px-2 py-0.5 rounded text-xs font-bold bg-green-50 text-green-700 border border-green-200 uppercase">
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
                    class="text-red-600 hover:text-red-700 text-xs font-semibold"
                  >
                    Détacher
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>
    </div>


    <!-- Modal: Add Caisse -->
    <UModal v-model:open="caisseModalOpen" title="Rattacher une Caisse de Cotisation">
      <template #content>
        <div class="p-6 space-y-4">
          <h2 class="text-lg font-bold text-slate-900 border-b border-slate-100 pb-2">Nouvelle Caisse</h2>
          
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Type de cotisation</label>
              <select v-model="caisseType" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="urssaf">CNPS (Sécurité Sociale)</option>
                <option value="retraite_complementaire">Retraite Complémentaire</option>
                <option value="prevoyance">Prévoyance / Mutuelle</option>
                <option value="autre">Autre</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom de la Caisse <span class="text-red-500">*</span></label>
              <input v-model="caisseNom" type="text" placeholder="Ex: URSSAF IDF" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Organisme</label>
              <input v-model="caisseDsn" type="text" placeholder="Ex: CNPS-01" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Numéro d'Affiliation</label>
              <input v-model="caisseAffiliation" type="text" placeholder="Ex: AFF12345" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4 border-t border-slate-100 pt-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">IBAN de Règlement</label>
              <input v-model="caisseIban" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">BIC</label>
              <input v-model="caisseBic" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono" />
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-100">
            <button type="button" @click="caisseModalOpen = false" class="px-4 py-2 border border-slate-200 text-sm font-semibold rounded-lg hover:bg-slate-50 text-slate-700 transition-colors">
              Annuler
            </button>
            <button type="button" @click="handleCreateCaisse" class="px-4 py-2 text-sm font-semibold bg-green-600 hover:bg-green-700 text-white rounded-lg shadow transition-colors">
              Rattacher la caisse
            </button>
          </div>
        </div>
      </template>
    </UModal>

  </div>
</template>
