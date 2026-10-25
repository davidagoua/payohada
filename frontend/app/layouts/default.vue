<script setup>
const { user, logout } = useSupabase()
const { openModal: openPasswordModal, checkAndSuggest: checkPasswordSuggestion } = useChangePasswordModal()
const { get } = useApi()
const route = useRoute()
const isAdmin = computed(() => !!user.value?.is_admin)

// Suggestion automatique du modal de mot de passe par défaut pour client / salarié
watch(() => user.value, (u) => {
  if (u) {
    checkPasswordSuggestion(u)
  }
}, { immediate: true })

const isClientRoute = computed(() => route.path.startsWith('/client'))
const isSalarieRoute = computed(() => route.path.startsWith('/salaries'))
const userRole = computed(() => user.value?.role || (user.value?.salarie_id ? 'salarie' : 'cabinet'))

const activeSpace = computed(() => {
  if (isClientRoute.value || userRole.value === 'client') return 'client'
  if (isSalarieRoute.value || userRole.value === 'salarie') return 'salarie'
  return 'cabinet'
})

// State for active company/dossier context
const currentDossier = useState('current-dossier', () => null)
const currentEtablissement = useState('current-etablissement', () => null)

// Parse route to see if an establishment or dossier is selected
const routeInfo = computed(() => {
  const segments = route.path.split('/').filter(Boolean)
  let dossierId = null
  let etabId = null

  const dossierIdx = segments.indexOf('dossiers')
  if (dossierIdx !== -1 && segments[dossierIdx + 1] && segments[dossierIdx + 1] !== 'new') {
    dossierId = segments[dossierIdx + 1]
  }

  const etabIdx = segments.indexOf('etablissements')
  if (etabIdx !== -1 && segments[etabIdx + 1] && segments[etabIdx + 1] !== 'new') {
    etabId = segments[etabIdx + 1]
  }

  const isEtab = !!etabId

  return {
    isEtabSelected: isEtab,
    dossierId,
    etabId
  }
})

// Automatically fetch dossier / establishment context based on route
watch(() => routeInfo.value, async (newVal) => {
  if (!newVal.dossierId) {
    currentDossier.value = null
    currentEtablissement.value = null
    return
  }

  // Fetch/Set Dossier if missing or changed
  if (!currentDossier.value || String(currentDossier.value.id) !== String(newVal.dossierId)) {
    try {
      currentDossier.value = await get(`/dossiers/${newVal.dossierId}`)
    } catch (e) {
      console.error('Error fetching dossier in layout:', e)
      currentDossier.value = null
    }
  }

  // Fetch/Set Etablissement if missing or changed
  if (newVal.etabId) {
    if (!currentEtablissement.value || String(currentEtablissement.value.id) !== String(newVal.etabId)) {
      try {
        currentEtablissement.value = await get(`/etablissements/${newVal.etabId}`)
      } catch (e) {
        console.error('Error fetching establishment in layout:', e)
        currentEtablissement.value = null
      }
    }
  } else {
    currentEtablissement.value = null
  }
}, { immediate: true })

const contextName = computed(() => {
  if (activeSpace.value === 'client') {
    return user.value?.nom_dossier || currentDossier.value?.nom_dossier || 'Espace Entreprise'
  }
  if (activeSpace.value === 'salarie') {
    return 'Espace Salarié'
  }
  if (currentEtablissement.value) {
    return currentEtablissement.value.raison_sociale
  }
  if (currentDossier.value) {
    return currentDossier.value.nom_dossier
  }
  return 'Espace Cabinet'
})

// Reactive breadcrumbs computed from route meta or path segments
const breadcrumbs = computed(() => {
  const paths = route.path.split('/').filter(Boolean)
  const items = [{ label: 'Accueil', to: '/dossiers', icon: 'i-lucide-home' }]

  if (paths.length > 0) {
    if (paths[0] === 'dossiers') {
      if (paths[1] && paths[1] !== 'new') {
        items.push({
          label: currentDossier.value ? currentDossier.value.nom_dossier : 'Dossier',
          to: `/dossiers/${paths[1]}`
        })

        if (paths[2] === 'etablissements' && paths[3]) {
          const isNewEtab = paths[3] === 'new'
          items.push({
            label: isNewEtab ? 'Nouvel Établissement' : 'Établissement',
            to: `/dossiers/${paths[1]}/etablissements/${paths[3]}`
          })

          if (!isNewEtab && paths[4] === 'salaries' && paths[5]) {
            const isNewSal = paths[5] === 'new'
            items.push({
              label: isNewSal ? 'Nouvel Employé' : 'Salarié',
              to: `/dossiers/${paths[1]}/etablissements/${paths[3]}/salaries/${paths[5]}`
            })

            if (!isNewSal && paths[6] === 'contrats' && paths[7]) {
              const isNewContrat = paths[7] === 'new'
              items.push({
                label: isNewContrat ? 'Nouveau Contrat' : 'Contrat',
                to: `/dossiers/${paths[1]}/etablissements/${paths[3]}/salaries/${paths[5]}/contrats/${paths[7]}`
              })
            }
          }
        }
      }
    }
  }
  return items
})

const handleLogout = async () => {
  await logout()
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-800">
    <!-- Liseré supérieur : signature bicolore de la marque (navy → vert) -->
    <div class="brand-accent-bar" />

    <!-- Barre de navigation principale — l'encre navy structure l'application -->
    <header class="bg-navy-900 shadow-flat sticky top-0 z-50">
      <!-- Top Row: Logo & Profile -->
      <div class="border-b border-white/10">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <!-- Left: Logo & Breadcrumbs -->
          <div class="flex items-center space-x-6">
            <NuxtLink
              to="/dossiers"
              class="flex items-center space-x-3 shrink-0 group"
            >
              <!-- Official Payohada Logo (variante claire pour fond navy) -->
              <img
                src="/payohada-logo-light.png"
                alt="payohada"
                class="h-8 w-auto object-contain transition-transform group-hover:scale-105"
              >
              <span
                v-if="contextName"
                class="text-[9px] px-2 py-0.5 bg-white/10 text-white/90 font-bold border border-white/20 tracking-wider uppercase ml-1"
              >
                {{ contextName }}
              </span>
            </NuxtLink>

            <!-- Breadcrumbs (hidden on mobile) -->
            <div class="hidden md:flex items-center space-x-2 text-sm text-slate-300">
              <span class="text-white/25">|</span>
              <div class="flex items-center space-x-2">
                <template
                  v-for="(item, index) in breadcrumbs"
                  :key="index"
                >
                  <span
                    v-if="index > 0"
                    class="text-white/25"
                  >/</span>
                  <NuxtLink
                    :to="item.to"
                    class="hover:text-white font-medium transition-colors duration-150 flex items-center"
                  >
                    <UIcon
                      v-if="item.icon"
                      :name="item.icon"
                      class="w-4 h-4 mr-1 text-white/40"
                    />
                    {{ item.label }}
                  </NuxtLink>
                </template>
              </div>
            </div>
          </div>

          <!-- Right: Actions & Profile -->
          <div class="flex items-center space-x-3">
            <span
                v-if="user.cabinet_nom"
                class="hidden sm:inline-block text-[11px] bg-white/10 text-white/90 font-semibold px-2 py-0.5 border border-white/20 max-w-[140px] truncate"
                :title="user.cabinet_nom"
              >
                🏢 {{ user.cabinet_nom }}
            </span>

            <div
              v-if="user"
              class="flex items-center space-x-3"
            >
              <div class="text-right hidden sm:block">
                <div class="flex items-center justify-end gap-1.5">
                  
                  <p class="text-sm font-semibold text-white">
                    {{ user.user_metadata?.first_name }} {{ user.user_metadata?.last_name }}
                  </p>
                </div>
                <p class="text-xs text-slate-400 truncate max-w-[180px]">
                  {{ user.email }}
                </p>
              </div>

              <!-- Profile Dropdown -->
              <UDropdownMenu
                :items="[[
                  {
                    label: 'Mon Profil',
                    icon: 'i-lucide-user'
                  },
                  {
                    label: 'Modifier le mot de passe',
                    icon: 'i-lucide-key',
                    onSelect: openPasswordModal
                  },
                  {
                    label: 'Se déconnecter',
                    icon: 'i-lucide-log-out',
                    class: 'text-red-600',
                    onSelect: handleLogout
                  }
                ]]"
              >
                <UButton
                  color="neutral"
                  variant="ghost"
                  class="rounded-full w-9 h-9 p-0 bg-green-500 text-navy-950 hover:bg-green-400 flex items-center justify-center font-bold"
                >
                  {{ user.email?.[0].toUpperCase() }}
                </UButton>
              </UDropdownMenu>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom Row: Navigation Menu Bar — navy plus clair que l'en-tête -->
      <div class="bg-navy-800">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-12 flex items-center justify-start overflow-x-auto no-scrollbar">
          <nav class="flex items-center space-x-1 h-12 shrink-0">
            <!-- 1. ESPACE SALARIÉ -->
            <template v-if="activeSpace === 'salarie'">
              <NuxtLink
                to="/salaries/bulletins"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                active-class="border-b-2! border-b-green-600! text-navy-900! bg-white! font-bold"
              >
                Mes Bulletins
              </NuxtLink>
              <NuxtLink
                to="/salaries/conges"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                active-class="border-b-2! border-b-green-600! text-navy-900! bg-white! font-bold"
              >
                Mes Congés
              </NuxtLink>
              <NuxtLink
                to="/salaries/acomptes"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                active-class="border-b-2! border-b-green-600! text-navy-900! bg-white! font-bold"
              >
                Mes Acomptes
              </NuxtLink>
            </template>

            <!-- 2. ESPACE CLIENT (ENTREPRISE) -->
            <template v-else-if="activeSpace === 'client'">
              <NuxtLink
                to="/client"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                exact-active-class="border-b-2! border-b-green-600! text-navy-900! bg-white! font-bold"
              >
                Tableau de bord
              </NuxtLink>
              <NuxtLink
                to="/client/variables"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                active-class="border-b-2! border-b-green-600! text-navy-900! bg-white! font-bold"
              >
                Saisie des Variables
              </NuxtLink>
              <NuxtLink
                to="/client/bulletins"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                active-class="border-b-2! border-b-green-600! text-navy-900! bg-white! font-bold"
              >
                Bulletins de Paie
              </NuxtLink>
              <NuxtLink
                to="/client/salaries"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                active-class="border-b-2! border-b-green-600! text-navy-900! bg-white! font-bold"
              >
                Personnel
              </NuxtLink>
              <NuxtLink
                to="/client/demandes"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                active-class="border-b-2! border-b-green-600! text-navy-900! bg-white! font-bold"
              >
                Demandes
              </NuxtLink>
              <NuxtLink
                to="/client/reclamations"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                active-class="border-b-2! border-b-green-600! text-navy-900! bg-white! font-bold"
              >
                Réclamations
              </NuxtLink>
            </template>

            <!-- 3. ESPACE CABINET -->
            <template v-else-if="!routeInfo.isEtabSelected">
              <NuxtLink
                to="/dossiers"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                active-class="border-b-2! border-b-green-600! text-navy-900! bg-white! font-bold"
              >
                Entreprises
              </NuxtLink>
              <NuxtLink
                to="/simulation"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                active-class="border-b-2! border-b-green-600! text-navy-900! bg-white! font-bold"
              >
                Simulateur de Paie
              </NuxtLink>
              <NuxtLink
                to="/admin/reclamations"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                active-class="border-b-2! border-b-green-600! text-navy-900! bg-white! font-bold"
              >
                Réclamations
              </NuxtLink>
              <NuxtLink
                v-if="isAdmin"
                to="/admin"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                active-class="border-b-2! border-b-green-600! text-navy-900! bg-white! font-bold"
              >
                Administration
              </NuxtLink>
            </template>

            <!-- If an establishment IS selected -->
            <template v-else>
              <NuxtLink
                :to="`/dossiers/${routeInfo.dossierId}/etablissements/${routeInfo.etabId}?tab=sals`"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 text-xs font-bold uppercase tracking-wider transition-all"
                :class="[
                  (!route.path.endsWith('/editions') && (!route.query.tab || route.query.tab === 'sals'))
                    ? 'border-b-green-600 text-navy-900 bg-white font-bold'
                    : 'border-transparent text-slate-300 hover:text-white hover:bg-white/5'
                ]"
              >
                Salariés
              </NuxtLink>
              <NuxtLink
                :to="`/dossiers/${routeInfo.dossierId}/etablissements/${routeInfo.etabId}?tab=contrats`"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 text-xs font-bold uppercase tracking-wider transition-all"
                :class="[
                  route.query.tab === 'contrats'
                    ? 'border-b-green-600 text-navy-900 bg-white font-bold'
                    : 'border-transparent text-slate-300 hover:text-white hover:bg-white/5'
                ]"
              >
                Contrats
              </NuxtLink>
              <NuxtLink
                :to="`/dossiers/${routeInfo.dossierId}/etablissements/${routeInfo.etabId}?tab=bulletins`"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 text-xs font-bold uppercase tracking-wider transition-all"
                :class="[
                  route.query.tab === 'bulletins'
                    ? 'border-b-green-600 text-navy-900 bg-white font-bold'
                    : 'border-transparent text-slate-300 hover:text-white hover:bg-white/5'
                ]"
              >
                Bulletins de Salaire
              </NuxtLink>
              <NuxtLink
                :to="`/dossiers/${routeInfo.dossierId}/etablissements/${routeInfo.etabId}?tab=infos`"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 text-xs font-bold uppercase tracking-wider transition-all"
                :class="[
                  route.query.tab === 'infos'
                    ? 'border-b-green-600 text-navy-900 bg-white font-bold'
                    : 'border-transparent text-slate-300 hover:text-white hover:bg-white/5'
                ]"
              >
                Information Générale
              </NuxtLink>
              <!-- Les états portent sur l'établissement : l'onglet suit le
                   même schéma que ses voisins, mais l'état actif se calcule sur
                   le chemin et non sur le paramètre « tab ». -->
              <NuxtLink
                :to="`/dossiers/${routeInfo.dossierId}/etablissements/${routeInfo.etabId}/editions`"
                class="px-4 py-3.5 whitespace-nowrap shrink-0 rounded-t-lg border-b-2 text-xs font-bold uppercase tracking-wider transition-all"
                :class="[
                  route.path.endsWith('/editions')
                    ? 'border-b-green-600 text-navy-900 bg-white font-bold'
                    : 'border-transparent text-slate-300 hover:text-white hover:bg-white/5'
                ]"
              >
                Éditions
              </NuxtLink>
            </template>
          </nav>
        </div>
      </div>
    </header>

    <!-- Main Workspace Container -->
    <main class="flex-grow max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
      <slot />
    </main>

    <!-- Pied de page : encre navy, filet vert de rappel -->
    <footer class="bg-navy-900 border-t-2 border-green-600 py-4 mt-auto">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center gap-2 text-xs text-slate-400">
        <p>payohada • © {{ new Date().getFullYear() }} — ERP Paie Solution</p>
        <p class="tracking-wide uppercase text-[10px] text-slate-400/80">
          La paie conforme pour l'Afrique de l'Ouest
        </p>
      </div>
    </footer>
  </div>
</template>
