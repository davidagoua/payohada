<script setup lang="ts">
import type { MenuItem } from 'primevue/menuitem'

/**
 * Menu déroulant fondé sur le `<Menu>` de PrimeVue, en mode « popup ».
 *
 * Les éléments gardent la forme utilisée dans l'application :
 * `{ label, icon: 'i-lucide-…', onSelect, class }`, éventuellement regroupés
 * dans des tableaux (`[[…], […]]`) : chaque groupe est séparé par un filet.
 * Le contenu du créneau par défaut sert de déclencheur.
 */
interface ElementMenu {
  label: string
  icon?: string
  class?: string
  disabled?: boolean
  onSelect?: () => void
}

const props = defineProps<{
  items: ElementMenu[] | ElementMenu[][]
}>()

const menu = ref()

const modele = computed<MenuItem[]>(() => {
  const groupes = (props.items.length && Array.isArray(props.items[0])
    ? props.items
    : [props.items]) as ElementMenu[][]

  return groupes.flatMap((groupe, index) => [
    ...(index > 0 ? [{ separator: true }] : []),
    ...groupe.map(element => ({
      label: element.label,
      icon: element.icon,
      class: element.class,
      disabled: element.disabled,
      command: () => element.onSelect?.()
    }))
  ])
})

const basculer = (event: Event) => menu.value?.toggle(event)
</script>

<template>
  <span
    class="inline-flex"
    aria-haspopup="true"
    @click="basculer"
  >
    <slot />
  </span>
  <Menu
    ref="menu"
    :model="modele"
    popup
  >
    <template #itemicon="{ item }">
      <Icon
        v-if="item.icon"
        :name="item.icon as string"
        class="w-4 h-4 shrink-0"
      />
    </template>
  </Menu>
</template>
