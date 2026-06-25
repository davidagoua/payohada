<script setup>
definePageMeta({
  layout: 'default'
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-50 text-green-700 rounded-lg flex items-center justify-center font-bold text-xl border border-green-200">
          <UIcon name="i-lucide-shield-check" class="w-6 h-6" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-900 leading-tight">Portail d'Administration</h1>
          <p class="text-xs text-slate-500 mt-1">Configurez les paramètres globaux du système de paie.</p>
        </div>
      </div>
    </div>

    <!-- Administrative Cards Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      
      <!-- Constants Card -->
      <NuxtLink to="/admin/constantes" class="block bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:border-green-500 hover:shadow-md transition-all duration-200 group">
        <div class="flex items-start space-x-4">
          <div class="w-12 h-12 bg-green-50 text-green-600 rounded-xl flex items-center justify-center group-hover:bg-green-600 group-hover:text-white transition-colors duration-200">
            <UIcon name="i-lucide-sliders" class="w-6 h-6" />
          </div>
          <div class="space-y-1">
            <h2 class="text-lg font-bold text-slate-900 group-hover:text-green-600 transition-colors">Constantes de Paie</h2>
            <p class="text-xs text-slate-500 leading-relaxed">
              Gérez les taux de cotisation, plafonds de calcul, SMIG et autres valeurs de référence utilisées pour le calcul de paie par pays.
            </p>
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-green-600">
          <span>Configurer les constantes</span>
          <UIcon name="i-lucide-chevron-right" class="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
        </div>
      </NuxtLink>

      <!-- Plan de Paie Card -->
      <NuxtLink to="/admin/plan-paie" class="block bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:border-green-500 hover:shadow-md transition-all duration-200 group">
        <div class="flex items-start space-x-4">
          <div class="w-12 h-12 bg-green-50 text-green-600 rounded-xl flex items-center justify-center group-hover:bg-green-600 group-hover:text-white transition-colors duration-200">
            <UIcon name="i-lucide-book-open" class="w-6 h-6" />
          </div>
          <div class="space-y-1">
            <h2 class="text-lg font-bold text-slate-900 group-hover:text-green-600 transition-colors">Plan Comptable de Paie</h2>
            <p class="text-xs text-slate-500 leading-relaxed">
              Configurez le plan des postes de paie (Brut, Cotisations, Primes, Avantages), leurs sens (gain/retenue) et leurs comptes de débit/crédit.
            </p>
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-green-600">
          <span>Configurer le plan de paie</span>
          <UIcon name="i-lucide-chevron-right" class="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
        </div>
      </NuxtLink>

    </div>
  </div>
</template>
