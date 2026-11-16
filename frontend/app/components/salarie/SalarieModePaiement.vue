<script setup>
/**
 * Choix du mode de paiement d'un salarié, parmi ceux acceptés par son
 * établissement (onglet « Information générale » de l'établissement).
 */
const props = defineProps({
  /** Modes acceptés par l'établissement (`etablissement.modes_paiement`). */
  modes: { type: Array, default: () => [] },
  /** Lien vers les informations de l'établissement, pour en ajouter. */
  lienEtablissement: { type: String, default: '' },
  erreur: { type: String, default: '' }
})
const modeId = defineModel({ type: [Number, null], default: null })

const options = computed(() => props.modes.map(mode => ({ label: mode.libelle, value: mode.id })))
</script>

<template>
  <div>
    <label for="sal-mode-paiement" class="block text-xs font-semibold uppercase tracking-wider text-slate-500">
      Mode de paiement du salaire<span v-if="modes.length" class="text-red-600"> *</span>
    </label>
    <Select
      v-if="modes.length"
      v-model="modeId"
      input-id="sal-mode-paiement"
      :options="options"
      option-label="label"
      option-value="value"
      placeholder="Choisir un mode de paiement"
      :invalid="!!erreur"
      class="mt-1 block w-full text-sm"
    />
    <p v-else class="mt-1 text-xs text-slate-500">
      L'établissement n'a encore choisi aucun mode de paiement.
      <NuxtLink v-if="lienEtablissement" :to="lienEtablissement" class="font-semibold text-green-700 hover:underline">
        Les définir dans les informations de l'établissement
      </NuxtLink>
    </p>
    <p v-if="erreur" class="mt-1 text-xs text-red-600 font-medium">{{ erreur }}</p>
  </div>
</template>
