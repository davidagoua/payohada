<script setup>
const { user, logout, isMock } = useSupabase()
const { get } = useApi()
const route = useRoute()
const isAdmin = ref(false)

watch(user, async (newUser) => {
  if (newUser) {
    try {
      const profile = await get('/auth/me')
      isAdmin.value = !!profile?.is_admin
    } catch (e) {
      isAdmin.value = false
    }
  } else {
    isAdmin.value = false
  }
}, { immediate: true })

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
      console.error("Error fetching dossier in layout:", e)
      currentDossier.value = null
    }
  }

  // Fetch/Set Etablissement if missing or changed
  if (newVal.etabId) {
    if (!currentEtablissement.value || String(currentEtablissement.value.id) !== String(newVal.etabId)) {
      try {
        currentEtablissement.value = await get(`/etablissements/${newVal.etabId}`)
      } catch (e) {
        console.error("Error fetching establishment in layout:", e)
        currentEtablissement.value = null
      }
    }
  } else {
    currentEtablissement.value = null
  }
}, { immediate: true })

const contextName = computed(() => {
  if (currentEtablissement.value) {
    return currentEtablissement.value.raison_sociale
  }
  if (currentDossier.value) {
    return currentDossier.value.nom_dossier
  }
  return ''
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
    <!-- SAP Top Line Accent (Green) -->
    <div class="h-1 bg-green-600 w-full" />

    <!-- SAP Fiori Shell Bar -->
    <header class="bg-white border-b-2 border-slate-200 shadow-flat sticky top-0 z-50">
      
      <!-- Top Row: Logo & Profile -->
      <div class="border-b border-slate-150">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          
          <!-- Left: Logo & Breadcrumbs -->
          <div class="flex items-center space-x-6">
            <NuxtLink to="/dossiers" class="flex items-center space-x-2 shrink-0">
              <!-- Corporate Square Logo -->
              <div class="w-8 h-8 bg-green-600 flex items-center justify-center text-white font-black text-lg border border-green-700 shadow-flat">
                P
              </div>
              <span class="text-xl font-bold tracking-tight text-slate-900 uppercase">
                payohada
              </span>
              <span v-if="contextName" class="text-[9px] px-2 py-0.5 bg-slate-100 text-slate-600 font-bold border border-slate-350 tracking-wider uppercase">
                {{ contextName }}
              </span>
            </NuxtLink>

            <!-- Breadcrumbs (hidden on mobile) -->
            <div class="hidden md:flex items-center space-x-2 text-sm text-slate-500">
              <span class="text-slate-300">|</span>
              <div class="flex items-center space-x-2">
                <template v-for="(item, index) in breadcrumbs" :key="index">
                  <span v-if="index > 0" class="text-slate-300">/</span>
                  <NuxtLink 
                    :to="item.to" 
                    class="hover:text-green-600 font-medium transition-colors duration-150 flex items-center"
                  >
                    <UIcon v-if="item.icon" :name="item.icon" class="w-4 h-4 mr-1 text-slate-400" />
                    {{ item.label }}
                  </NuxtLink>
                </template>
              </div>
            </div>
          </div>

          <!-- Right: Actions & Profile -->
          <div class="flex items-center space-x-4">
            <div v-if="isMock" class="px-2.5 py-1 rounded bg-amber-50 border border-amber-200 text-amber-700 text-xs font-semibold flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
              Mode Démo (Local)
            </div>

            <div v-if="user" class="flex items-center space-x-3">
              <div class="text-right hidden sm:block">
                <p class="text-sm font-semibold text-slate-900">
                  {{ user.user_metadata?.first_name }} {{ user.user_metadata?.last_name }}
                </p>
                <p class="text-xs text-slate-500 truncate max-w-[150px]">
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
                  class="rounded-full w-9 h-9 p-0 bg-green-50 text-green-700 hover:bg-green-100 flex items-center justify-center font-bold"
                >
                  {{ user.email?.[0].toUpperCase() }}
                </UButton>
              </UDropdownMenu>
            </div>
          </div>

        </div>
      </div>

      <!-- Bottom Row: Navigation Menu Bar -->
      <div class="bg-slate-50/40">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-12 flex items-center justify-start">
          <nav class="flex items-center space-x-1 h-12">
            <!-- If no establishment selected -->
            <template v-if="!routeInfo.isEtabSelected">
              <NuxtLink 
                to="/dossiers" 
                class="px-4 py-3.5 border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-650 hover:text-green-600 hover:bg-slate-100/50 transition-all"
                active-class="border-b-2! border-b-green-600! text-green-700! bg-white! font-bold"
              >
                Entreprises
              </NuxtLink>
              <NuxtLink 
                to="/simulation" 
                class="px-4 py-3.5 border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-650 hover:text-green-600 hover:bg-slate-100/50 transition-all"
                active-class="border-b-2! border-b-green-600! text-green-700! bg-white! font-bold"
              >
                Simulateur de Paie
              </NuxtLink>
              <NuxtLink 
                v-if="isAdmin"
                to="/admin" 
                class="px-4 py-3.5 border-b-2 border-transparent text-xs font-bold uppercase tracking-wider text-slate-650 hover:text-green-600 hover:bg-slate-100/50 transition-all"
                active-class="border-b-2! border-b-green-600! text-green-700! bg-white! font-bold"
              >
                Administration
              </NuxtLink>
            </template>
            
            <!-- If an establishment IS selected -->
            <template v-else>
              
              <NuxtLink 
                :to="`/dossiers/${routeInfo.dossierId}/etablissements/${routeInfo.etabId}?tab=sals`" 
                class="px-4 py-3.5 border-b-2 text-xs font-bold uppercase tracking-wider transition-all"
                :class="[
                  (!route.query.tab || route.query.tab === 'sals')
                    ? 'border-b-green-600 text-green-700 bg-white font-bold'
                    : 'border-transparent text-slate-650 hover:text-green-600 hover:bg-slate-100/50'
                ]"
              >
                Salariés
              </NuxtLink>
              <NuxtLink 
                :to="`/dossiers/${routeInfo.dossierId}/etablissements/${routeInfo.etabId}?tab=contrats`" 
                class="px-4 py-3.5 border-b-2 text-xs font-bold uppercase tracking-wider transition-all"
                :class="[
                  route.query.tab === 'contrats'
                    ? 'border-b-green-600 text-green-700 bg-white font-bold'
                    : 'border-transparent text-slate-650 hover:text-green-600 hover:bg-slate-100/50'
                ]"
              >
                Contrats
              </NuxtLink>
              <NuxtLink 
                :to="`/dossiers/${routeInfo.dossierId}/etablissements/${routeInfo.etabId}?tab=bulletins`" 
                class="px-4 py-3.5 border-b-2 text-xs font-bold uppercase tracking-wider transition-all"
                :class="[
                  route.query.tab === 'bulletins'
                    ? 'border-b-green-600 text-green-700 bg-white font-bold'
                    : 'border-transparent text-slate-650 hover:text-green-600 hover:bg-slate-100/50'
                ]"
              >
                Bulletins de Salaire
              </NuxtLink>
              <NuxtLink 
                :to="`/dossiers/${routeInfo.dossierId}/etablissements/${routeInfo.etabId}?tab=infos`" 
                class="px-4 py-3.5 border-b-2 text-xs font-bold uppercase tracking-wider transition-all"
                :class="[
                  route.query.tab === 'infos'
                    ? 'border-b-green-600 text-green-700 bg-white font-bold'
                    : 'border-transparent text-slate-650 hover:text-green-600 hover:bg-slate-100/50'
                ]"
              >
                Information Générale
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

    <footer class="bg-white border-t border-slate-200 py-4 mt-auto">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center text-xs text-slate-500">
        <p>payohada • © {{ new Date().getFullYear() }} — ERP Paie Solution</p>
      </div>
    </footer>
  </div>
</template>
