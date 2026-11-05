<script setup>
/**
 * Assistant d'import Excel/CSV des données de base d'un dossier :
 * établissements, salariés et contrats.
 *
 * Le flux est volontairement en trois temps : télécharger le modèle, déposer
 * le fichier pour une analyse à blanc, puis exécuter l'import des lignes
 * valides. Aucune écriture n'a lieu avant l'exécution.
 */
const route = useRoute()
const { get, post, fetch: apiFetch } = useApi()
const { token } = useSupabase()
const toast = useToast()
const config = useRuntimeConfig()

const dossierId = route.params.dossierId
const dossier = ref(null)

const typesImport = ref([])
const typeSelectionne = ref('etablissements')
const fichier = ref(null)
const inputFichier = ref(null)
const analyse = ref(null)
const analyseEnCours = ref(false)
const execution = ref(null)
const executionEnCours = ref(false)
const historique = ref([])
const chargementHistorique = ref(false)
const mappingSelection = ref({})
const erreurAnalyse = ref('')
const erreurExecution = ref('')
const diagnostic = ref(null)

const champsCourants = computed(() => typeCourant.value?.champs || [])

const champsAffiches = computed(() => champsCourants.value.slice(0, 7))

const champsManquantsAvecCle = computed(() => {
  if (!analyse.value?.champs_manquants?.length) return []
  return analyse.value.champs_manquants.map((libelle) => {
    const champ = champsCourants.value.find((item) => item.libelle === libelle)
    return { libelle, cle: champ?.cle || libelle }
  })
})

const mappingComplet = computed(() =>
  champsManquantsAvecCle.value.every((champ) => !!mappingSelection.value[champ.cle])
)

const messageErreur = (e) => {
  const status = e?.status || e?.response?.status
  const detail = e?.data?.detail || e?.response?._data?.detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || String(item)).join(' — ')
  }
  if (typeof detail === 'string' && detail.length < 600) return detail
  if (status === 413) {
    return 'Le fichier est trop volumineux pour le serveur (limite du proxy). Réduisez sa taille ou découpez-le.'
  }
  if (status === 502 || status === 503 || status === 504) {
    return `Le serveur est indisponible (HTTP ${status}). Réessayez dans quelques instants ou contactez l'administrateur.`
  }
  if (status === 401 || status === 403) {
    return 'Votre session ou vos droits ne permettent pas cet import. Reconnectez-vous puis réessayez.'
  }
  if (!status) {
    return 'Impossible de joindre le serveur. Vérifiez votre connexion réseau.'
  }
  return `L'import a échoué (HTTP ${status}). Consultez les logs du serveur pour le détail.`
}

const chargerDiagnostic = async () => {
  try {
    diagnostic.value = await get('/imports/diagnostic')
  } catch (e) {
    // Endpoint absent sur une version antérieure du backend : on reste silencieux.
    diagnostic.value = null
  }
}

const typeCourantLabel = (code) =>
  typesImport.value.find((item) => item.code === code)?.libelle || code

const statutLabel = (statut) =>
  ({
    analyse: 'Analysé',
    pret: 'Prêt à importer',
    mapping_requis: 'Mapping requis',
    termine: 'Terminé',
    echec: 'Échec'
  })[statut] || statut

const statutCouleur = (statut) =>
  ({
    pret: 'bg-green-50 text-green-700 border-green-200',
    termine: 'bg-navy-50 text-navy-700 border-navy-200',
    mapping_requis: 'bg-amber-50 text-amber-700 border-amber-200',
    echec: 'bg-red-50 text-red-700 border-red-200'
  })[statut] || 'bg-slate-50 text-slate-600 border-slate-200'

const formaterDate = (valeur) => {
  if (!valeur) return '—'
  const date = new Date(valeur)
  if (Number.isNaN(date.getTime())) return valeur
  return date.toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

const formaterTaille = (octets) => {
  if (!octets) return '—'
  if (octets < 1024 * 1024) return `${Math.round(octets / 1024)} Ko`
  return `${(octets / (1024 * 1024)).toFixed(1)} Mo`
}

const chargerTypes = async () => {
  try {
    typesImport.value = (await get('/imports/types')) || []
  } catch (e) {
    console.error('Chargement des types d’import impossible :', e)
  }
}

const chargerDossier = async () => {
  try {
    dossier.value = await get(`/dossiers/${dossierId}`)
  } catch (e) {
    console.error('Chargement du dossier impossible :', e)
  }
}

const chargerHistorique = async () => {
  chargementHistorique.value = true
  try {
    historique.value = (await get('/imports', { params: { dossier_id: dossierId } })) || []
  } catch (e) {
    console.error('Chargement de l’historique impossible :', e)
  } finally {
    chargementHistorique.value = false
  }
}

const choisirType = (code) => {
  if (typeSelectionne.value === code) return
  typeSelectionne.value = code
  fichier.value = null
  analyse.value = null
  execution.value = null
  mappingSelection.value = {}
  if (inputFichier.value) inputFichier.value.value = ''
}

const choisirFichier = (event) => {
  const selection = event.target.files?.[0]
  if (!selection) return
  const extension = selection.name.split('.').pop()?.toLowerCase()
  if (!['xlsx', 'xlsm', 'csv'].includes(extension)) {
    toast.add({
      title: 'Format non pris en charge',
      description: 'Utilisez un fichier .xlsx, .xlsm ou .csv.',
      color: 'warning'
    })
    event.target.value = ''
    return
  }
  fichier.value = selection
  analyse.value = null
  execution.value = null
  mappingSelection.value = {}
}

const deposerFichier = (event) => {
  event.preventDefault()
  const selection = event.dataTransfer?.files?.[0]
  if (selection) {
    choisirFichier({ target: { files: [selection], value: '' } })
  }
}

const telechargerModele = async () => {
  try {
    const reponse = await fetch(
      `${resoudreApiBase(config.public.apiBase)}/imports/modeles/${typeSelectionne.value}`,
      { headers: { Authorization: `Bearer ${token.value}` } }
    )
    if (!reponse.ok) throw new Error('Téléchargement impossible')
    const blob = await reponse.blob()
    const url = URL.createObjectURL(blob)
    const lien = document.createElement('a')
    lien.href = url
    lien.download = `modele-${typeSelectionne.value}.xlsx`
    document.body.appendChild(lien)
    lien.click()
    lien.remove()
    URL.revokeObjectURL(url)
    toast.add({
      title: 'Modèle téléchargé',
      description: 'Remplissez-le, puis déposez-le ci-dessous.',
      color: 'success'
    })
  } catch (e) {
    console.error('Téléchargement du modèle impossible :', e)
    toast.add({
      title: 'Téléchargement impossible',
      description: 'Réessayez ou vérifiez votre connexion.',
      color: 'danger'
    })
  }
}

const analyserFichier = async () => {
  if (!fichier.value) {
    toast.add({
      title: 'Aucun fichier',
      description: 'Choisissez d’abord un fichier à analyser.',
      color: 'warning'
    })
    return
  }
  analyseEnCours.value = true
  execution.value = null
  erreurAnalyse.value = ''
  erreurExecution.value = ''
  try {
    const formulaire = new FormData()
    formulaire.append('dossier_id', String(dossierId))
    formulaire.append('type_import', typeSelectionne.value)
    formulaire.append('fichier', fichier.value)
    if (Object.keys(mappingSelection.value).length > 0) {
      formulaire.append('mapping', JSON.stringify(mappingSelection.value))
    }
    analyse.value = await apiFetch('/imports/analyser', { method: 'POST', body: formulaire })
    await chargerDiagnostic()
    if (!analyse.value.champs_manquants?.length) {
      toast.add({
        title: 'Analyse terminée',
        description: analyse.value.message,
        color: analyse.value.job.lignes_erreurs ? 'warning' : 'success'
      })
    }
  } catch (e) {
    console.error('Analyse de l’import impossible :', e)
    erreurAnalyse.value = messageErreur(e)
  } finally {
    analyseEnCours.value = false
  }
}

const executerImport = async (ignorerErreurs = false) => {
  if (!analyse.value?.job?.id) return
  const nombreErreurs = analyse.value.job.lignes_erreurs || 0
  if (nombreErreurs > 0 && !ignorerErreurs) return
  if (nombreErreurs > 0 && ignorerErreurs) {
    const confirmation = confirm(
      `Importer uniquement les ${analyse.value.job.lignes_valides} ligne(s) valide(s) ? ` +
      `Les ${nombreErreurs} ligne(s) en erreur seront ignorées.`
    )
    if (!confirmation) return
  }
  executionEnCours.value = true
  erreurExecution.value = ''
  try {
    execution.value = await post(`/imports/${analyse.value.job.id}/executer`, {
      ignorer_erreurs: ignorerErreurs
    })
    toast.add({
      title: 'Import exécuté',
      description: execution.value.message,
      color: 'success'
    })
    await chargerHistorique()
  } catch (e) {
    console.error('Exécution de l’import impossible :', e)
    erreurExecution.value = messageErreur(e)
  } finally {
    executionEnCours.value = false
  }
}

onMounted(async () => {
  await Promise.all([chargerTypes(), chargerDossier(), chargerHistorique(), chargerDiagnostic()])
})
</script>

<template>
  <div class="space-y-6">
    <!-- En-tête -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div class="flex items-start gap-4">
          <div class="w-12 h-12 bg-navy-50 text-navy-700 rounded-xl flex items-center justify-center border border-navy-200 shrink-0">
            <UIcon name="i-lucide-upload" class="w-6 h-6" />
          </div>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <h1 class="text-2xl font-bold text-navy-900 leading-tight">Importer des données</h1>
              <span class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-navy-50 text-navy-700 border border-navy-200">
                {{ dossier?.code || 'Dossier' }}
              </span>
            </div>
            <p class="text-xs text-slate-500 mt-1">
              Analysez un fichier Excel ou CSV, corrigez les erreurs, puis importez les lignes valides.
              Aucune donnée n'est écrite avant l'exécution.
            </p>
          </div>
        </div>
        <NuxtLink
          :to="`/dossiers/${dossierId}`"
          class="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 text-slate-600 hover:bg-slate-50 text-xs font-bold uppercase tracking-wider transition-colors shrink-0"
        >
          <UIcon name="i-lucide-arrow-left" class="w-4 h-4" />
          Retour au dossier
        </NuxtLink>
      </div>
    </div>

    <!-- Diagnostic d'installation (production) -->
    <div
      v-if="diagnostic && (!diagnostic.table_imports || !diagnostic.ecriture_possible)"
      class="bg-red-50 border border-red-200 rounded-xl p-4 text-xs text-red-900 flex items-start gap-2"
    >
      <UIcon name="i-lucide-server-crash" class="w-4 h-4 mt-0.5 shrink-0" />
      <div class="space-y-1">
        <p class="font-bold">Le module d'import n'est pas complètement installé sur le serveur.</p>
        <p v-if="!diagnostic.table_imports">
          La table <span class="font-mono">imports</span> est absente de la base. Appliquez les migrations
          (<span class="font-mono">python apply_migrations.py</span>) puis redémarrez l'API.
        </p>
        <p v-if="!diagnostic.ecriture_possible">
          Le dossier d'imports n'est pas accessible en écriture :
          <span class="font-mono">{{ diagnostic.dossier_imports }}</span>.
          Vérifiez les droits du volume monté sur le conteneur backend.
        </p>
      </div>
    </div>

    <!-- Erreur d'analyse ou d'exécution -->
    <div v-if="erreurAnalyse" class="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-900 flex items-start gap-2">
      <UIcon name="i-lucide-triangle-alert" class="w-4 h-4 mt-0.5 shrink-0" />
      <div>
        <p class="font-bold">L'analyse n'a pas abouti.</p>
        <p class="mt-0.5">{{ erreurAnalyse }}</p>
      </div>
    </div>
    <div v-if="erreurExecution" class="bg-red-50 border border-red-200 rounded-xl p-4 text-xs text-red-900 flex items-start gap-2">
      <UIcon name="i-lucide-circle-x" class="w-4 h-4 mt-0.5 shrink-0" />
      <div>
        <p class="font-bold">L'exécution de l'import a échoué.</p>
        <p class="mt-0.5">{{ erreurExecution }}</p>
      </div>
    </div>

    <!-- Étapes -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="bg-white border border-slate-200 rounded-xl p-4 flex items-start gap-3">
        <span class="w-7 h-7 rounded-full bg-navy-900 text-white text-xs font-bold flex items-center justify-center shrink-0">1</span>
        <div>
          <p class="text-sm font-bold text-navy-900">Télécharger le modèle</p>
          <p class="text-xs text-slate-500 mt-0.5">Un fichier par type de données.</p>
        </div>
      </div>
      <div class="bg-white border border-slate-200 rounded-xl p-4 flex items-start gap-3">
        <span class="w-7 h-7 rounded-full bg-navy-900 text-white text-xs font-bold flex items-center justify-center shrink-0">2</span>
        <div>
          <p class="text-sm font-bold text-navy-900">Analyser sans écrire</p>
          <p class="text-xs text-slate-500 mt-0.5">Rapport d'erreurs ligne par ligne, sans écriture.</p>
        </div>
      </div>
      <div class="bg-white border border-slate-200 rounded-xl p-4 flex items-start gap-3">
        <span class="w-7 h-7 rounded-full bg-navy-900 text-white text-xs font-bold flex items-center justify-center shrink-0">3</span>
        <div>
          <p class="text-sm font-bold text-navy-900">Exécuter l'import</p>
          <p class="text-xs text-slate-500 mt-0.5">Créations et mises à jour idempotentes.</p>
        </div>
      </div>
    </div>

    <!-- Choix du type -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider mb-4">Type de données</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <button
          v-for="type in typesImport"
          :key="type.code"
          type="button"
          class="text-left border rounded-xl p-4 transition-all"
          :class="typeSelectionne === type.code
            ? 'border-green-600 bg-green-50/40 ring-2 ring-green-100'
            : 'border-slate-200 hover:border-navy-300 hover:bg-slate-50'"
          @click="choisirType(type.code)"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm font-bold text-navy-900">{{ type.libelle }}</span>
            <UIcon
              :name="typeSelectionne === type.code ? 'i-lucide-check-circle-2' : 'i-lucide-circle'"
              class="w-5 h-5"
              :class="typeSelectionne === type.code ? 'text-green-600' : 'text-slate-300'"
            />
          </div>
          <p class="text-xs text-slate-500 mt-1 leading-relaxed">{{ type.description }}</p>
          <p class="text-[11px] text-slate-400 mt-2">
            {{ type.champs.filter(c => c.obligatoire).length }} champ(s) obligatoire(s)
          </p>
        </button>
      </div>

      <div class="mt-5 flex flex-col sm:flex-row sm:items-center gap-3">
        <button
          type="button"
          class="inline-flex items-center gap-2 px-4 py-2 border border-navy-200 text-navy-800 hover:bg-navy-50 text-xs font-bold uppercase tracking-wider transition-colors"
          @click="telechargerModele"
        >
          <UIcon name="i-lucide-download" class="w-4 h-4" />
          Télécharger le modèle Excel
        </button>
        <p class="text-xs text-slate-500">
          Importez d'abord les établissements, puis les salariés, puis les contrats.
        </p>
      </div>
    </div>

    <!-- Dépôt et analyse -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider mb-4">Fichier à analyser</h2>

      <div
        class="border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer"
        :class="fichier ? 'border-green-300 bg-green-50/30' : 'border-slate-300 hover:border-navy-400 hover:bg-slate-50'"
        @click="inputFichier?.click()"
        @dragover.prevent
        @drop="deposerFichier"
      >
        <input
          ref="inputFichier"
          type="file"
          accept=".xlsx,.xlsm,.csv"
          class="hidden"
          @change="choisirFichier"
        >
        <UIcon name="i-lucide-file-spreadsheet" class="w-8 h-8 mx-auto mb-2" :class="fichier ? 'text-green-600' : 'text-slate-400'" />
        <p v-if="fichier" class="text-sm font-bold text-navy-900">{{ fichier.name }}</p>
        <p v-else class="text-sm font-semibold text-slate-600">Cliquez ou déposez un fichier ici</p>
        <p class="text-xs text-slate-400 mt-1">
          {{ fichier ? formaterTaille(fichier.size) : '.xlsx, .xlsm ou .csv — 25 Mo maximum' }}
        </p>
      </div>

      <div class="mt-4 flex justify-end">
        <button
          type="button"
          :disabled="!fichier || analyseEnCours"
          class="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white text-xs font-bold uppercase tracking-wider transition-colors"
          @click="analyserFichier"
        >
          <UIcon v-if="analyseEnCours" name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
          <UIcon v-else name="i-lucide-scan-search" class="w-4 h-4" />
          {{ analyseEnCours ? 'Analyse en cours…' : 'Analyser le fichier' }}
        </button>
      </div>
    </div>

    <!-- Résultat de l'analyse -->
    <div v-if="analyse" class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider">Rapport d'analyse</h2>
          <p class="text-xs text-slate-500 mt-1">{{ analyse.message }}</p>
        </div>
        <span class="px-2 py-1 text-[10px] font-bold uppercase tracking-wider border self-start" :class="statutCouleur(analyse.job.statut)">
          {{ statutLabel(analyse.job.statut) }}
        </span>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="bg-slate-50 border border-slate-200 rounded-lg p-3">
          <p class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Lignes</p>
          <p class="text-xl font-bold text-navy-900">{{ analyse.job.total_lignes }}</p>
        </div>
        <div class="bg-green-50 border border-green-200 rounded-lg p-3">
          <p class="text-[10px] font-bold uppercase tracking-wider text-green-700">Valides</p>
          <p class="text-xl font-bold text-green-700">{{ analyse.job.lignes_valides }}</p>
        </div>
        <div class="bg-red-50 border border-red-200 rounded-lg p-3">
          <p class="text-[10px] font-bold uppercase tracking-wider text-red-700">En erreur</p>
          <p class="text-xl font-bold text-red-700">{{ analyse.job.lignes_erreurs }}</p>
        </div>
        <div class="bg-slate-50 border border-slate-200 rounded-lg p-3">
          <p class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Colonnes</p>
          <p class="text-xl font-bold text-navy-900">{{ analyse.colonnes.length }}</p>
        </div>
      </div>

      <!-- Mapping incomplet -->
      <div v-if="champsManquantsAvecCle.length" class="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-3">
        <div class="flex items-start gap-2">
          <UIcon name="i-lucide-triangle-alert" class="w-4 h-4 text-amber-700 mt-0.5 shrink-0" />
          <div>
            <p class="text-sm font-bold text-amber-900">Associez les colonnes manquantes</p>
            <p class="text-xs text-amber-800 mt-0.5">
              Le fichier ne contient pas certaines colonnes obligatoires. Indiquez la colonne correspondante,
              puis relancez l'analyse.
            </p>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div v-for="champ in champsManquantsAvecCle" :key="champ.cle">
            <label class="block text-[11px] font-bold uppercase tracking-wider text-amber-900">{{ champ.libelle }}</label>
            <select
              v-model="mappingSelection[champ.cle]"
              class="mt-1 block w-full px-3 py-2 border border-amber-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              <option value="">— Choisir une colonne —</option>
              <option v-for="colonne in analyse.colonnes" :key="colonne" :value="colonne">{{ colonne }}</option>
            </select>
          </div>
        </div>
        <div class="flex justify-end">
          <button
            type="button"
            :disabled="!mappingComplet || analyseEnCours"
            class="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:bg-slate-300 text-white text-xs font-bold uppercase tracking-wider transition-colors"
            @click="analyserFichier"
          >
            <UIcon name="i-lucide-refresh-cw" class="w-4 h-4" />
            Relancer l'analyse
          </button>
        </div>
      </div>

      <!-- Erreurs -->
      <div v-if="analyse.erreurs.length" class="space-y-2">
        <div class="flex items-center justify-between">
          <h3 class="text-xs font-bold uppercase tracking-wider text-red-700">Erreurs à corriger</h3>
          <span class="text-[11px] text-slate-500">
            {{ analyse.job.lignes_erreurs }} ligne(s) — {{ analyse.erreurs.length }} erreur(s) affichée(s)
          </span>
        </div>
        <div class="max-h-64 overflow-auto border border-slate-200 rounded-lg">
          <table class="min-w-full text-xs">
            <thead class="bg-slate-50 text-slate-500 uppercase tracking-wider text-[10px] sticky top-0">
              <tr>
                <th class="px-3 py-2 text-left">Ligne</th>
                <th class="px-3 py-2 text-left">Champ</th>
                <th class="px-3 py-2 text-left">Message</th>
                <th class="px-3 py-2 text-left">Valeur</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="(erreur, index) in analyse.erreurs" :key="index" class="hover:bg-slate-50">
                <td class="px-3 py-2 font-mono text-slate-600">{{ erreur.ligne }}</td>
                <td class="px-3 py-2 font-semibold text-navy-900">{{ erreur.champ || '—' }}</td>
                <td class="px-3 py-2 text-slate-600">{{ erreur.message }}</td>
                <td class="px-3 py-2 font-mono text-slate-500">{{ erreur.valeur ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Aperçu -->
      <div v-if="analyse.apercu.length" class="space-y-2">
        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-600">Aperçu des lignes valides</h3>
        <div class="overflow-x-auto border border-slate-200 rounded-lg">
          <table class="min-w-full text-xs">
            <thead class="bg-slate-50 text-slate-500 uppercase tracking-wider text-[10px]">
              <tr>
                <th v-for="champ in champsAffiches" :key="champ.cle" class="px-3 py-2 text-left whitespace-nowrap">{{ champ.libelle }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="(ligne, index) in analyse.apercu" :key="index">
                <td v-for="champ in champsAffiches" :key="champ.cle" class="px-3 py-2 text-slate-600 whitespace-nowrap">
                  {{ ligne[champ.cle] ?? '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Exécution -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-end gap-3 pt-2 border-t border-slate-100">
        <button
          v-if="analyse.job.lignes_erreurs > 0"
          type="button"
          :disabled="executionEnCours || analyse.job.lignes_valides === 0"
          class="inline-flex items-center gap-2 px-4 py-2 border border-amber-300 text-amber-800 hover:bg-amber-50 disabled:opacity-50 text-xs font-bold uppercase tracking-wider transition-colors"
          @click="executerImport(true)"
        >
          <UIcon v-if="executionEnCours" name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
          <UIcon v-else name="i-lucide-filter" class="w-4 h-4" />
          Importer les {{ analyse.job.lignes_valides }} ligne(s) valide(s)
        </button>
        <button
          type="button"
          :disabled="executionEnCours || analyse.job.statut === 'mapping_requis' || analyse.job.lignes_erreurs > 0 || analyse.job.lignes_valides === 0"
          class="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white text-xs font-bold uppercase tracking-wider transition-colors"
          @click="executerImport(false)"
        >
          <UIcon v-if="executionEnCours" name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
          <UIcon v-else name="i-lucide-play" class="w-4 h-4" />
          Exécuter l'import
        </button>
      </div>
    </div>

    <!-- Résultat de l'exécution -->
    <div v-if="execution" class="bg-green-50 border border-green-200 rounded-xl p-6">
      <div class="flex items-start gap-3">
        <UIcon name="i-lucide-check-circle-2" class="w-6 h-6 text-green-700 shrink-0" />
        <div>
          <p class="text-sm font-bold text-green-900">Import terminé</p>
          <p class="text-xs text-green-800 mt-1">{{ execution.message }}</p>
          <div class="flex flex-wrap gap-4 mt-3 text-xs font-semibold text-green-900">
            <span>{{ execution.crees }} création(s)</span>
            <span>{{ execution.mis_a_jour }} mise(s) à jour</span>
            <span v-if="execution.ignores">{{ execution.ignores }} ignorée(s)</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Historique -->
    <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      <div class="p-5 border-b border-slate-100 flex items-center justify-between">
        <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider">Historique des imports</h2>
        <button type="button" class="text-xs font-semibold text-navy-700 hover:text-navy-900" @click="chargerHistorique">
          Actualiser
        </button>
      </div>
      <div v-if="chargementHistorique" class="p-8 text-center text-sm text-slate-500">
        <UIcon name="i-lucide-loader-2" class="w-5 h-5 animate-spin text-green-600 mx-auto mb-2" />
        Chargement…
      </div>
      <div v-else-if="historique.length === 0" class="p-8 text-center text-sm text-slate-500">
        Aucun import pour ce dossier. Commencez par télécharger un modèle.
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr>
              <th class="px-5 py-3 text-left">Date</th>
              <th class="px-5 py-3 text-left">Type</th>
              <th class="px-5 py-3 text-left">Fichier</th>
              <th class="px-5 py-3 text-left">Statut</th>
              <th class="px-5 py-3 text-right">Lignes</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="job in historique" :key="job.id" class="hover:bg-slate-50">
              <td class="px-5 py-3 text-slate-600 whitespace-nowrap">{{ formaterDate(job.created_at) }}</td>
              <td class="px-5 py-3 font-semibold text-navy-900">{{ typeCourantLabel(job.type_import) }}</td>
              <td class="px-5 py-3 text-slate-600">{{ job.fichier_nom }}</td>
              <td class="px-5 py-3">
                <span class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border" :class="statutCouleur(job.statut)">
                  {{ statutLabel(job.statut) }}
                </span>
              </td>
              <td class="px-5 py-3 text-right text-slate-600">
                {{ job.lignes_valides }} / {{ job.total_lignes }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
