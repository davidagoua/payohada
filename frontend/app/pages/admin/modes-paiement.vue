<script setup>
/**
 * Référentiel des modes de paiement des salaires (administrateur plateforme).
 *
 * Les établissements choisissent ensuite ceux qu'ils acceptent, et chaque
 * salarié est payé par l'un d'eux. Un mode déjà utilisé ne se supprime pas :
 * on le désactive, il reste alors attaché à ceux qui l'utilisent.
 */
const { get, post, put, delete: apiDelete } = useApi()
const toast = useToast()

definePageMeta({
  layout: 'default'
})

const modes = ref([])
const loading = ref(false)
const enregistrement = ref(false)

const showModal = ref(false)
const currentId = ref(null)
const isEditing = computed(() => currentId.value !== null)

const formulaireVide = () => ({
  code: '',
  libelle: '',
  description: '',
  ordre: (modes.value.length || 0) + 1,
  est_actif: true
})
const form = ref(formulaireVide())

const fetchModes = async () => {
  loading.value = true
  try {
    modes.value = (await get('/modes-paiement')) || []
  } catch (e) {
    console.error('Chargement des modes de paiement impossible :', e)
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  currentId.value = null
  form.value = formulaireVide()
  showModal.value = true
}

const openEditModal = (mode) => {
  currentId.value = mode.id
  form.value = {
    code: mode.code,
    libelle: mode.libelle,
    description: mode.description || '',
    ordre: mode.ordre,
    est_actif: mode.est_actif
  }
  showModal.value = true
}

const handleSubmit = async () => {
  if (!form.value.code.trim() || !form.value.libelle.trim()) {
    toast.add({ title: 'Champs requis', description: 'Le code et le libellé sont obligatoires.', color: 'warning' })
    return
  }
  enregistrement.value = true
  const payload = {
    ...form.value,
    description: form.value.description?.trim() || null,
    ordre: Number(form.value.ordre) || 0
  }
  try {
    if (isEditing.value) {
      await put(`/modes-paiement/${currentId.value}`, payload)
      toast.add({ title: 'Mode de paiement mis à jour', description: payload.libelle, color: 'success' })
    } else {
      await post('/modes-paiement', payload)
      toast.add({ title: 'Mode de paiement créé', description: payload.libelle, color: 'success' })
    }
    showModal.value = false
    await fetchModes()
  } catch (e) {
    console.error('Enregistrement du mode de paiement impossible :', e)
  } finally {
    enregistrement.value = false
  }
}

const basculerActif = async (mode) => {
  try {
    await put(`/modes-paiement/${mode.id}`, { est_actif: !mode.est_actif })
    toast.add({
      title: mode.est_actif ? 'Mode désactivé' : 'Mode réactivé',
      description: mode.libelle,
      color: 'success'
    })
    await fetchModes()
  } catch (e) {
    console.error('Changement de statut impossible :', e)
  }
}

const handleDelete = async (mode) => {
  if (!confirm(`Supprimer définitivement le mode « ${mode.libelle} » ?`)) return
  try {
    await apiDelete(`/modes-paiement/${mode.id}`)
    toast.add({ title: 'Mode de paiement supprimé', description: mode.libelle, color: 'success' })
    await fetchModes()
  } catch (e) {
    console.error('Suppression du mode de paiement impossible :', e)
  }
}

onMounted(fetchModes)
</script>

<template>
  <div class="space-y-6">
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-navy-50 text-navy-700 rounded-lg flex items-center justify-center border border-navy-200">
          <Icon name="i-lucide-wallet" class="w-6 h-6" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-navy-900 leading-tight">Modes de paiement</h1>
          <p class="text-xs text-slate-500 mt-1">
            Modes de versement des salaires proposés aux établissements, qui choisissent ceux qu'ils acceptent.
          </p>
        </div>
      </div>
      <button
        class="w-full md:w-auto px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2"
        @click="openCreateModal"
      >
        <Icon name="i-lucide-plus" class="w-4 h-4" />
        <span>Nouveau mode</span>
      </button>
    </div>

    <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      <div v-if="loading" class="p-16 flex flex-col items-center justify-center gap-4">
        <Icon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
        <span class="text-sm font-semibold text-slate-600">Chargement des modes de paiement…</span>
      </div>

      <div v-else-if="modes.length === 0" class="p-16 text-center text-slate-500 italic text-sm">
        Aucun mode de paiement. Cliquez sur « Nouveau mode » pour en créer un.
      </div>

      <div v-else class="overflow-x-auto">
        <DataTable
          :pt="{ thead: { class: 'bg-slate-50 text-slate-600 font-bold text-xs uppercase tracking-wider' }, tbody: { class: 'text-slate-700' } }"
          class="min-w-full divide-y divide-slate-200 text-sm"
          :value="modes"
          data-key="id"
          row-hover
        >
          <Column header="Ordre" header-class="px-6 py-3.5 text-center" body-class="px-6 py-4 text-center font-mono text-xs text-slate-500">
            <template #body="{ data: mode }">
              {{ mode.ordre }}
            </template>
          </Column>
          <Column header="Libellé" header-class="px-6 py-3.5 text-left" body-class="px-6 py-4">
            <template #body="{ data: mode }">
              <p class="font-bold text-navy-900">{{ mode.libelle }}</p>
              <p v-if="mode.description" class="text-xs text-slate-500 mt-0.5">{{ mode.description }}</p>
            </template>
          </Column>
          <Column header="Code" header-class="px-6 py-3.5 text-left" body-class="px-6 py-4 font-mono text-xs font-bold text-slate-900">
            <template #body="{ data: mode }">
              {{ mode.code }}
            </template>
          </Column>
          <Column header="Statut" header-class="px-6 py-3.5 text-center" body-class="px-6 py-4 text-center">
            <template #body="{ data: mode }">
              <span
                :class="mode.est_actif ? 'bg-green-50 text-green-700 border-green-200' : 'bg-slate-100 text-slate-600 border-slate-200'"
                class="px-2 py-0.5 rounded-full text-[10px] font-bold border"
              >
                {{ mode.est_actif ? 'Proposé' : 'Désactivé' }}
              </span>
            </template>
          </Column>
          <Column header="Actions" header-class="px-6 py-3.5 text-right" body-class="px-6 py-4 text-right whitespace-nowrap">
            <template #body="{ data: mode }">
              <button
                class="text-navy-700 hover:text-navy-900 hover:bg-navy-50 p-1.5 rounded transition-colors"
                :title="`Modifier ${mode.libelle}`"
                :aria-label="`Modifier ${mode.libelle}`"
                @click="openEditModal(mode)"
              >
                <Icon name="i-lucide-pencil" class="w-4 h-4" />
              </button>
              <button
                class="text-slate-600 hover:text-navy-900 hover:bg-slate-100 p-1.5 rounded transition-colors"
                :title="mode.est_actif ? `Désactiver ${mode.libelle}` : `Réactiver ${mode.libelle}`"
                :aria-label="mode.est_actif ? `Désactiver ${mode.libelle}` : `Réactiver ${mode.libelle}`"
                @click="basculerActif(mode)"
              >
                <Icon :name="mode.est_actif ? 'i-lucide-eye-off' : 'i-lucide-eye'" class="w-4 h-4" />
              </button>
              <button
                class="text-red-500 hover:text-red-700 hover:bg-red-50 p-1.5 rounded transition-colors"
                :title="`Supprimer ${mode.libelle}`"
                :aria-label="`Supprimer ${mode.libelle}`"
                @click="handleDelete(mode)"
              >
                <Icon name="i-lucide-trash" class="w-4 h-4" />
              </button>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>

    <div class="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-600 flex items-start gap-2">
      <Icon name="i-lucide-info" class="w-4 h-4 mt-0.5 text-slate-500 shrink-0" />
      <p>
        Un mode désactivé n'est plus proposé aux établissements, mais reste attaché à ceux qui l'utilisent déjà.
        Un mode utilisé par un établissement ou un salarié ne peut pas être supprimé.
      </p>
    </div>

    <div v-if="showModal" class="fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        class="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="titre-mode-paiement"
      >
        <div class="px-6 py-4 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
          <h3 id="titre-mode-paiement" class="text-sm font-bold text-navy-900 uppercase tracking-wider">
            {{ isEditing ? 'Modifier le mode de paiement' : 'Nouveau mode de paiement' }}
          </h3>
          <button class="text-slate-400 hover:text-slate-600" aria-label="Fermer" @click="showModal = false">
            <Icon name="i-lucide-x" class="w-5 h-5" />
          </button>
        </div>

        <form class="p-6 space-y-4" @submit.prevent="handleSubmit">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="mode_libelle" class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Libellé</label>
              <InputText
                id="mode_libelle"
                v-model="form.libelle"
                required
                placeholder="ex : Mobile money"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
            <div>
              <label for="mode_code" class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Code</label>
              <InputText
                id="mode_code"
                v-model="form.code"
                required
                placeholder="ex : MOBILE_MONEY"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono uppercase focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
          </div>

          <div>
            <label for="mode_description" class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Description</label>
            <InputText
              id="mode_description"
              v-model="form.description"
              placeholder="ex : Orange Money, MTN MoMo, Moov Money, Wave…"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          <div class="grid grid-cols-2 gap-4 items-end">
            <div>
              <label for="mode_ordre" class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Ordre d'affichage</label>
              <InputText
                id="mode_ordre"
                v-model.number="form.ordre"
                type="number"
                min="0"
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
            <div class="flex items-center gap-2 pb-2">
              <Checkbox v-model="form.est_actif" input-id="mode_actif" binary />
              <label for="mode_actif" class="text-xs font-semibold text-slate-700 select-none">Proposé aux établissements</label>
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-4 border-t border-slate-200">
            <button
              type="button"
              class="px-4 py-2 border border-slate-200 rounded-lg text-slate-700 hover:bg-slate-50 text-sm font-semibold"
              @click="showModal = false"
            >
              Annuler
            </button>
            <button
              type="submit"
              :disabled="enregistrement"
              class="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white rounded-lg text-sm font-semibold shadow-sm"
            >
              {{ enregistrement ? 'Enregistrement…' : 'Enregistrer' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
