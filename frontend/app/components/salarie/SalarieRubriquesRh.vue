<script setup>
/**
 * Onglets RH de la fiche salarié : entretiens, santé, formations, absences,
 * prêts, contrats RH, services et archivage des documents.
 */
const props = defineProps({
  salarieId: { type: [String, Number], required: true },
  dossierId: { type: [String, Number], required: true },
  activeTab: { type: String, required: true }
})
const emit = defineEmits(['compteurs'])
const salarieId = props.salarieId
const dossierId = props.dossierId

const { get, post } = useApi()
const toast = useToast()

// Rubriques RH : une liste et un formulaire chacune (voir useRessourceRh).

const {
  liste: entretiens, showForm: showEntretienForm, editing: editingEntretien, form: formEntretien,
  save: saveEntretien, edit: editEntretien, remove: deleteEntretien, cancel: cancelEntretien
} = useRessourceRh({
  salarieId,
  collection: 'entretiens',
  formVide: () => ({ date_entretien: '', nom_evaluateur: '', note_globale: null, commentaires: '' }),
  champsDate: ['date_entretien'],
  messages: {
    cree: 'Entretien enregistré avec succès.',
    modifie: 'Entretien mis à jour avec succès.',
    supprime: 'Entretien supprimé.',
    confirmation: 'Supprimer cet entretien définitivement ?'
  },
})

const {
  liste: visites, showForm: showVisiteForm, editing: editingVisite, form: formVisite,
  save: saveVisite, edit: editVisite, remove: deleteVisite, cancel: cancelVisite
} = useRessourceRh({
  salarieId,
  collection: 'visites-medicales',
  formVide: () => ({ date_visite: '', type_visite: 'Embauche', aptitude: 'Apte', prochaine_visite: '' }),
  champsDate: ['date_visite', 'prochaine_visite'],
  messages: {
    cree: 'Visite médicale enregistrée.',
    modifie: 'Visite médicale mise à jour.',
    supprime: 'Visite médicale supprimée.',
    confirmation: 'Supprimer cette visite médicale ?'
  },
})

const {
  liste: formations, showForm: showFormationForm, editing: editingFormation, form: formFormation,
  save: saveFormation, edit: editFormation, remove: deleteFormation, cancel: cancelFormation
} = useRessourceRh({
  salarieId,
  collection: 'formations',
  formVide: () => ({ intitule_formation: '', organisme: '', date_debut: '', date_fin: '', statut_formation: 'Demandée' }),
  champsDate: ['date_debut', 'date_fin'],
  messages: {
    cree: 'Formation enregistrée.',
    modifie: 'Formation mise à jour.',
    supprime: 'Formation supprimée.',
    confirmation: 'Supprimer cette formation ?'
  },
})

const {
  liste: absences, showForm: showAbsenceForm, editing: editingAbsence, form: formAbsence,
  save: saveAbsence, edit: editAbsence, remove: deleteAbsence, cancel: cancelAbsence
} = useRessourceRh({
  salarieId,
  collection: 'absences-hr',
  formVide: () => ({ type_absence: 'Congés payés', date_debut_absence: '', date_fin_absence: '', justificatif_fourni: false }),
  champsDate: ['date_debut_absence', 'date_fin_absence'],
  messages: {
    cree: 'Absence enregistrée.',
    modifie: 'Absence mise à jour.',
    supprime: 'Absence supprimée.',
    confirmation: 'Supprimer cette absence ?'
  },
})

const {
  liste: prets, showForm: showPretForm, editing: editingPret, form: formPret,
  save: savePret, edit: editPret, remove: deletePret, cancel: cancelPret
} = useRessourceRh({
  salarieId,
  collection: 'prets',
  formVide: () => ({ montant_pret: 0, date_deblocage: '', montant_mensualite: 0, reste_a_rembourser: 0 }),
  champsDate: ['date_deblocage'],
  messages: {
    cree: 'Prêt enregistré.',
    modifie: 'Prêt mis à jour.',
    supprime: 'Prêt supprimé.',
    confirmation: 'Supprimer ce prêt ?'
  },
})

const {
  liste: contratsHr, showForm: showContratHrForm, editing: editingContratHr, form: formContratHr,
  save: saveContratHr, edit: editContratHr, remove: deleteContratHr, cancel: cancelContratHr
} = useRessourceRh({
  salarieId,
  collection: 'contrats-info',
  formVide: () => ({ type_contrat: 'CDI', date_embauche: '', date_fin_contrat: '', fin_periode_essai: '' }),
  champsDate: ['date_embauche', 'date_fin_contrat', 'fin_periode_essai'],
  messages: {
    cree: 'Infos contrat enregistrées.',
    modifie: 'Infos contrat mises à jour.',
    supprime: 'Contrat RH supprimé.',
    confirmation: 'Supprimer ce contrat RH ?'
  },
})

const {
  liste: services, showForm: showServiceForm, editing: editingService, form: formService,
  save: saveService, edit: editService, remove: deleteService, cancel: cancelService
} = useRessourceRh({
  salarieId,
  collection: 'services',
  formVide: () => ({ departement: '', poste_occupe: '', manager: '', dotation_materiel: '' }),
  champsDate: [],
  messages: {
    cree: 'Infos service enregistrées.',
    modifie: 'Infos service mises à jour.',
    supprime: 'Affectation supprimée.',
    confirmation: 'Supprimer cette affectation de service ?'
  },
})

const {
  liste: archivages, showForm: showArchivageForm, editing: editingArchivage, form: formArchivage,
  save: saveArchivage, edit: editArchivage, remove: deleteArchivage, cancel: cancelArchivage
} = useRessourceRh({
  salarieId,
  collection: 'archivages',
  formVide: () => ({ type_document: '', fichier_joint: '', date_ajout: '' }),
  champsDate: ['date_ajout'],
  messages: {
    cree: 'Document archivé avec succès.',
    modifie: 'Document archivé mis à jour.',
    supprime: 'Document supprimé.',
    confirmation: 'Supprimer ce document archivé ?'
  },
  preparer: async (form) => {
    let fileUrl = form.fichier_joint
    if (selectedFile.value) {
      // Upload file first
      const formData = new FormData()
      formData.append('file', selectedFile.value)
      const uploadRes = await post(`/salaries/${salarieId}/upload-document`, formData)
      fileUrl = uploadRes.url
    }
    return { type_document: form.type_document, date_ajout: form.date_ajout, fichier_joint: fileUrl }
  },
  surReinitialisation: () => {
    selectedFile.value = null
  },
})

const dossierDepartements = ref([])

// File upload state
const selectedFile = ref(null)
const config = useRuntimeConfig()
const apiBase = resoudreApiBase(config.public.apiBase)

const onFileSelected = (event) => {
  selectedFile.value = event.target.files[0]
}

/**
 * Télécharge une pièce jointe RH.
 *
 * L'URL stockée contient déjà le préfixe `/api/v1` alors que `apiBase` le
 * contient aussi : on ne conserve que le chemin, sinon l'appel part sur
 * `/api/v1/api/v1/...`. Le jeton est envoyé en en-tête, car un simple lien
 * ne peut pas s'authentifier auprès de l'endpoint protégé.
 */
const telechargerDocument = async (url) => {
  if (!url) return
  const chemin = url.startsWith('/uploads/')
    // Anciennes pièces jointes : le fichier est désormais servi par l'API.
    ? `/salaries/documents/${url.split('/uploads/').pop()}`
    : (url.includes('/api/v1') ? url.slice(url.indexOf('/api/v1') + '/api/v1'.length) : url)
  try {
    const { token } = useSupabase()
    const reponse = await fetch(`${apiBase}${chemin}`, {
      headers: { Authorization: `Bearer ${token.value}` }
    })
    if (!reponse.ok) throw new Error(`HTTP ${reponse.status}`)

    const blob = await reponse.blob()
    const nom = decodeURIComponent(chemin.split('/').pop() || 'document')
    const lien = document.createElement('a')
    lien.href = URL.createObjectURL(blob)
    lien.download = nom
    lien.click()
    URL.revokeObjectURL(lien.href)
  } catch (e) {
    console.error('Téléchargement du document impossible :', e)
    toast.add({
      title: 'Téléchargement impossible',
      description: 'Le document n\'a pas pu être récupéré.',
      color: 'danger'
    })
  }
}

const chargerRubriques = async () => {
  try {
    const [entList, visList, formList, absList, pretList, cHrList, servList, archList, deptsList] = await Promise.all([
      get(`/salaries/${salarieId}/entretiens`),
      get(`/salaries/${salarieId}/visites-medicales`),
      get(`/salaries/${salarieId}/formations`),
      get(`/salaries/${salarieId}/absences-hr`),
      get(`/salaries/${salarieId}/prets`),
      get(`/salaries/${salarieId}/contrats-info`),
      get(`/salaries/${salarieId}/services`),
      get(`/salaries/${salarieId}/archivages`),
      get(`/dossiers/${dossierId}/departements`)
    ])
    entretiens.value = entList || []
    visites.value = visList || []
    formations.value = formList || []
    absences.value = absList || []
    prets.value = pretList || []
    contratsHr.value = cHrList || []
    services.value = servList || []
    archivages.value = archList || []
    dossierDepartements.value = deptsList || []
  } catch (err) {
    console.error("Erreur lors de la récupération des infos RH complémentaires:", err)
  }
}

// La page affiche l'effectif de chaque rubrique dans le libellé de son onglet.
watchEffect(() => {
  emit('compteurs', {
    entretiens: entretiens.value.length,
    visites: visites.value.length,
    formations: formations.value.length,
    absences: absences.value.length,
    prets: prets.value.length,
    contratsHr: contratsHr.value.length,
    services: services.value.length,
    archivages: archivages.value.length
  })
})

onMounted(chargerRubriques)
</script>

<template>
  <div class="contents">
    <!-- Tab 3: Entretiens -->
    <div v-show="activeTab === 'entretiens'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-navy-900">Entretiens Annuels d'Évaluation</h3>
            <p class="text-xs text-slate-500">Historique des entretiens d'évaluation du salarié.</p>
          </div>
          <button 
            v-if="!showEntretienForm"
            @click="showEntretienForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouvel Entretien
          </button>
        </div>

        <!-- Form -->
        <form v-if="showEntretienForm" @submit.prevent="saveEntretien" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-navy-900">{{ editingEntretien ? 'Modifier l\'entretien' : 'Saisir un nouvel entretien' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de l'entretien</label>
              <input type="date" v-model="formEntretien.date_entretien" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Nom de l'évaluateur</label>
              <input type="text" v-model="formEntretien.nom_evaluateur" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Note globale (sur 20)</label>
              <input type="number" step="0.1" min="0" max="20" v-model.number="formEntretien.note_globale" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase">Commentaires et objectifs</label>
            <textarea v-model="formEntretien.commentaires" rows="3" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"></textarea>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelEntretien" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="entretiens.length === 0 && !showEntretienForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun entretien enregistré.
        </div>
        <div v-else-if="!showEntretienForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Date</th>
                <th scope="col" class="px-6 py-3 text-left">Évaluateur</th>
                <th scope="col" class="px-6 py-3 text-left">Note Globale</th>
                <th scope="col" class="px-6 py-3 text-left">Commentaires</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in entretiens" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-mono">{{ item.date_entretien }}</td>
                <td class="px-6 py-4 font-medium text-slate-800">{{ item.nom_evaluateur }}</td>
                <td class="px-6 py-4 font-mono font-semibold">{{ item.note_globale !== null ? item.note_globale + '/20' : '-' }}</td>
                <td class="px-6 py-4 text-slate-650 max-w-xs truncate">{{ item.commentaires || '-' }}</td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editEntretien(item)" class="text-navy-700 hover:text-navy-900 text-xs font-semibold">Modifier</button>
                  <button @click="deleteEntretien(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


    <!-- Tab 4: Santé (Visite Médicale) -->
    <div v-show="activeTab === 'sante'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-navy-900">Visites Médicales</h3>
            <p class="text-xs text-slate-500">Suivi médical et avis d'aptitude du salarié.</p>
          </div>
          <button 
            v-if="!showVisiteForm"
            @click="showVisiteForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouvelle Visite
          </button>
        </div>

        <!-- Form -->
        <form v-if="showVisiteForm" @submit.prevent="saveVisite" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-navy-900">{{ editingVisite ? 'Modifier la visite' : 'Saisir une nouvelle visite' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de la visite</label>
              <input type="date" v-model="formVisite.date_visite" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Type de visite</label>
              <select v-model="formVisite.type_visite" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="Embauche">Embauche</option>
                <option value="Reprise">Reprise</option>
                <option value="Périodique">Périodique</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Avis d'aptitude</label>
              <select v-model="formVisite.aptitude" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="Apte">Apte</option>
                <option value="Inapte">Inapte</option>
                <option value="Apte avec réserves">Apte avec réserves</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date prochaine visite</label>
              <input type="date" v-model="formVisite.prochaine_visite" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelVisite" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="visites.length === 0 && !showVisiteForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucune visite médicale enregistrée.
        </div>
        <div v-else-if="!showVisiteForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Date Visite</th>
                <th scope="col" class="px-6 py-3 text-left">Type de Visite</th>
                <th scope="col" class="px-6 py-3 text-left">Avis d'Aptitude</th>
                <th scope="col" class="px-6 py-3 text-left">Prochaine Visite</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in visites" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-mono">{{ item.date_visite }}</td>
                <td class="px-6 py-4 font-medium text-slate-800">{{ item.type_visite }}</td>
                <td class="px-6 py-4">
                  <span 
                    :class="[
                      item.aptitude === 'Apte' ? 'bg-green-50 text-green-700 border-green-200' : item.aptitude === 'Inapte' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-amber-50 text-amber-700 border-amber-200',
                      'px-2 py-0.5 rounded text-[10px] uppercase font-bold border'
                    ]"
                  >
                    {{ item.aptitude }}
                  </span>
                </td>
                <td class="px-6 py-4 font-mono text-slate-600">{{ item.prochaine_visite || '-' }}</td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editVisite(item)" class="text-navy-700 hover:text-navy-900 text-xs font-semibold">Modifier</button>
                  <button @click="deleteVisite(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


    <!-- Tab 5: Formations -->
    <div v-show="activeTab === 'formations'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-navy-900">Suivi des Formations</h3>
            <p class="text-xs text-slate-500">Formations demandées, en cours ou terminées.</p>
          </div>
          <button 
            v-if="!showFormationForm"
            @click="showFormationForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouvelle Formation
          </button>
        </div>

        <!-- Form -->
        <form v-if="showFormationForm" @submit.prevent="saveFormation" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-navy-900">{{ editingFormation ? 'Modifier la formation' : 'Saisir une nouvelle formation' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Intitulé de la formation</label>
              <input type="text" v-model="formFormation.intitule_formation" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Organisme de formation</label>
              <input type="text" v-model="formFormation.organisme" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de début</label>
              <input type="date" v-model="formFormation.date_debut" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de fin</label>
              <input type="date" v-model="formFormation.date_fin" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Statut</label>
              <select v-model="formFormation.statut_formation" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="Demandée">Demandée</option>
                <option value="En cours">En cours</option>
                <option value="Terminée">Terminée</option>
              </select>
            </div>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelFormation" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="formations.length === 0 && !showFormationForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucune formation enregistrée.
        </div>
        <div v-else-if="!showFormationForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Intitulé</th>
                <th scope="col" class="px-6 py-3 text-left">Organisme</th>
                <th scope="col" class="px-6 py-3 text-left">Période</th>
                <th scope="col" class="px-6 py-3 text-left">Statut</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in formations" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-medium text-slate-800">{{ item.intitule_formation }}</td>
                <td class="px-6 py-4 text-slate-700">{{ item.organisme }}</td>
                <td class="px-6 py-4 font-mono text-xs text-slate-650">Du {{ item.date_debut }} au {{ item.date_fin }}</td>
                <td class="px-6 py-4">
                  <span 
                    :class="[
                      item.statut_formation === 'Terminée' ? 'bg-green-50 text-green-700 border-green-200' : item.statut_formation === 'En cours' ? 'bg-navy-50 text-navy-700 border-navy-200' : 'bg-slate-100 text-slate-650 border-slate-200',
                      'px-2 py-0.5 rounded text-[10px] uppercase font-bold border'
                    ]"
                  >
                    {{ item.statut_formation }}
                  </span>
                </td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editFormation(item)" class="text-navy-700 hover:text-navy-900 text-xs font-semibold">Modifier</button>
                  <button @click="deleteFormation(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


    <!-- Tab 6: Absences -->
    <div v-show="activeTab === 'absences'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-navy-900">Saisie et Suivi des Absences</h3>
            <p class="text-xs text-slate-500">Congés, maladies et autres motifs d'absences.</p>
          </div>
          <button 
            v-if="!showAbsenceForm"
            @click="showAbsenceForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouvelle Absence
          </button>
        </div>

        <!-- Form -->
        <form v-if="showAbsenceForm" @submit.prevent="saveAbsence" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-navy-900">{{ editingAbsence ? 'Modifier l\'absence' : 'Saisir une nouvelle absence' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Motif de l'absence</label>
              <select v-model="formAbsence.type_absence" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="Congés payés">Congés payés</option>
                <option value="Maladie">Maladie</option>
                <option value="Maternité/Paternité">Maternité/Paternité</option>
                <option value="Sans solde">Sans solde</option>
              </select>
            </div>
            <div class="flex items-end pb-2">
              <div class="flex items-center space-x-2">
                <input type="checkbox" id="justif" v-model="formAbsence.justificatif_fourni" class="rounded border-slate-300 text-green-600 focus:ring-green-500 h-4 w-4" />
                <label for="justif" class="text-sm font-semibold text-slate-700">Justificatif fourni</label>
              </div>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de début</label>
              <input type="date" v-model="formAbsence.date_debut_absence" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de fin</label>
              <input type="date" v-model="formAbsence.date_fin_absence" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelAbsence" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="absences.length === 0 && !showAbsenceForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucune absence enregistrée.
        </div>
        <div v-else-if="!showAbsenceForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Motif</th>
                <th scope="col" class="px-6 py-3 text-left">Période</th>
                <th scope="col" class="px-6 py-3 text-left">Justificatif</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in absences" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-medium text-slate-800">{{ item.type_absence }}</td>
                <td class="px-6 py-4 font-mono text-xs text-slate-650">Du {{ item.date_debut_absence }} au {{ item.date_fin_absence }}</td>
                <td class="px-6 py-4">
                  <span 
                    :class="[
                      item.justificatif_fourni ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200',
                      'px-2 py-0.5 rounded text-[10px] uppercase font-bold border'
                    ]"
                  >
                    {{ item.justificatif_fourni ? 'Oui' : 'Non' }}
                  </span>
                </td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editAbsence(item)" class="text-navy-700 hover:text-navy-900 text-xs font-semibold">Modifier</button>
                  <button @click="deleteAbsence(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


    <!-- Tab 7: Prêts -->
    <div v-show="activeTab === 'prets'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-navy-900">Prêts accordés au Salarié</h3>
            <p class="text-xs text-slate-500">Suivi des retenues mensuelles et soldes des prêts.</p>
          </div>
          <button 
            v-if="!showPretForm"
            @click="showPretForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouveau Prêt
          </button>
        </div>

        <!-- Form -->
        <form v-if="showPretForm" @submit.prevent="savePret" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-navy-900">{{ editingPret ? 'Modifier le prêt' : 'Saisir un nouveau prêt' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Montant total accordé (FCFA)</label>
              <input type="number" v-model.number="formPret.montant_pret" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de déblocage</label>
              <input type="date" v-model="formPret.date_deblocage" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Retenue mensuelle (FCFA)</label>
              <input type="number" v-model.number="formPret.montant_mensualite" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Reste à rembourser (FCFA)</label>
              <input type="number" v-model.number="formPret.reste_a_rembourser" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelPret" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="prets.length === 0 && !showPretForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun prêt enregistré.
        </div>
        <div v-else-if="!showPretForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Montant Prêt</th>
                <th scope="col" class="px-6 py-3 text-left">Date Déblocage</th>
                <th scope="col" class="px-6 py-3 text-left">Mensualité Retenue</th>
                <th scope="col" class="px-6 py-3 text-left">Reste à Rembourser</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in prets" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-mono font-semibold text-slate-800">{{ item.montant_pret.toLocaleString() }} FCFA</td>
                <td class="px-6 py-4 font-mono">{{ item.date_deblocage }}</td>
                <td class="px-6 py-4 font-mono text-slate-650">{{ item.montant_mensualite.toLocaleString() }} FCFA</td>
                <td class="px-6 py-4 font-mono text-red-650 font-bold">{{ item.reste_a_rembourser.toLocaleString() }} FCFA</td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editPret(item)" class="text-navy-700 hover:text-navy-900 text-xs font-semibold">Modifier</button>
                  <button @click="deletePret(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


    <!-- Tab 8: Contrats HR -->
    <div v-show="activeTab === 'contrats_hr'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-navy-900">Suivi Administratif des Contrats</h3>
            <p class="text-xs text-slate-500">Dates clés, périodes d'essai et types de contrats RH.</p>
          </div>
          <button 
            v-if="!showContratHrForm"
            @click="showContratHrForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouveau Contrat HR
          </button>
        </div>

        <!-- Form -->
        <form v-if="showContratHrForm" @submit.prevent="saveContratHr" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-navy-900">{{ editingContratHr ? 'Modifier le contrat' : 'Saisir un nouveau contrat' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Type de contrat</label>
              <select v-model="formContratHr.type_contrat" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="CDI">CDI</option>
                <option value="CDD">CDD</option>
                <option value="Apprentissage">Apprentissage</option>
                <option value="Stage">Stage</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date d'embauche</label>
              <input type="date" v-model="formContratHr.date_embauche" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de fin</label>
              <input type="date" v-model="formContratHr.date_fin_contrat" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Fin période d'essai</label>
              <input type="date" v-model="formContratHr.fin_periode_essai" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelContratHr" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="contratsHr.length === 0 && !showContratHrForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun contrat HR enregistré.
        </div>
        <div v-else-if="!showContratHrForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Type Contrat</th>
                <th scope="col" class="px-6 py-3 text-left">Date Embauche</th>
                <th scope="col" class="px-6 py-3 text-left">Date Fin</th>
                <th scope="col" class="px-6 py-3 text-left">Fin Période Essai</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in contratsHr" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-semibold text-slate-800">{{ item.type_contrat }}</td>
                <td class="px-6 py-4 font-mono">{{ item.date_embauche }}</td>
                <td class="px-6 py-4 font-mono text-slate-650">{{ item.date_fin_contrat || 'Illimité (CDI)' }}</td>
                <td class="px-6 py-4 font-mono text-slate-600">{{ item.fin_periode_essai || '-' }}</td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editContratHr(item)" class="text-navy-700 hover:text-navy-900 text-xs font-semibold">Modifier</button>
                  <button @click="deleteContratHr(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


    <!-- Tab 9: Services -->
    <div v-show="activeTab === 'services'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-navy-900">Département, Poste & Matériel</h3>
            <p class="text-xs text-slate-500">Service d'affectation, manager et équipements remis.</p>
          </div>
          <button 
            v-if="!showServiceForm"
            @click="showServiceForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouvelle Affectation
          </button>
        </div>

        <!-- Form -->
        <form v-if="showServiceForm" @submit.prevent="saveService" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-navy-900">{{ editingService ? 'Modifier l\'affectation' : 'Saisir une nouvelle affectation' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Département / Service</label>
              <select v-model="formService.departement" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select">
                <option value="" disabled>-- Choisir un service --</option>
                <option v-for="d in dossierDepartements" :key="d.id" :value="d.nom">
                  {{ d.nom }} {{ d.code ? `(${d.code})` : '' }}
                </option>
              </select>
              <p v-if="dossierDepartements.length === 0" class="mt-1 text-xs text-amber-600 font-medium">
                <UIcon name="i-lucide-alert-triangle" class="w-3.5 h-3.5 inline mr-1 align-text-bottom" />
                Aucun département configuré pour ce dossier. Veuillez d'abord en ajouter dans la fiche du dossier client.
              </p>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Poste occupé</label>
              <input type="text" v-model="formService.poste_occupe" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Responsable hiérarchique</label>
              <input type="text" v-model="formService.manager" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase">Matériel confié (PC, Téléphone, Voiture...)</label>
            <textarea v-model="formService.dotation_materiel" rows="3" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" placeholder="Ex: PC Dell Latitude, iPhone 13, Clés bureau..."></textarea>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelService" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="services.length === 0 && !showServiceForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucune affectation de service enregistrée.
        </div>
        <div v-else-if="!showServiceForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Service</th>
                <th scope="col" class="px-6 py-3 text-left">Poste</th>
                <th scope="col" class="px-6 py-3 text-left">Responsable (Manager)</th>
                <th scope="col" class="px-6 py-3 text-left">Matériel Dotation</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in services" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-semibold text-slate-800">{{ item.departement }}</td>
                <td class="px-6 py-4 text-slate-700">{{ item.poste_occupe }}</td>
                <td class="px-6 py-4 font-medium text-slate-650">{{ item.manager }}</td>
                <td class="px-6 py-4 text-slate-500 max-w-xs truncate">{{ item.dotation_materiel || '-' }}</td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editService(item)" class="text-navy-700 hover:text-navy-900 text-xs font-semibold">Modifier</button>
                  <button @click="deleteService(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>


    <!-- Tab 10: Archivage -->
    <div v-show="activeTab === 'archivage'" class="space-y-6">
      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 class="text-lg font-bold text-navy-900">Archivage de Documents</h3>
            <p class="text-xs text-slate-500">Stockage et dépôt de documents liés au salarié (CNI, RIB, etc.).</p>
          </div>
          <button 
            v-if="!showArchivageForm"
            @click="showArchivageForm = true"
            class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <UIcon name="i-lucide-file-plus" class="w-3.5 h-3.5" />
            Nouveau Document
          </button>
        </div>

        <!-- Form -->
        <form v-if="showArchivageForm" @submit.prevent="saveArchivage" class="space-y-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
          <h4 class="font-semibold text-sm text-navy-900">{{ editingArchivage ? 'Modifier le document' : 'Archiver un nouveau document' }}</h4>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Type de document</label>
              <input type="text" v-model="formArchivage.type_document" placeholder="Ex: RIB, CNI, Diplôme..." required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Date de dépôt</label>
              <input type="date" v-model="formArchivage.date_ajout" required class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase">Fichier joint</label>
              <input type="file" @change="onFileSelected" :required="!editingArchivage" class="mt-1 block w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100" />
              <div v-if="formArchivage.fichier_joint" class="text-xs text-slate-500 mt-1">
                Fichier actuel : <button type="button" @click="telechargerDocument(formArchivage.fichier_joint)" class="text-navy-700 hover:underline font-medium">{{ formArchivage.fichier_joint.split('/').pop() }}</button>
              </div>
            </div>
          </div>
          <div class="flex justify-end space-x-2">
            <button type="button" @click="cancelArchivage" class="px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-100 rounded-lg text-xs font-semibold">Annuler</button>
            <button type="submit" class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold shadow-sm">Enregistrer</button>
          </div>
        </form>

        <!-- List -->
        <div v-if="archivages.length === 0 && !showArchivageForm" class="text-center py-12 text-slate-500 italic text-sm">
          Aucun document archivé.
        </div>
        <div v-else-if="!showArchivageForm" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th scope="col" class="px-6 py-3 text-left">Type de Document</th>
                <th scope="col" class="px-6 py-3 text-left">Date de Dépôt</th>
                <th scope="col" class="px-6 py-3 text-left">Fichier</th>
                <th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 bg-white">
              <tr v-for="item in archivages" :key="item.id" class="hover:bg-slate-50">
                <td class="px-6 py-4 font-semibold text-slate-800">{{ item.type_document }}</td>
                <td class="px-6 py-4 font-mono">{{ item.date_ajout }}</td>
                <td class="px-6 py-4">
                  <button
                    v-if="item.fichier_joint"
                    type="button"
                    class="inline-flex items-center gap-1 text-navy-700 hover:text-navy-900 font-semibold hover:underline"
                    @click="telechargerDocument(item.fichier_joint)"
                  >
                    <UIcon name="i-lucide-download" class="w-3.5 h-3.5" />
                    Télécharger
                  </button>
                  <span v-else class="text-slate-400 italic">Aucun fichier</span>
                </td>
                <td class="px-6 py-4 text-right space-x-2">
                  <button @click="editArchivage(item)" class="text-navy-700 hover:text-navy-900 text-xs font-semibold">Modifier</button>
                  <button @click="deleteArchivage(item.id)" class="text-red-600 hover:text-red-800 text-xs font-semibold">Supprimer</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
