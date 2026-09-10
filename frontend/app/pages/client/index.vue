<script setup>
const { user } = useSupabase()
const { get, post } = useApi()
const toast = useToast()

const loading = ref(true)
const dossier = ref(null)
const periodeStatut = ref(null)
const stats = ref({
  salariesCount: 0,
  hsCount: 0,
  absCount: 0,
  primesCount: 0,
  bulletinsCount: 0,
  reclamationsCount: 0
})

const selectedMois = ref(new Date().getMonth() + 1)
const selectedAnnee = ref(String(new Date().getFullYear()))

const monthNames = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
]

const currentPeriodLabel = computed(() => {
  return `${monthNames[selectedMois.value - 1]} ${selectedAnnee.value}`
})

const fetchClientDashboard = async () => {
  loading.value = true
  try {
    // 1. Récupérer les dossiers accessibles
    const dossiers = await get('/dossiers')
    if (dossiers && dossiers.length > 0) {
      // Si l'utilisateur est client rattaché à un dossier précis
      const targetId = user.value?.dossier_id || dossiers[0].id
      dossier.value = dossiers.find(d => d.id === targetId) || dossiers[0]
    }

    if (dossier.value) {
      // 2. Statut de la période
      try {
        periodeStatut.value = await get(`/dossiers/${dossier.value.id}/periodes/${selectedAnnee.value}/${selectedMois.value}/statut`)
      } catch (e) {
        periodeStatut.value = { statut: 'saisie_en_cours' }
      }

      // 3. Salariés et variables
      const varsRows = await get(`/dossiers/${dossier.value.id}/variables-mensuelles?mois=${selectedMois.value}&annee=${selectedAnnee.value}`)
      stats.value.salariesCount = varsRows.length
      stats.value.hsCount = varsRows.reduce((acc, r) => acc + (r.heures_supplementaires?.length || 0), 0)
      stats.value.absCount = varsRows.reduce((acc, r) => acc + (r.absences?.length || 0), 0)
      stats.value.primesCount = varsRows.reduce((acc, r) => acc + (r.primes?.length || 0), 0)
      stats.value.bulletinsCount = varsRows.filter(r => r.has_bulletin).length

      // 4. Réclamations du dossier
      try {
        const claims = await get('/reclamations')
        stats.value.reclamationsCount = claims ? claims.filter(c => c.statut === 'en_attente').length : 0
      } catch (e) {
        stats.value.reclamationsCount = 0
      }
    }
  } catch (e) {
    console.error("Erreur chargement dashboard client:", e)
    toast.add({ title: "Erreur", description: "Impossible de charger les données de l'entreprise.", color: "danger" })
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchClientDashboard()
})

const getStatusBadge = (statut) => {
  switch (statut) {
    case 'transmis':
      return { label: 'Transmis au cabinet (Prêt pour calcul)', color: 'warning', icon: 'i-lucide-send' }
    case 'calcule':
      return { label: 'Bulletins calculés par le cabinet', color: 'success', icon: 'i-lucide-check-circle-2' }
    case 'valide':
      return { label: 'Période validée & clôturée', color: 'success', icon: 'i-lucide-lock' }
    default:
      return { label: 'Saisie des variables en cours', color: 'info', icon: 'i-lucide-edit-3' }
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- En-tête de bienvenue entreprise -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div class="flex items-start gap-4">
        <div class="w-14 h-14 rounded-xl bg-green-50 border border-green-200 flex items-center justify-center text-green-700 font-black text-2xl shadow-xs shrink-0">
          {{ dossier?.nom_dossier ? dossier.nom_dossier.charAt(0).toUpperCase() : 'E' }}
        </div>
        <div>
          <div class="flex items-center gap-2.5 flex-wrap">
            <h1 class="text-xl font-bold text-slate-900 tracking-tight">
              {{ dossier?.nom_dossier || 'Mon Entreprise' }}
            </h1>
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-green-100 text-green-800 border border-green-200">
              Espace Entreprise
            </span>
            <span v-if="dossier?.code" class="text-xs text-slate-500 font-mono bg-slate-100 px-2 py-0.5 rounded border border-slate-250">
              Code: {{ dossier.code }}
            </span>
          </div>
          <p class="text-sm text-slate-500 mt-1">
            Gestion des variables de paie et suivi mensuel des bulletins en relation avec votre cabinet.
          </p>
        </div>
      </div>

      <!-- Sélecteur rapide de période active -->
      <div class="flex items-center gap-2 bg-slate-50 p-2 rounded-lg border border-slate-200 shrink-0">
        <UIcon name="i-lucide-calendar" class="w-4 h-4 text-slate-500 ml-1" />
        <span class="text-xs font-bold text-slate-700">Période :</span>
        <span class="text-xs font-black text-green-700 bg-white px-2.5 py-1 rounded shadow-2xs border border-slate-200">
          {{ currentPeriodLabel }}
        </span>
      </div>
    </div>

    <!-- Stepper / État d'avancement du cycle de paie -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2">
          <UIcon name="i-lucide-activity" class="w-5 h-5 text-green-600" />
          <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wide">
            Avancement de la paie • {{ currentPeriodLabel }}
          </h2>
        </div>
        <UBadge 
          :color="getStatusBadge(periodeStatut?.statut).color"
          variant="subtle"
          size="md"
          class="font-semibold"
        >
          <UIcon :name="getStatusBadge(periodeStatut?.statut).icon" class="w-4 h-4 mr-1.5" />
          {{ getStatusBadge(periodeStatut?.statut).label }}
        </UBadge>
      </div>

      <!-- Étapes graphiques -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
        <!-- Étape 1 -->
        <div class="p-4 rounded-lg border transition-all" :class="[
          periodeStatut?.statut === 'saisie_en_cours' 
            ? 'bg-green-50/70 border-green-300 ring-2 ring-green-500/20' 
            : 'bg-slate-50 border-slate-200'
        ]">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold" :class="[
              periodeStatut?.statut === 'saisie_en_cours' ? 'bg-green-600 text-white' : 'bg-slate-200 text-slate-700'
            ]">1</div>
            <span class="text-xs font-bold uppercase tracking-wider text-slate-700">Saisie Client</span>
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">
            Entrez les heures sup, congés, absences et primes du mois dans la grille.
          </p>
        </div>

        <!-- Étape 2 -->
        <div class="p-4 rounded-lg border transition-all" :class="[
          periodeStatut?.statut === 'transmis' 
            ? 'bg-amber-50/70 border-amber-300 ring-2 ring-amber-500/20' 
            : (['calcule', 'valide'].includes(periodeStatut?.statut) ? 'bg-slate-50 border-slate-200' : 'bg-slate-50/50 border-slate-200 opacity-80')
        ]">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold" :class="[
              periodeStatut?.statut === 'transmis' ? 'bg-amber-500 text-white' : (['calcule', 'valide'].includes(periodeStatut?.statut) ? 'bg-green-600 text-white' : 'bg-slate-200 text-slate-700')
            ]">2</div>
            <span class="text-xs font-bold uppercase tracking-wider text-slate-700">Transmission</span>
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">
            Transmettez la grille validée à votre cabinet pour le calcul officiel.
          </p>
        </div>

        <!-- Étape 3 -->
        <div class="p-4 rounded-lg border transition-all" :class="[
          periodeStatut?.statut === 'calcule' 
            ? 'bg-green-50/70 border-green-300 ring-2 ring-green-500/20' 
            : 'bg-slate-50/50 border-slate-200 opacity-80'
        ]">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold" :class="[
              periodeStatut?.statut === 'calcule' ? 'bg-green-600 text-white' : (periodeStatut?.statut === 'valide' ? 'bg-green-600 text-white' : 'bg-slate-200 text-slate-700')
            ]">3</div>
            <span class="text-xs font-bold uppercase tracking-wider text-slate-700">Calcul Cabinet</span>
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">
            Le gestionnaire applique les règles légales et calcule les bulletins.
          </p>
        </div>

        <!-- Étape 4 -->
        <div class="p-4 rounded-lg border transition-all" :class="[
          periodeStatut?.statut === 'valide' 
            ? 'bg-green-50/70 border-green-300 ring-2 ring-green-500/20' 
            : 'bg-slate-50/50 border-slate-200 opacity-80'
        ]">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold" :class="[
              periodeStatut?.statut === 'valide' ? 'bg-green-600 text-white' : 'bg-slate-200 text-slate-700'
            ]">4</div>
            <span class="text-xs font-bold uppercase tracking-wider text-slate-700">Mise à disposition</span>
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">
            Bulletins disponibles pour l'entreprise et téléchargeables par les salariés.
          </p>
        </div>
      </div>
    </div>

    <!-- Cartes statistiques clés -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      <!-- Effectif -->
      <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex items-center justify-between">
        <div>
          <p class="text-xs font-bold uppercase tracking-wider text-slate-500">Effectif Salariés</p>
          <p class="text-2xl font-black text-slate-900 mt-1">{{ stats.salariesCount }}</p>
          <p class="text-xs text-slate-500 mt-0.5">Contrats actifs dans l'entreprise</p>
        </div>
        <div class="w-12 h-12 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
          <UIcon name="i-lucide-users" class="w-6 h-6" />
        </div>
      </div>

      <!-- Heures Sup & Absences -->
      <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex items-center justify-between">
        <div>
          <p class="text-xs font-bold uppercase tracking-wider text-slate-500">Variables Saisies</p>
          <div class="flex items-baseline gap-2 mt-1">
            <span class="text-2xl font-black text-slate-900">{{ stats.hsCount + stats.absCount }}</span>
            <span class="text-xs text-slate-500 font-medium">({{ stats.hsCount }} HS, {{ stats.absCount }} Abs)</span>
          </div>
          <p class="text-xs text-slate-500 mt-0.5">Pour {{ currentPeriodLabel }}</p>
        </div>
        <div class="w-12 h-12 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
          <UIcon name="i-lucide-clock" class="w-6 h-6" />
        </div>
      </div>

      <!-- Primes -->
      <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex items-center justify-between">
        <div>
          <p class="text-xs font-bold uppercase tracking-wider text-slate-500">Primes Déclarées</p>
          <p class="text-2xl font-black text-slate-900 mt-1">{{ stats.primesCount }}</p>
          <p class="text-xs text-slate-500 mt-0.5">Primes et gratifications du mois</p>
        </div>
        <div class="w-12 h-12 rounded-xl bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-600">
          <UIcon name="i-lucide-award" class="w-6 h-6" />
        </div>
      </div>

      <!-- Bulletins Calculés -->
      <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex items-center justify-between">
        <div>
          <p class="text-xs font-bold uppercase tracking-wider text-slate-500">Bulletins Générés</p>
          <div class="flex items-baseline gap-2 mt-1">
            <span class="text-2xl font-black text-slate-900">{{ stats.bulletinsCount }}</span>
            <span class="text-xs text-slate-500 font-medium">/ {{ stats.salariesCount }}</span>
          </div>
          <p class="text-xs text-slate-500 mt-0.5">Calculés pour ce mois</p>
        </div>
        <div class="w-12 h-12 rounded-xl bg-green-50 border border-green-200 flex items-center justify-center text-green-600">
          <UIcon name="i-lucide-file-check" class="w-6 h-6" />
        </div>
      </div>
    </div>

    <!-- Actions rapides -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
      <!-- Action 1 : Saisie des variables -->
      <NuxtLink to="/client/variables" class="group bg-white border border-slate-200 hover:border-green-500 rounded-xl p-6 shadow-xs hover:shadow-md transition-all flex flex-col justify-between">
        <div>
          <div class="w-10 h-10 rounded-lg bg-green-100 text-green-700 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <UIcon name="i-lucide-edit-3" class="w-5 h-5" />
          </div>
          <h3 class="text-base font-bold text-slate-900 group-hover:text-green-700 transition-colors">
            Saisir les variables du mois
          </h3>
          <p class="text-xs text-slate-500 mt-1 leading-relaxed">
            Heures supplémentaires (HS15, HS50...), congés, absences, primes et acomptes via grille rapide ou matrice Excel.
          </p>
        </div>
        <div class="mt-5 flex items-center text-xs font-bold text-green-700 group-hover:translate-x-1 transition-transform">
          Ouvrir la grille de saisie
          <UIcon name="i-lucide-arrow-right" class="w-4 h-4 ml-1" />
        </div>
      </NuxtLink>

      <!-- Action 2 : Bulletins de paie -->
      <NuxtLink to="/client/bulletins" class="group bg-white border border-slate-200 hover:border-blue-500 rounded-xl p-6 shadow-xs hover:shadow-md transition-all flex flex-col justify-between">
        <div>
          <div class="w-10 h-10 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <UIcon name="i-lucide-file-text" class="w-5 h-5" />
          </div>
          <h3 class="text-base font-bold text-slate-900 group-hover:text-blue-700 transition-colors">
            Consulter les bulletins
          </h3>
          <p class="text-xs text-slate-500 mt-1 leading-relaxed">
            Visualisez et téléchargez les bulletins de paie calculés par le cabinet, ainsi que le récapitulatif salarial.
          </p>
        </div>
        <div class="mt-5 flex items-center text-xs font-bold text-blue-700 group-hover:translate-x-1 transition-transform">
          Accéder aux bulletins
          <UIcon name="i-lucide-arrow-right" class="w-4 h-4 ml-1" />
        </div>
      </NuxtLink>

      <!-- Action 3 : Salariés & Équipes -->
      <NuxtLink to="/client/salaries" class="group bg-white border border-slate-200 hover:border-purple-500 rounded-xl p-6 shadow-xs hover:shadow-md transition-all flex flex-col justify-between">
        <div>
          <div class="w-10 h-10 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <UIcon name="i-lucide-users" class="w-5 h-5" />
          </div>
          <h3 class="text-base font-bold text-slate-900 group-hover:text-purple-700 transition-colors">
            Effectif & Personnel
          </h3>
          <p class="text-xs text-slate-500 mt-1 leading-relaxed">
            Consultez la liste des salariés de votre entreprise, leurs postes, dates d'embauche et contrats en cours.
          </p>
        </div>
        <div class="mt-5 flex items-center text-xs font-bold text-purple-700 group-hover:translate-x-1 transition-transform">
          Voir le personnel
          <UIcon name="i-lucide-arrow-right" class="w-4 h-4 ml-1" />
        </div>
      </NuxtLink>
    </div>
  </div>
</template>
