<script setup>
const { user } = useSupabase()
const { get, post } = useApi()
const toast = useToast()

const dossiers = ref([])
const loading = ref(true)
const modalOpen = ref(false)

// Form fields for dossier creation
const code = ref('')
const nomDossier = ref('')
const rccm = ref('')
const jourVirement = ref(null)
const pays = ref("Côte d'Ivoire")
const email = ref('')
const telephone = ref('')
const nomContact = ref('')
const qualite = ref(1)
const annee = ref(new Date().getFullYear().toString())

const fetchDossiers = async () => {
  loading.value = true
  try {
    const data = await get('/dossiers')
    dossiers.value = data || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const handleCreateDossier = async () => {
  if (!code.value || !nomDossier.value) {
    toast.add({
      title: 'Validation',
      description: 'Le code et le nom du dossier sont obligatoires.',
      color: 'warning'
    })
    return
  }

  try {
    const payload = {
      code: code.value,
      nom_dossier: nomDossier.value,
      rccm: rccm.value || null,
      jour_virement: jourVirement.value || null,
      adresse_email: email.value || null,
      telephone: telephone.value || null,
      nom_contact: nomContact.value || null,
      qualite: Number(qualite.value) || null,
      annee: annee.value || null,
      pays: pays.value || "Côte d'Ivoire"
    }

    const newDossier = await post('/dossiers', payload)
    if (newDossier) {
      toast.add({
        title: 'Succès',
        description: `Le dossier ${newDossier.nom_dossier} a été créé avec succès.`,
        color: 'success'
      })
      modalOpen.value = false
      // Reset form
      code.value = ''
      nomDossier.value = ''
      rccm.value = ''
      jourVirement.value = null
      email.value = ''
      telephone.value = ''
      nomContact.value = ''
      pays.value = "Côte d'Ivoire"
      
      // Refresh list
      await fetchDossiers()
    }
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  if (!user.value) {
    navigateTo('/login')
  } else {
    fetchDossiers()
  }
})
</script>

<template>
  <div class="space-y-6">
    
    <!-- En-tête de page -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b-2 border-navy-900 pb-4">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 tracking-tight">Tableau de bord des Dossiers</h1>
        <p class="text-sm text-slate-500 mt-1">Sélectionnez ou créez un dossier client pour commencer la saisie de paie.</p>
      </div>
      
      <button 
        @click="modalOpen = true"
        class="mt-4 sm:mt-0 flex items-center justify-center px-4 py-2 border-2 border-green-700 text-xs font-bold uppercase tracking-wider bg-green-600 hover:bg-green-700 text-white transition-all space-x-2 shadow-flat cursor-pointer shadow-flat-hover shadow-flat-active"
      >
        <UIcon name="i-lucide-folder-plus" class="w-4 h-4" />
        <span>Nouveau Dossier</span>
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4">
      <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
      <span class="text-sm text-slate-500 font-medium">Chargement des dossiers clients...</span>
    </div>

    <!-- Empty State -->
    <div v-else-if="dossiers.length === 0" class="bg-white border-2 border-dashed border-slate-350 p-12 text-center max-w-xl mx-auto space-y-4 shadow-flat">
      <div class="w-12 h-12 bg-navy-50 flex items-center justify-center text-navy-700 mx-auto">
        <UIcon name="i-lucide-folder-open" class="w-6 h-6" />
      </div>
      <h3 class="font-bold text-navy-900 text-lg">Aucun dossier d'entreprise</h3>
      <p class="text-sm text-slate-500">
        Vous n'avez pas encore configuré de dossier client. Commencez par créer votre premier dossier pour ajouter vos établissements et salariés.
      </p>
      <button 
        @click="modalOpen = true"
        class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-bold text-xs uppercase tracking-wider transition-colors inline-flex items-center space-x-2 shadow-flat"
      >
        <UIcon name="i-lucide-folder-plus" class="w-4 h-4" />
        <span>Créer un dossier</span>
      </button>
    </div>

    <!-- Grille des dossiers -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      <NuxtLink 
        v-for="dossier in dossiers" 
        :key="dossier.id" 
        :to="`/dossiers/${dossier.id}`"
        class="bg-white border-2 border-slate-200 p-6 shadow-flat hover:shadow-flat-hover hover:border-navy-700 transition-all duration-150 flex flex-col justify-between group cursor-pointer border-t-4 border-t-navy-900 hover:border-t-navy-700"
      >
        <div class="space-y-4">
          <!-- Top Row: Icon and Code badge -->
          <div class="flex items-center justify-between">
            <div class="w-10 h-10 bg-navy-50 text-navy-700 flex items-center justify-center group-hover:bg-navy-800 group-hover:text-white transition-colors duration-150 border border-navy-100">
              <UIcon name="i-lucide-folder" class="w-5 h-5" />
            </div>
            <span class="text-xs px-2 py-0.5 font-mono font-bold bg-navy-50 text-navy-700 group-hover:bg-navy-100 group-hover:text-navy-900 transition-colors border border-navy-200">
              {{ dossier.code }}
            </span>
          </div>

          <!-- Mid: Title & RCCM -->
          <div>
            <h2 class="font-bold text-navy-900 group-hover:text-navy-700 text-lg transition-colors leading-tight">
              {{ dossier.nom_dossier }}
            </h2>
            <p v-if="dossier.rccm" class="text-xs text-slate-500 mt-1 font-mono">
              RCCM : {{ dossier.rccm }}
            </p>
            <p v-else class="text-xs text-slate-400 mt-1 italic">
              Aucun RCCM renseigné
            </p>
          </div>
        </div>

        <!-- Bottom Row: Contact info & Year -->
        <div class="border-t border-slate-100 mt-4 pt-3 flex items-center justify-between text-xs text-slate-500">
          <span class="truncate max-w-[150px]">
            <UIcon name="i-lucide-user" class="w-3.5 h-3.5 inline mr-1 text-slate-400" />
            {{ dossier.nom_contact || 'Non spécifié' }}
          </span>
          <span class="bg-navy-50 px-1.5 py-0.5 font-semibold text-navy-700 border border-navy-200">
            Exercice {{ dossier.annee || new Date().getFullYear() }}
          </span>
        </div>
      </NuxtLink>
    </div>

    <!-- Dialog / Modal: Create Dossier Form -->
    <UModal v-model:open="modalOpen" title="Créer un nouveau Dossier Client">
      <template #content>
        <div class="p-6 space-y-4">
          <h2 class="text-lg font-bold text-navy-900 border-b border-slate-100 pb-2">Nouveau Dossier d'Entreprise</h2>
          
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code Dossier <span class="text-red-500">*</span></label>
              <input 
                v-model="code" 
                type="text" 
                placeholder="Ex: ACME" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Exercice Annuel</label>
              <input 
                v-model="annee" 
                type="text" 
                placeholder="Ex: 2026" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
              />
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom de l'Entreprise <span class="text-red-500">*</span></label>
            <input 
              v-model="nomDossier" 
              type="text" 
              placeholder="Ex: ACME SARL" 
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">RCCM</label>
              <input 
                v-model="rccm" 
                type="text" 
                placeholder="Ex : CI-ABJ-03-2024-B12-01234" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Jour de virement</label>
              <select
                v-model.number="jourVirement"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
              >
                <option :value="null">-- Non précisé --</option>
                <option v-for="jour in 31" :key="jour" :value="jour">{{ jour }}</option>
              </select>
              <p class="mt-1 text-[11px] text-slate-400">Paiement des salaires, chaque mois.</p>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Pays de Référence</label>
              <input 
                v-model="pays" 
                type="text" 
                placeholder="Ex: Côte d'Ivoire" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom Contact</label>
              <input 
                v-model="nomContact" 
                type="text" 
                placeholder="Ex: M. Dupont" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Qualité du contact</label>
              <select 
                v-model="qualite" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm bg-white"
              >
                <option :value="1">1 - Gestionnaire Principal</option>
                <option :value="2">2 - Mandataire</option>
                <option :value="3">3 - Cabinet Comptable</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Email Contact</label>
              <input 
                v-model="email" 
                type="email" 
                placeholder="contact@acme.com" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Téléphone</label>
              <input 
                v-model="telephone" 
                type="text" 
                placeholder="Ex: 0102030405" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
              />
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-100">
            <button 
              type="button" 
              @click="modalOpen = false"
              class="px-4 py-2 border border-slate-200 text-sm font-semibold rounded-lg hover:bg-slate-50 text-slate-700 transition-colors"
            >
              Annuler
            </button>
            <button 
              type="button" 
              @click="handleCreateDossier"
              class="px-4 py-2 text-sm font-semibold bg-green-600 hover:bg-green-700 text-white rounded-lg shadow transition-colors"
            >
              Créer le dossier
            </button>
          </div>
        </div>
      </template>
    </UModal>

  </div>
</template>
