<script setup>
/**
 * Onglets de l'espace Administration.
 *
 * Réservés au cabinet (vue d'ensemble, utilisateurs, référentiels en lecture).
 * L'administrateur plateforme navigue par la barre principale du layout.
 */
const { user } = useSupabase()
const route = useRoute()

const estAdminPlateforme = computed(() => !!user.value?.is_admin)
const estAdminCabinet = computed(
  () => !estAdminPlateforme.value && user.value?.role === 'cabinet'
)

const onglets = computed(() => {
  const items = [{ to: '/admin', label: "Vue d'ensemble", exact: true }]
  if (estAdminCabinet.value) {
    items.push({ to: '/admin/utilisateurs', label: 'Utilisateurs', exact: false })
    // Référentiels globaux : consultables par le cabinet, modifiables par la
    // plateforme uniquement (l'écran masque les actions d'écriture).
    items.push({ to: '/admin/constantes', label: 'Constantes', exact: false })
    items.push({ to: '/admin/plan-paie', label: 'Plan de paie', exact: false })
  }
  return items
})

const estActif = (onglet) => {
  if (onglet.exact) return route.path === onglet.to
  return route.path === onglet.to || route.path.startsWith(`${onglet.to}/`)
}
</script>

<template>
  <nav
    v-if="!estAdminPlateforme"
    class="flex items-center gap-1 overflow-x-auto no-scrollbar border-b border-slate-200"
    aria-label="Navigation de l'administration"
  >
    <NuxtLink
      v-for="onglet in onglets"
      :key="onglet.to"
      :to="onglet.to"
      class="px-4 py-2.5 whitespace-nowrap text-xs font-bold uppercase tracking-wider border-b-2 transition-colors"
      :class="estActif(onglet)
        ? 'border-navy-900 text-navy-900 bg-slate-50'
        : 'border-transparent text-slate-500 hover:text-navy-900 hover:bg-slate-50'"
    >
      {{ onglet.label }}
    </NuxtLink>
  </nav>
</template>
