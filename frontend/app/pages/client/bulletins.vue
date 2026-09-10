<script setup>
const { user } = useSupabase()
const { get } = useApi()
const toast = useToast()

const loading = ref(true)
const dossier = ref(null)
const bulletins = ref([])
const selectedMois = ref(new Date().getMonth() + 1)
const selectedAnnee = ref(String(new Date().getFullYear()))
const searchQuery = ref('')

const selectedBulletin = ref(null)
const previewModalOpen = ref(false)

const months = [
  { value: 1, label: 'Janvier' },
  { value: 2, label: 'Février' },
  { value: 3, label: 'Mars' },
  { value: 4, label: 'Avril' },
  { value: 5, label: 'Mai' },
  { value: 6, label: 'Juin' },
  { value: 7, label: 'Juillet' },
  { value: 8, label: 'Août' },
  { value: 9, label: 'Septembre' },
  { value: 10, label: 'Octobre' },
  { value: 11, label: 'Novembre' },
  { value: 12, label: 'Décembre' }
]

const years = [
  String(new Date().getFullYear() - 1),
  String(new Date().getFullYear()),
  String(new Date().getFullYear() + 1)
]

const fetchBulletins = async () => {
  loading.value = true
  try {
    const dossiers = await get('/dossiers')
    if (dossiers && dossiers.length > 0) {
      const targetId = user.value?.dossier_id || dossiers[0].id
      dossier.value = dossiers.find(d => d.id === targetId) || dossiers[0]
    }

    if (dossier.value) {
      bulletins.value = await get(
        `/dossiers/${dossier.value.id}/bulletins?mois=${selectedMois.value}&annee=${selectedAnnee.value}`
      )
    }
  } catch (e) {
    console.error("Erreur chargement bulletins entreprise:", e)
    toast.add({ title: "Erreur", description: "Impossible de charger les bulletins.", color: "danger" })
  } finally {
    loading.value = false
  }
}

watch([selectedMois, selectedAnnee], () => {
  fetchBulletins()
})

onMounted(() => {
  fetchBulletins()
})

const formatFCFA = (amount) => {
  if (amount === undefined || amount === null) return '0 FCFA'
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XOF', minimumFractionDigits: 0 })
    .format(amount)
    .replace('XOF', 'FCFA')
}

const filteredBulletins = computed(() => {
  if (!searchQuery.value) return bulletins.value
  const q = searchQuery.value.toLowerCase()
  return bulletins.value.filter(b => 
    (b.salarie_nom && b.salarie_nom.toLowerCase().includes(q)) ||
    (b.salarie_prenom && b.salarie_prenom.toLowerCase().includes(q)) ||
    (b.matricule && b.matricule.toLowerCase().includes(q))
  )
})

const totalBrut = computed(() => bulletins.value.reduce((acc, b) => acc + (b.salaire_brut || 0), 0))
const totalNet = computed(() => bulletins.value.reduce((acc, b) => acc + (b.net_a_payer || 0), 0))
const totalCharges = computed(() => bulletins.value.reduce((acc, b) => acc + (b.total_charges_patronales || 0), 0))

const handlePreview = (b) => {
  selectedBulletin.value = b
  previewModalOpen.value = true
}

const handlePrint = () => {
  window.print()
}
</script>

<template>
  <div class="space-y-6">
    <!-- En-tête -->
    <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <div class="flex items-center gap-2">
          <NuxtLink to="/client" class="text-xs text-slate-500 hover:text-green-600 font-semibold flex items-center gap-1">
            <UIcon name="i-lucide-arrow-left" class="w-3.5 h-3.5" />
            Tableau de bord
          </NuxtLink>
        </div>
        <h1 class="text-xl font-bold text-slate-900 mt-1">
          Bulletins de Paie de l'Entreprise
        </h1>
        <p class="text-xs text-slate-500 mt-0.5">
          Consultez et téléchargez les bulletins calculés par votre cabinet pour chacun de vos salariés.
        </p>
      </div>

      <!-- Filtres Période -->
      <div class="flex items-center gap-2 bg-slate-50 p-1.5 rounded-lg border border-slate-200">
        <label class="text-xs font-bold text-slate-600 ml-1">Mois :</label>
        <select 
          v-model="selectedMois" 
          class="bg-white border border-slate-250 rounded px-2.5 py-1 text-xs font-bold text-slate-800"
        >
          <option v-for="m in months" :key="m.value" :value="m.value">
            {{ m.label }}
          </option>
        </select>

        <label class="text-xs font-bold text-slate-600 ml-2">Année :</label>
        <select 
          v-model="selectedAnnee" 
          class="bg-white border border-slate-250 rounded px-2.5 py-1 text-xs font-bold text-slate-800"
        >
          <option v-for="y in years" :key="y" :value="y">
            {{ y }}
          </option>
        </select>
      </div>
    </div>

    <!-- Récapitulatif Masse Salariale du Mois -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-5">
      <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <p class="text-xs font-bold uppercase tracking-wider text-slate-500">Masse Brute Totale</p>
        <p class="text-2xl font-black text-slate-900 mt-1">{{ formatFCFA(totalBrut) }}</p>
        <p class="text-xs text-slate-500 mt-0.5">{{ bulletins.length }} bulletin(s) généré(s)</p>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <p class="text-xs font-bold uppercase tracking-wider text-slate-500">Total Net à Verser</p>
        <p class="text-2xl font-black text-green-700 mt-1">{{ formatFCFA(totalNet) }}</p>
        <p class="text-xs text-slate-500 mt-0.5">Virements salariaux nets</p>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <p class="text-xs font-bold uppercase tracking-wider text-slate-500">Cotisations Patronales</p>
        <p class="text-2xl font-black text-blue-700 mt-1">{{ formatFCFA(totalCharges) }}</p>
        <p class="text-xs text-slate-500 mt-0.5">CNPS, CMU, taxes patronales</p>
      </div>
    </div>

    <!-- Tableau des bulletins -->
    <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
      <div class="p-4 border-b border-slate-200 flex items-center justify-between gap-4">
        <div class="relative w-full max-w-sm">
          <UIcon name="i-lucide-search" class="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="Rechercher un bulletin..."
            class="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-800"
          />
        </div>
      </div>

      <div v-if="loading" class="p-12 text-center text-slate-400">
        <UIcon name="i-lucide-loader-2" class="w-8 h-8 mx-auto animate-spin mb-2" />
        <p class="text-xs">Chargement des bulletins...</p>
      </div>

      <div v-else-if="filteredBulletins.length === 0" class="p-12 text-center text-slate-500">
        <UIcon name="i-lucide-file-x" class="w-10 h-10 mx-auto text-slate-300 mb-2" />
        <p class="text-sm font-bold text-slate-800">Aucun bulletin calculé</p>
        <p class="text-xs text-slate-500 mt-1">
          Les bulletins de cette période n'ont pas encore été calculés par le cabinet. Assurez-vous d'avoir transmis vos variables.
        </p>
        <NuxtLink to="/client/variables" class="inline-flex items-center gap-1 mt-4 text-xs font-bold text-green-700 hover:underline">
          <UIcon name="i-lucide-edit-3" class="w-4 h-4" />
          Accéder à la saisie des variables
        </NuxtLink>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 text-left">
          <thead class="bg-slate-50 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
            <tr>
              <th scope="col" class="px-4 py-3">Salarié</th>
              <th scope="col" class="px-4 py-3">Brut</th>
              <th scope="col" class="px-4 py-3">Charges Salariales</th>
              <th scope="col" class="px-4 py-3">Charges Patronales</th>
              <th scope="col" class="px-4 py-3">Net à Payer</th>
              <th scope="col" class="px-4 py-3 text-center">Statut</th>
              <th scope="col" class="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-150 text-xs">
            <tr v-for="b in filteredBulletins" :key="b.id" class="hover:bg-slate-50/70 transition-colors">
              <td class="px-4 py-3.5">
                <div class="font-bold text-slate-900">
                  {{ b.salarie_nom }} {{ b.salarie_prenom }}
                </div>
                <div class="text-[11px] text-slate-500 font-mono">
                  Matricule: {{ b.matricule || `EMP-${b.contrat_id}` }}
                </div>
              </td>
              <td class="px-4 py-3.5 font-semibold text-slate-800">
                {{ formatFCFA(b.salaire_brut) }}
              </td>
              <td class="px-4 py-3.5 text-slate-600">
                {{ formatFCFA(b.total_retenues) }}
              </td>
              <td class="px-4 py-3.5 text-slate-600">
                {{ formatFCFA(b.total_charges_patronales) }}
              </td>
              <td class="px-4 py-3.5 font-black text-green-700 text-sm">
                {{ formatFCFA(b.net_a_payer) }}
              </td>
              <td class="px-4 py-3.5 text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold" :class="[
                  b.statut === 'valide' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'
                ]">
                  {{ b.statut === 'valide' ? 'Validé' : 'Brouillon' }}
                </span>
              </td>
              <td class="px-4 py-3.5 text-right">
                <UButton 
                  color="neutral" 
                  variant="ghost" 
                  size="xs"
                  @click="handlePreview(b)"
                >
                  <UIcon name="i-lucide-eye" class="w-4 h-4 mr-1 text-slate-500" />
                  Visualiser
                </UButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal Visualisation Bulletin -->
    <UModal v-model:open="previewModalOpen" :title="`Bulletin de Paie • ${selectedBulletin?.salarie_nom || ''} ${selectedBulletin?.salarie_prenom || ''}`">
      <template #body>
        <div v-if="selectedBulletin" class="space-y-4 text-xs">
          <!-- Infos entête -->
          <div class="grid grid-cols-2 gap-4 bg-slate-50 p-4 rounded-lg border border-slate-200">
            <div>
              <p class="font-bold text-slate-900">{{ selectedBulletin.salarie_nom }} {{ selectedBulletin.salarie_prenom }}</p>
              <p class="text-slate-500">Matricule: {{ selectedBulletin.matricule }}</p>
              <p class="text-slate-500">Période: {{ selectedBulletin.mois }}/{{ selectedBulletin.annee }}</p>
            </div>
            <div class="text-right">
              <p class="text-slate-500">Net à payer :</p>
              <p class="text-xl font-black text-green-700">{{ formatFCFA(selectedBulletin.net_a_payer) }}</p>
            </div>
          </div>

          <!-- Lignes du bulletin -->
          <div class="border border-slate-200 rounded-lg overflow-hidden">
            <table class="min-w-full divide-y divide-slate-200 text-left">
              <thead class="bg-slate-100 text-[10px] font-bold uppercase text-slate-600">
                <tr>
                  <th class="px-3 py-2">Code</th>
                  <th class="px-3 py-2">Libellé</th>
                  <th class="px-3 py-2 text-right">Gain</th>
                  <th class="px-3 py-2 text-right">Retenue</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-150 text-[11px]">
                <tr v-for="l in selectedBulletin.lignes" :key="l.id">
                  <td class="px-3 py-1.5 font-mono text-slate-500">{{ l.code }}</td>
                  <td class="px-3 py-1.5 font-medium text-slate-800">{{ l.libelle }}</td>
                  <td class="px-3 py-1.5 text-right font-medium text-slate-900">
                    {{ l.sens === 'Gain' ? formatFCFA(l.montant_s) : '-' }}
                  </td>
                  <td class="px-3 py-1.5 text-right font-medium text-red-700">
                    {{ l.sens === 'Retenue' ? formatFCFA(l.montant_cs || l.montant_s) : '-' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
      <template #footer>
        <div class="flex justify-between w-full">
          <UButton color="neutral" variant="outline" size="sm" @click="handlePrint">
            <UIcon name="i-lucide-printer" class="w-4 h-4 mr-1" />
            Imprimer
          </UButton>
          <UButton color="neutral" variant="ghost" size="sm" @click="previewModalOpen = false">
            Fermer
          </UButton>
        </div>
      </template>
    </UModal>
  </div>
</template>
