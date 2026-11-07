<script setup>
definePageMeta({
  layout: 'default'
})

const { user } = useSupabase()

// L'administrateur plateforme arrive ici sur le pilotage du SaaS ; le cabinet
// y administre ses membres et consulte les référentiels.
const estAdminPlateforme = computed(() => !!user.value?.is_admin)

const titre = computed(() =>
  estAdminPlateforme.value ? 'Pilotage de la plateforme' : "Portail d'Administration"
)
const sousTitre = computed(() =>
  estAdminPlateforme.value
    ? 'Usage du SaaS par cabinet, abonnés et activité de paie agrégée.'
    : 'Gérez les membres de votre cabinet et consultez les référentiels globaux.'
)
</script>

<template>
  <div class="space-y-6">
    <!-- En-tête -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-navy-50 text-navy-700 rounded-lg flex items-center justify-center font-bold text-xl border border-navy-200">
          <UIcon name="i-lucide-shield-check" class="w-6 h-6" />
        </div>
        <div>
          <div class="flex items-center gap-2 flex-wrap">
            <h1 class="text-2xl font-bold text-navy-900 leading-tight">{{ titre }}</h1>
            <span class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-navy-50 text-navy-700 border border-navy-200">
              {{ estAdminPlateforme ? 'Plateforme' : 'Cabinet' }}
            </span>
          </div>
          <p class="text-xs text-slate-500 mt-1">{{ sousTitre }}</p>
        </div>
      </div>
    </div>

    <AdminNav />

    <PlateformeTableauDeBord v-if="estAdminPlateforme" />

    <!-- Cartes d'administration du cabinet -->
    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 gap-6"
    >

      <!-- Utilisateurs du cabinet -->
      <NuxtLink
        to="/admin/utilisateurs"
        class="block bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:border-navy-500 hover:shadow-md transition-all duration-200 group"
      >
        <div class="flex items-start space-x-4">
          <div class="w-12 h-12 bg-navy-50 text-navy-700 rounded-xl flex items-center justify-center group-hover:bg-navy-900 group-hover:text-white transition-colors duration-200">
            <UIcon name="i-lucide-users" class="w-6 h-6" />
          </div>
          <div class="space-y-1">
            <h2 class="text-lg font-bold text-navy-900 group-hover:text-navy-700 transition-colors">Utilisateurs du cabinet</h2>
            <p class="text-xs text-slate-500 leading-relaxed">
              Invitez vos collaborateurs, attribuez les rôles (administrateur du cabinet ou gestionnaire de paie) et gérez l'accès aux sociétés.
            </p>
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-navy-700">
          <span>Gérer les utilisateurs</span>
          <UIcon name="i-lucide-chevron-right" class="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
        </div>
      </NuxtLink>

      <!-- Constantes de paie (plateforme) -->
      <NuxtLink
        to="/admin/constantes"
        class="block bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:border-navy-500 hover:shadow-md transition-all duration-200 group"
      >
        <div class="flex items-start space-x-4">
          <div class="w-12 h-12 bg-navy-50 text-navy-700 rounded-xl flex items-center justify-center group-hover:bg-navy-900 group-hover:text-white transition-colors duration-200">
            <UIcon name="i-lucide-sliders" class="w-6 h-6" />
          </div>
          <div class="space-y-1">
            <div class="flex items-center gap-2 flex-wrap">
              <h2 class="text-lg font-bold text-navy-900 group-hover:text-navy-700 transition-colors">Constantes de Paie</h2>
              <span class="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider bg-slate-100 text-slate-600 border border-slate-200">
                Lecture seule
              </span>
            </div>
            <p class="text-xs text-slate-500 leading-relaxed">
              Gérez les taux de cotisation, plafonds de calcul, SMIG et autres valeurs de référence utilisées pour le calcul de paie par pays.
            </p>
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-navy-700">
          <span>Consulter les constantes</span>
          <UIcon name="i-lucide-chevron-right" class="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
        </div>
      </NuxtLink>

      <!-- Plan de paie (plateforme) -->
      <NuxtLink
        to="/admin/plan-paie"
        class="block bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:border-navy-500 hover:shadow-md transition-all duration-200 group"
      >
        <div class="flex items-start space-x-4">
          <div class="w-12 h-12 bg-navy-50 text-navy-700 rounded-xl flex items-center justify-center group-hover:bg-navy-900 group-hover:text-white transition-colors duration-200">
            <UIcon name="i-lucide-book-open" class="w-6 h-6" />
          </div>
          <div class="space-y-1">
            <div class="flex items-center gap-2 flex-wrap">
              <h2 class="text-lg font-bold text-navy-900 group-hover:text-navy-700 transition-colors">Plan Comptable de Paie</h2>
              <span class="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider bg-slate-100 text-slate-600 border border-slate-200">
                Lecture seule
              </span>
            </div>
            <p class="text-xs text-slate-500 leading-relaxed">
              Configurez le plan des postes de paie (Brut, Cotisations, Primes, Avantages), leurs sens (gain/retenue) et leurs comptes de débit/crédit.
            </p>
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-navy-700">
          <span>Consulter le plan de paie</span>
          <UIcon name="i-lucide-chevron-right" class="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
        </div>
      </NuxtLink>

      <!-- Rappel pour un cabinet : les référentiels sont consultables -->
      <div
        class="bg-slate-50 border border-slate-200 rounded-xl p-6 text-xs text-slate-500 leading-relaxed"
      >
        <p class="font-bold text-navy-900 text-sm mb-1">Référentiels globaux en lecture seule</p>
        <p>
          Les constantes de paie et le plan comptable sont communs à la plateforme.
          Vous pouvez les consulter ici ; leur modification est réservée à
          l'administrateur plateforme.
        </p>
      </div>
    </div>
  </div>
</template>
