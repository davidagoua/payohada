<script setup>
/**
 * Module « Éditions » — états de paie de l'établissement.
 *
 * Principe repris du menu Éditions des logiciels de paie : on choisit un état
 * dans un catalogue, on précise une période, on visualise le résultat dans
 * l'application, puis on l'exporte (PDF, Excel, CSV) ou on l'envoie par email.
 *
 * Le périmètre est l'**établissement** : la page est atteinte depuis les
 * onglets de l'établissement, et l'identifiant vient de l'URL — il n'y a donc
 * pas de sélecteur d'établissement.
 *
 * L'aperçu affiché est le modèle tabulaire renvoyé par le serveur : le fichier
 * exporté contient exactement les mêmes lignes et les mêmes totaux.
 */
definePageMeta({ layout: 'default' })

const route = useRoute()
const router = useRouter()
const { get, post } = useApi()
const toast = useToast()

const dossierId = route.params.dossierId
const etabId = route.params.etabId

const MOIS = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
]

const maintenant = new Date()
const anneeCourante = maintenant.getFullYear()
const annees = Array.from({ length: 7 }, (_, i) => anneeCourante + 1 - i)

// ── Filtres ──────────────────────────────────────────────────────────
const periode = ref({
  mois_debut: maintenant.getMonth() + 1,
  annee_debut: anneeCourante,
  mois_fin: maintenant.getMonth() + 1,
  annee_fin: anneeCourante
})

// ── État de l'écran ──────────────────────────────────────────────────
const etablissement = ref(null)
const familles = ref([])
const codeSelectionne = ref(null)
const apercu = ref(null)
const chargementCatalogue = ref(true)
const generationEnCours = ref(false)
const exportEnCours = ref(null)
const envoiEnCours = ref(false)

const envoi = ref({ ouvert: false, destinataire: '', copie: '', objet: '', message: '' })

const editionsDisponibles = computed(() => familles.value.flatMap(f => f.editions))

const editionSelectionnee = computed(() =>
  editionsDisponibles.value.find(e => e.code === codeSelectionne.value) || null
)

// L'état déclare les formats qu'il sait produire : on n'affiche que ceux-là.
// Sans ce filtre, un document disponible en PDF seul proposerait un export
// Excel que le serveur refuserait.
const formatsDisponibles = computed(() => editionSelectionnee.value?.formats || [])

// La ligne de totaux porte son libellé sur la première colonne non totalisée,
// comme dans les fichiers PDF, Excel et CSV.
const positionLibelleTotaux = computed(() =>
  apercu.value ? apercu.value.colonnes.findIndex(colonne => !colonne.total) : -1
)

const corpsRequete = computed(() => ({
  etablissement_id: Number(etabId),
  ...periode.value
}))

// ── Chargement ───────────────────────────────────────────────────────
const chargerCatalogue = async () => {
  chargementCatalogue.value = true
  try {
    familles.value = (await get('/editions')) || []
    if (!codeSelectionne.value && editionsDisponibles.value.length) {
      codeSelectionne.value = editionsDisponibles.value[0].code
    }
  } catch (e) {
    console.error('Chargement du catalogue impossible :', e)
    toast.add({ title: 'Catalogue indisponible', color: 'danger' })
  } finally {
    chargementCatalogue.value = false
  }
}

const chargerEtablissement = async () => {
  try {
    etablissement.value = await get(`/etablissements/${etabId}`)
  } catch (e) {
    console.error('Chargement de l\'établissement impossible :', e)
  }
}

// ── Visualisation ────────────────────────────────────────────────────
const visualiser = async () => {
  if (!codeSelectionne.value) return
  generationEnCours.value = true
  apercu.value = null
  try {
    apercu.value = await post(`/editions/${codeSelectionne.value}/generer`, corpsRequete.value)
    if (!apercu.value.lignes?.length) {
      toast.add({
        title: 'Aucune donnée',
        description: 'Aucun bulletin calculé ou validé sur cette période.',
        color: 'warning'
      })
    }
  } catch (e) {
    console.error('Génération impossible :', e)
    toast.add({
      title: 'Génération impossible',
      description: e?.data?.detail || 'Une erreur est survenue.',
      color: 'danger'
    })
  } finally {
    generationEnCours.value = false
  }
}

const choisir = (code) => {
  codeSelectionne.value = code
  apercu.value = null
}

// ── Export ───────────────────────────────────────────────────────────
const telecharger = async (format) => {
  if (!codeSelectionne.value) return
  if (!formatsDisponibles.value.includes(format)) return
  exportEnCours.value = format
  try {
    const config = useRuntimeConfig()
    const { token } = useSupabase()
    const apiBase = config.public.apiBase || 'http://localhost:8000'
    const reponse = await fetch(
      `${apiBase}/api/v1/editions/${codeSelectionne.value}/export?format=${format}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token.value}`
        },
        body: JSON.stringify(corpsRequete.value)
      }
    )
    if (!reponse.ok) {
      const detail = await reponse.json().catch(() => ({}))
      throw new Error(detail.detail || `HTTP ${reponse.status}`)
    }

    const blob = await reponse.blob()
    const nom = (reponse.headers.get('content-disposition') || '')
      .match(/filename="([^"]+)"/)?.[1] || `etat.${format === 'excel' ? 'xlsx' : format}`
    const lien = document.createElement('a')
    lien.href = URL.createObjectURL(blob)
    lien.download = nom
    lien.click()
    URL.revokeObjectURL(lien.href)

    toast.add({ title: 'Export réussi', description: `${nom} téléchargé.`, color: 'success' })
  } catch (e) {
    console.error('Export impossible :', e)
    toast.add({
      title: 'Export impossible',
      description: e?.message || 'Une erreur est survenue.',
      color: 'danger'
    })
  } finally {
    exportEnCours.value = null
  }
}

// ── Envoi par email ──────────────────────────────────────────────────
const ouvrirEnvoi = () => {
  envoi.value = {
    ouvert: true,
    destinataire: '',
    copie: '',
    objet: editionSelectionnee.value
      ? `${editionSelectionnee.value.libelle} — ${apercu.value?.contexte?.periode || ''}`
      : '',
    message: ''
  }
}

const envoyer = async () => {
  if (!envoi.value.destinataire) {
    toast.add({ title: 'Destinataire requis', color: 'warning' })
    return
  }
  envoiEnCours.value = true
  try {
    const resultat = await post(`/editions/${codeSelectionne.value}/envoyer`, {
      ...corpsRequete.value,
      destinataire: envoi.value.destinataire,
      copie: envoi.value.copie || null,
      objet: envoi.value.objet || null,
      message: envoi.value.message || null
    })
    toast.add({
      title: 'État envoyé',
      description: `${resultat.piece_jointe} — ${resultat.lignes} ligne(s).`,
      color: 'success'
    })
    envoi.value.ouvert = false
  } catch (e) {
    console.error('Envoi impossible :', e)
    toast.add({
      title: 'Envoi impossible',
      description: e?.data?.detail || 'Une erreur est survenue.',
      color: 'danger'
    })
  } finally {
    envoiEnCours.value = false
  }
}

// ── Formatage ────────────────────────────────────────────────────────
const formatValeur = (valeur, colonne) => {
  if (valeur === null || valeur === undefined || valeur === '') return '—'
  if (colonne.type === 'montant') {
    return Number(valeur).toLocaleString('fr-FR', { maximumFractionDigits: 0 })
  }
  if (colonne.type === 'nombre') {
    return Number(valeur).toLocaleString('fr-FR', { maximumFractionDigits: 2 })
  }
  return String(valeur)
}

const classeColonne = (colonne) =>
  ['montant', 'nombre'].includes(colonne.type) ? 'text-right font-mono' : 'text-left'

const periodeLibelle = computed(() => {
  const debut = `${MOIS[periode.value.mois_debut - 1]} ${periode.value.annee_debut}`
  const fin = `${MOIS[periode.value.mois_fin - 1]} ${periode.value.annee_fin}`
  return debut === fin ? debut : `${debut} – ${fin}`
})

onMounted(async () => {
  await Promise.all([chargerCatalogue(), chargerEtablissement()])
})
</script>

<template>
  <div class="space-y-6">
    <!-- En-tête -->
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
      <div>
        <button
          class="carbon-helper hover:underline inline-flex items-center gap-1.5 mb-1"
          @click="router.push(`/dossiers/${dossierId}/etablissements/${etabId}?tab=infos`)"
        >
          <UIcon name="i-lucide-arrow-left" class="w-3.5 h-3.5" />
          Retour à l'établissement
        </button>
        <h1 class="carbon-heading-03">Éditions</h1>
        <p class="carbon-helper mt-0.5">
          {{ etablissement?.raison_sociale || 'Établissement' }} — états de paie, exports et envois
        </p>
      </div>
    </div>

    <!-- Paramètres de période -->
    <section class="carbon-tile">
      <h2 class="carbon-label">Période</h2>
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 items-end">
        <div>
          <label class="carbon-label">Mois de début</label>
          <select v-model.number="periode.mois_debut" class="w-full">
            <option v-for="(libelle, index) in MOIS" :key="index" :value="index + 1">
              {{ libelle }}
            </option>
          </select>
        </div>
        <div>
          <label class="carbon-label">Année de début</label>
          <select v-model.number="periode.annee_debut" class="w-full">
            <option v-for="a in annees" :key="a" :value="a">{{ a }}</option>
          </select>
        </div>
        <div>
          <label class="carbon-label">Mois de fin</label>
          <select v-model.number="periode.mois_fin" class="w-full">
            <option v-for="(libelle, index) in MOIS" :key="index" :value="index + 1">
              {{ libelle }}
            </option>
          </select>
        </div>
        <div>
          <label class="carbon-label">Année de fin</label>
          <select v-model.number="periode.annee_fin" class="w-full">
            <option v-for="a in annees" :key="a" :value="a">{{ a }}</option>
          </select>
        </div>
      </div>
      <p class="carbon-helper mt-3">
        Périmètre : <strong>{{ etablissement?.raison_sociale || 'cet établissement' }}</strong>
        · Période : <strong>{{ periodeLibelle }}</strong>
      </p>
    </section>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <!-- Catalogue -->
      <div class="lg:col-span-1 space-y-4">
        <div v-if="chargementCatalogue" class="carbon-tile text-center py-8">
          <UIcon name="i-lucide-loader-2" class="w-6 h-6 animate-spin inline-block" />
          <p class="carbon-helper mt-2">Chargement du catalogue…</p>
        </div>

        <template v-else>
          <section v-for="famille in familles" :key="famille.famille" class="space-y-2">
            <h2 class="carbon-label">{{ famille.famille }}</h2>
            <!-- La carte ne porte que le libellé : la description, trop longue
                 pour une liste, s'affiche en infobulle native au survol. -->
            <button
              v-for="edition in famille.editions"
              :key="edition.code"
              :title="edition.description"
              class="carbon-tile carbon-tile--clickable w-full text-left"
              :class="codeSelectionne === edition.code ? 'border-slate-900 border-2' : ''"
              @click="choisir(edition.code)"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="font-semibold text-slate-900">{{ edition.libelle }}</span>
                <UIcon
                  v-if="codeSelectionne === edition.code"
                  name="i-lucide-check"
                  class="w-4 h-4 text-green-600 shrink-0"
                />
              </div>
            </button>
          </section>
        </template>
      </div>

      <!-- Aperçu -->
      <div class="lg:col-span-3 space-y-4">
        <!-- Barre d'actions -->
        <div class="carbon-tile flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
          <div>
            <p class="font-semibold text-slate-900">
              {{ editionSelectionnee?.libelle || 'Choisissez une édition' }}
            </p>
            <p class="carbon-helper">{{ periodeLibelle }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              :disabled="!codeSelectionne || generationEnCours"
              class="px-4 h-10 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white font-semibold inline-flex items-center gap-2"
              @click="visualiser"
            >
              <UIcon :name="generationEnCours ? 'i-lucide-loader-2' : 'i-lucide-eye'"
                     class="w-4 h-4" :class="{ 'animate-spin': generationEnCours }" />
              Visualiser
            </button>
            <button
              v-for="format in formatsDisponibles"
              :key="format"
              :disabled="!codeSelectionne || exportEnCours === format"
              class="px-3 h-10 border border-slate-400 hover:bg-slate-100 disabled:opacity-40 font-semibold inline-flex items-center gap-1.5 uppercase text-xs"
              @click="telecharger(format)"
            >
              <UIcon :name="exportEnCours === format ? 'i-lucide-loader-2' : 'i-lucide-download'"
                     class="w-3.5 h-3.5" :class="{ 'animate-spin': exportEnCours === format }" />
              {{ format === 'excel' ? 'Excel' : format }}
            </button>
            <button
              :disabled="!codeSelectionne"
              class="px-3 h-10 border border-slate-400 hover:bg-slate-100 disabled:opacity-40 font-semibold inline-flex items-center gap-1.5 uppercase text-xs"
              @click="ouvrirEnvoi"
            >
              <UIcon name="i-lucide-mail" class="w-3.5 h-3.5" />
              Email
            </button>
          </div>
        </div>

        <!-- Résultat -->
        <div v-if="apercu" class="carbon-tile space-y-3">
          <div class="flex flex-wrap items-baseline justify-between gap-2">
            <div>
              <h2 class="font-bold text-slate-900 uppercase tracking-wide text-sm">
                {{ apercu.titre }}
              </h2>
              <p class="carbon-helper">
                {{ apercu.contexte.etablissement }} — {{ apercu.contexte.periode }}
              </p>
            </div>
            <span class="carbon-tag">{{ apercu.nombre_lignes }} ligne(s)</span>
          </div>

          <div class="overflow-x-auto border border-slate-200">
            <table class="w-full text-xs">
              <thead>
                <tr>
                  <th v-for="colonne in apercu.colonnes" :key="colonne.cle"
                      :class="classeColonne(colonne)">
                    {{ colonne.libelle }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(ligne, index) in apercu.lignes" :key="index">
                  <td v-for="colonne in apercu.colonnes" :key="colonne.cle"
                      :class="classeColonne(colonne)">
                    {{ formatValeur(ligne[colonne.cle], colonne) }}
                  </td>
                </tr>
                <tr v-if="!apercu.lignes.length">
                  <td :colspan="apercu.colonnes.length" class="text-center text-slate-500 py-6">
                    Aucune donnée sur cette période.
                  </td>
                </tr>
              </tbody>
              <tfoot v-if="Object.keys(apercu.totaux).length">
                <tr class="bg-slate-100 font-bold">
                  <td v-for="(colonne, index) in apercu.colonnes" :key="colonne.cle"
                      :class="classeColonne(colonne)">
                    {{ colonne.total
                      ? formatValeur(apercu.totaux[colonne.cle], colonne)
                      : (index === positionLibelleTotaux ? 'TOTAUX' : '') }}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          <div v-for="(note, index) in apercu.notes" :key="index"
               class="carbon-notification carbon-notification--warning">
            <p class="carbon-helper">{{ note }}</p>
          </div>
        </div>

        <div v-else class="carbon-tile text-center py-16">
          <UIcon name="i-lucide-table-2" class="w-10 h-10 text-slate-300 inline-block" />
          <p class="carbon-helper mt-3">
            Choisissez une édition puis cliquez sur « Visualiser » pour afficher l'aperçu.
          </p>
        </div>
      </div>
    </div>

    <!-- Envoi par email -->
    <div v-if="envoi.ouvert"
         class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
         @click.self="envoi.ouvert = false">
      <div class="bg-white border border-slate-300 w-full max-w-lg">
        <div class="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
          <h2 class="font-bold uppercase tracking-wide text-sm">
            Envoyer « {{ editionSelectionnee?.libelle }} »
          </h2>
          <button class="text-slate-500 hover:text-slate-900" @click="envoi.ouvert = false">
            <UIcon name="i-lucide-x" class="w-4 h-4" />
          </button>
        </div>
        <div class="p-4 space-y-4">
          <p class="carbon-helper">
            L'état sera joint au message au format PDF ({{ periodeLibelle }}).
          </p>
          <div>
            <label class="carbon-label">Destinataire *</label>
            <input v-model="envoi.destinataire" type="email"
                   placeholder="adresse@exemple.ci" class="w-full">
          </div>
          <div>
            <label class="carbon-label">Copie (facultatif)</label>
            <input v-model="envoi.copie" type="email"
                   placeholder="copie@exemple.ci" class="w-full">
          </div>
          <div>
            <label class="carbon-label">Objet</label>
            <input v-model="envoi.objet" type="text" class="w-full">
          </div>
          <div>
            <label class="carbon-label">Message (facultatif)</label>
            <textarea v-model="envoi.message" rows="3" class="w-full"
                      placeholder="Message accompagnant l'envoi…" />
          </div>
        </div>
        <div class="px-4 py-3 border-t border-slate-200 flex justify-end gap-2">
          <button class="px-3 h-10 border border-slate-400 hover:bg-slate-100 font-semibold"
                  @click="envoi.ouvert = false">
            Annuler
          </button>
          <button :disabled="envoiEnCours"
                  class="px-4 h-10 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white font-semibold inline-flex items-center gap-2"
                  @click="envoyer">
            <UIcon :name="envoiEnCours ? 'i-lucide-loader-2' : 'i-lucide-send'"
                   class="w-4 h-4" :class="{ 'animate-spin': envoiEnCours }" />
            Envoyer
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
