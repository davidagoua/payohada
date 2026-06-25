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
    <header class="bg-white border-b border-slate-200 shadow-sm sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        <!-- Left: Logo & Breadcrumbs -->
        <div class="flex items-center space-x-6">
          <NuxtLink to="/dossiers" class="flex items-center space-x-2 shrink-0">
            <!-- Sleek Green Badge Logo -->
            <div class="w-8 h-8 rounded-lg bg-green-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
              P
            </div>
            <span class="text-xl font-bold tracking-tight text-slate-900">
              payohada
            </span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 font-semibold border border-slate-200">
              Fiori Shell
            </span>
          </NuxtLink>

          <!-- Navigation Links -->
          <nav class="hidden md:flex items-center space-x-1 ml-4 border-l border-slate-200 pl-4">
            <NuxtLink 
              to="/dossiers" 
              class="px-3 py-1.5 rounded-md text-sm font-medium text-slate-600 hover:text-green-600 hover:bg-green-50 transition-colors"
              active-class="text-green-700 bg-green-50 font-semibold"
            >
              Entreprises
            </NuxtLink>
            <NuxtLink 
              to="/bulletins" 
              class="px-3 py-1.5 rounded-md text-sm font-medium text-slate-600 hover:text-green-600 hover:bg-green-50 transition-colors"
              active-class="text-green-700 bg-green-50 font-semibold"
            >
              Bulletins de Paie
            </NuxtLink>
            <NuxtLink 
              to="/simulation" 
              class="px-3 py-1.5 rounded-md text-sm font-medium text-slate-600 hover:text-green-600 hover:bg-green-50 transition-colors"
              active-class="text-green-700 bg-green-50 font-semibold"
            >
              Simulateur de Paie
            </NuxtLink>
            <NuxtLink 
              v-if="isAdmin"
              to="/admin" 
              class="px-3 py-1.5 rounded-md text-sm font-medium text-slate-600 hover:text-green-600 hover:bg-green-50 transition-colors"
              active-class="text-green-700 bg-green-50 font-semibold"
            >
              Administration
            </NuxtLink>
          </nav>

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
    </header>

    <!-- Main Workspace Container -->
    <main class="flex-grow max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
      <slot />
    </main>

    <!-- SAP Fiori Style Footer -->
    <footer class="bg-white border-t border-slate-200 py-4 mt-auto">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center text-xs text-slate-500">
        <p>payohada • © {{ new Date().getFullYear() }} — ERP Payroll Solution</p>
        <p class="mt-2 sm:mt-0">Design basé sur SAP Fiori & Vue.js</p>
      </div>
    </footer>
  </div>
</template>
