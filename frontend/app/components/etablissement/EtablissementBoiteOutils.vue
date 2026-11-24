<script setup>
/**
 * Onglet « Boîte à outils » de l'établissement : simulateurs de calcul,
 * indépendants des processus (rien n'y est enregistré).
 */
defineProps({
  contracts: { type: Array, default: () => [] },
  salaries: { type: Array, default: () => [] }
})

const OUTILS = [
  {
    id: 'depart',
    titre: 'Simulateur de départ',
    description: 'Indemnités de licenciement, retraite, décès, fin de CDD, congés et gratification.',
    icone: 'i-lucide-log-out'
  }
]

const outilActif = ref(OUTILS[0].id)
</script>

<template>
  <div class="space-y-6">
    <div class="bg-white border-2 border-slate-200 p-5 shadow-flat border-t-4 border-t-navy-900">
      <h2 class="text-lg font-bold text-navy-900 uppercase tracking-wider">Boîte à outils</h2>
      <p class="text-xs text-slate-500 mt-1">Outils de simulation : les calculs sont indicatifs et ne modifient aucun dossier.</p>
      <div class="mt-4 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3" role="tablist" aria-label="Outils de simulation">
        <button
          v-for="outil in OUTILS"
          :key="outil.id"
          type="button"
          role="tab"
          :aria-selected="outilActif === outil.id"
          class="flex items-start gap-3 p-4 text-left border rounded-lg transition-colors"
          :class="outilActif === outil.id ? 'border-green-600 bg-green-50' : 'border-slate-200 hover:bg-slate-50'"
          @click="outilActif = outil.id"
        >
          <Icon :name="outil.icone" class="w-5 h-5 mt-0.5 shrink-0 text-green-700" />
          <span>
            <span class="block text-sm font-bold text-navy-900">{{ outil.titre }}</span>
            <span class="block text-xs text-slate-500 mt-0.5">{{ outil.description }}</span>
          </span>
        </button>
      </div>
    </div>

    <OutilsSimulateurDepart v-if="outilActif === 'depart'" :contracts="contracts" :salaries="salaries" />
  </div>
</template>
