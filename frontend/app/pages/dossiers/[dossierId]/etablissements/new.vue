<script setup>
const route = useRoute()
const router = useRouter()
const { get, post } = useApi()
const toast = useToast()

const dossierId = route.params.dossierId

// Form fields
const etabNom = ref('')
const etabCode = ref('')

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
      dgi_regime_fiscal: dgiRegimeFiscal.value || null
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
  }
}

onMounted(() => {
  fetchDossierContext()
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
        
        <!-- General Section -->
        <div class="space-y-4">
          <h3 class="text-md font-bold text-slate-900 border-b border-slate-100 pb-2">Informations de l'Établissement</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Établissement <span class="text-red-500">*</span></label>
              <input 
                v-model="etabCode" 
                type="text" 
                required
                placeholder="Ex: ETAB01" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm font-mono"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom Établissement (Raison Sociale) <span class="text-red-500">*</span></label>
              <input 
                v-model="etabNom" 
                type="text" 
                required
                placeholder="Ex: Siège Social" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
              />
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
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 font-mono"
              />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code activité</label>
              <input 
                v-model="cnpsCodeActivite" 
                type="text" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 font-mono"
              />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code agence</label>
              <input 
                v-model="cnpsCodeAgence" 
                type="text" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 font-mono"
              />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Code établissement</label>
              <input 
                v-model="cnpsCodeEtablissement" 
                type="text" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 font-mono"
              />
            </div>
          </div>

          <div>
            <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Agence de rattachement</label>
            <input 
              v-model="cnpsAgenceRattachement" 
              type="text" 
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
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
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 font-mono"
              />
            </div>
            <div>
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Centre des impôts</label>
              <input 
                v-model="dgiCentreImpots" 
                type="text" 
                placeholder="Ex: RIVIERA 2"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
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
