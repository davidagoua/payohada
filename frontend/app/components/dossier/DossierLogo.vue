<script setup>
/**
 * Logo de l'entreprise : aperçu, dépôt, remplacement et retrait.
 *
 * Le logo est stocké en base par l'API (PNG, JPEG ou WebP, 1 Mo au plus) et
 * relu en data URL, la balise <img> ne pouvant pas porter le jeton d'accès.
 */
const props = defineProps({
  dossierId: { type: [Number, String], required: true },
  /** `dossier.a_logo` : un logo a déjà été déposé. */
  aLogo: { type: Boolean, default: false }
})
const emit = defineEmits(['change'])

const { get, put, delete: apiDelete } = useApi()
const toast = useToast()

const TAILLE_MAX = 1024 * 1024
const FORMATS = ['image/png', 'image/jpeg', 'image/webp']

const apercu = ref(null)
const enCours = ref(false)
const champFichier = ref(null)

const chargerApercu = async () => {
  if (!props.aLogo) {
    apercu.value = null
    return
  }
  try {
    const logo = await get(`/dossiers/${props.dossierId}/logo`)
    apercu.value = logo?.data_url || null
  } catch {
    apercu.value = null
  }
}

watch(() => [props.dossierId, props.aLogo], chargerApercu, { immediate: true })

const choisir = () => champFichier.value?.click()

const deposer = async (evenement) => {
  const fichier = evenement.target.files?.[0]
  evenement.target.value = ''
  if (!fichier) return
  // Contrôlé aussi par l'API, mais un message clair vaut mieux qu'un refus brut.
  if (!FORMATS.includes(fichier.type)) {
    toast.add({ title: 'Format non pris en charge', description: 'Utilisez une image PNG, JPEG ou WebP.', color: 'warning' })
    return
  }
  if (fichier.size > TAILLE_MAX) {
    toast.add({ title: 'Logo trop lourd', description: 'Le logo ne doit pas dépasser 1 Mo.', color: 'warning' })
    return
  }
  enCours.value = true
  try {
    const donnees = new FormData()
    donnees.append('fichier', fichier)
    const dossier = await put(`/dossiers/${props.dossierId}/logo`, donnees)
    toast.add({ title: 'Logo enregistré', description: fichier.name, color: 'success' })
    emit('change', dossier)
    await chargerApercu()
  } catch (e) {
    console.error('Dépôt du logo impossible :', e)
  } finally {
    enCours.value = false
  }
}

const retirer = async () => {
  if (!confirm('Retirer le logo de l’entreprise ?')) return
  enCours.value = true
  try {
    const dossier = await apiDelete(`/dossiers/${props.dossierId}/logo`)
    apercu.value = null
    toast.add({ title: 'Logo retiré', color: 'success' })
    emit('change', dossier)
  } catch (e) {
    console.error('Retrait du logo impossible :', e)
  } finally {
    enCours.value = false
  }
}
</script>

<template>
  <div class="flex flex-col sm:flex-row sm:items-center gap-4">
    <div
      class="w-32 h-20 shrink-0 border border-slate-200 rounded-lg bg-slate-50 flex items-center justify-center overflow-hidden"
    >
      <img v-if="apercu" :src="apercu" alt="Logo de l'entreprise" class="max-w-full max-h-full object-contain">
      <span v-else class="text-xs text-slate-400">Aucun logo</span>
    </div>
    <div class="space-y-2">
      <p class="text-xs font-semibold text-slate-700">Logo de l'entreprise</p>
      <p class="text-xs text-slate-500">PNG, JPEG ou WebP, 1 Mo au plus.</p>
      <div class="flex flex-wrap gap-2">
        <button
          type="button"
          :disabled="enCours"
          class="px-3 py-1.5 text-xs font-semibold border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-700 disabled:opacity-60 flex items-center gap-1.5"
          @click="choisir"
        >
          <Icon :name="enCours ? 'i-lucide-loader-2' : 'i-lucide-upload'" class="w-3.5 h-3.5" :class="{ 'animate-spin': enCours }" />
          {{ apercu ? 'Remplacer le logo' : 'Ajouter un logo' }}
        </button>
        <button
          v-if="apercu"
          type="button"
          :disabled="enCours"
          class="px-3 py-1.5 text-xs font-semibold border border-red-200 rounded-lg hover:bg-red-50 text-red-700 disabled:opacity-60"
          @click="retirer"
        >
          Retirer
        </button>
      </div>
      <input
        ref="champFichier"
        type="file"
        accept="image/png,image/jpeg,image/webp"
        class="hidden"
        aria-label="Fichier du logo de l'entreprise"
        @change="deposer"
      >
    </div>
  </div>
</template>
