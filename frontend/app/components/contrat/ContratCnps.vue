<script setup>
/**
 * Paramètres de déclaration CNPS du contrat : type de salarié (M, J, H) et
 * branches cotisées. Sans effet sur le calcul de la paie.
 */
const props = defineProps({
  /** Type de salaire du contrat, pour afficher le type déduit par défaut. */
  typeSalaire: { type: String, default: 'Mensuel' }
})
const typeSalarie = defineModel('typeSalarie', { type: [String, null], default: null })
const branches = defineModel('branches', { type: String, default: '123' })

const typeDeduit = computed(() => (props.typeSalaire === 'Mensuel' ? 'M' : 'H'))
const LIBELLES_TYPES = { M: 'Mensuel', J: 'Journalier', H: 'Horaire' }
const optionsTypes = computed(() => [
  { label: `Automatique (${LIBELLES_TYPES[typeDeduit.value]})`, value: null },
  { label: 'M — Mensuel', value: 'M' },
  { label: 'J — Journalier', value: 'J' },
  { label: 'H — Horaire', value: 'H' }
])

const BRANCHES = [
  { code: '1', libelle: 'Retraite' },
  { code: '2', libelle: 'Accidents du travail et maladies professionnelles' },
  { code: '3', libelle: 'Prestations familiales et assurance maternité' }
]
const brancheCochee = (code) => (branches.value || '').includes(code)
const basculerBranche = (code) => {
  const actuelles = new Set((branches.value || '').split(''))
  actuelles.has(code) ? actuelles.delete(code) : actuelles.add(code)
  branches.value = [...actuelles].filter(Boolean).sort().join('') || '123'
}
</script>

<template>
  <fieldset class="grid grid-cols-1 md:grid-cols-2 gap-6 border-t border-slate-100 pt-4">
    <legend class="text-xs font-bold text-navy-900 uppercase tracking-wider pt-4 md:col-span-2">Déclaration CNPS</legend>
    <div>
      <label for="contrat-type-cnps" class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Type de salarié déclaré</label>
      <Select v-model="typeSalarie" input-id="contrat-type-cnps" :options="optionsTypes" option-label="label" option-value="value" :placeholder="optionsTypes[0].label" class="mt-1 block w-full text-sm" />
      <p class="mt-1 text-[10px] text-slate-400">Colonne « Type salarié » du fichier de cotisation nominative.</p>
    </div>
    <div>
      <span class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Branches cotisées ({{ branches || '123' }})</span>
      <div class="mt-1 space-y-1.5">
        <div v-for="branche in BRANCHES" :key="branche.code" class="flex items-center gap-2">
          <Checkbox :model-value="brancheCochee(branche.code)" :input-id="`branche-cnps-${branche.code}`" binary @update:model-value="basculerBranche(branche.code)" />
          <label :for="`branche-cnps-${branche.code}`">{{ branche.code }} — {{ branche.libelle }}</label>
        </div>
      </div>
    </div>
  </fieldset>
</template>
