<script setup>
const { get, put } = useApi()
const toast = useToast()

const claims = ref([])
const loading = ref(true)
const selectedClaim = ref(null)
const processModalOpen = ref(false)
const claimStatus = ref('traite')
const managerComment = ref('')
const submitting = ref(false)

const fetchClaims = async () => {
  loading.value = true
  try {
    claims.value = await get('/reclamations')
  } catch (e) {
    console.error("Error fetching claims:", e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchClaims()
})

const getPeriodLabel = (mois, annee) => {
  const months = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
  ]
  return `${months[mois - 1]} ${annee}`
}

const handleOpenProcessModal = (c) => {
  selectedClaim.value = c
  claimStatus.value = c.statut === 'en_attente' ? 'traite' : c.statut
  managerComment.value = c.commentaire_gestionnaire || ''
  processModalOpen.value = true
}

const handleSaveProcess = async () => {
  submitting.value = true
  try {
    await put(`/reclamations/${selectedClaim.value.id}`, {
      statut: claimStatus.value,
      commentaire_gestionnaire: managerComment.value
    })
    toast.add({ title: 'Succès', description: 'Le statut de la réclamation a été mis à jour.', color: 'success' })
    processModalOpen.value = false
    await fetchClaims()
  } catch (e) {
    console.error("Error updating claim:", e)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white border-2 border-slate-200 p-6 shadow-flat border-t-4 border-t-green-600 flex justify-between items-center">
      <div>
        <h1 class="text-2xl font-black text-slate-900 uppercase">Gestion des Réclamations</h1>
        <p class="text-sm text-slate-500 font-medium mt-1">
          Visualisez et traitez les réclamations soumises par les salariés sur leurs bulletins de paie.
        </p>
      </div>
    </div>

    <!-- Main List Card -->
    <div class="bg-white border-2 border-slate-200 shadow-flat rounded-none">
      <div class="px-6 py-4 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
        <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider">Réclamations reçues</h2>
        <span class="px-2 py-0.5 text-[10px] bg-green-50 text-green-700 border border-green-200 font-bold uppercase tracking-wider">
          {{ claims.length }} total
        </span>
      </div>

      <div v-if="loading" class="p-12 text-center text-slate-500 font-medium">
        Chargement des réclamations...
      </div>
      <div v-else-if="claims.length === 0" class="p-12 text-center text-slate-500 font-medium">
        Aucune réclamation n'a été soumise pour le moment.
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200">
          <thead class="bg-slate-50 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            <tr>
              <th scope="col" class="px-6 py-3 text-left">Salarié</th>
              <th scope="col" class="px-6 py-3 text-left">Bulletin concerné</th>
              <th scope="col" class="px-6 py-3 text-left">Sujet / Motif</th>
              <th scope="col" class="px-6 py-3 text-left">Description</th>
              <th scope="col" class="px-6 py-3 text-center">Date d'envoi</th>
              <th scope="col" class="px-6 py-3 text-center">Statut</th>
              <th scope="col" class="px-6 py-3 text-center">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-150 text-sm text-slate-700">
            <tr v-for="c in claims" :key="c.id" class="hover:bg-slate-50/50 transition-colors">
              <td class="px-6 py-4 font-bold text-slate-900">
                {{ c.salarie_prenom }} {{ c.salarie_nom?.toUpperCase() }}
              </td>
              <td class="px-6 py-4 uppercase font-semibold text-slate-650">
                {{ getPeriodLabel(c.bulletin_mois, c.bulletin_annee) }}
              </td>
              <td class="px-6 py-4 font-bold text-slate-800">
                {{ c.sujet }}
              </td>
              <td class="px-6 py-4 text-slate-600 max-w-xs truncate" :title="c.description">
                {{ c.description }}
              </td>
              <td class="px-6 py-4 text-center font-mono text-xs text-slate-500">
                {{ new Date(c.created_at).toLocaleDateString('fr-FR') }}
              </td>
              <td class="px-6 py-4 text-center">
                <span class="inline-block px-2.5 py-0.5 text-[9px] font-black uppercase border rounded-none tracking-wider"
                  :class="[
                    c.statut === 'en_attente' ? 'bg-amber-50 border-amber-300 text-amber-700' :
                    c.statut === 'traite' ? 'bg-green-50 border-green-300 text-green-700' :
                    'bg-slate-100 border-slate-300 text-slate-650'
                  ]"
                >
                  {{ c.statut === 'en_attente' ? 'À traiter' : c.statut === 'traite' ? 'Traitée' : 'Rejetée' }}
                </span>
              </td>
              <td class="px-6 py-4 text-center">
                <button 
                  @click="handleOpenProcessModal(c)" 
                  class="px-2.5 py-1 text-[11px] font-bold uppercase bg-slate-50 border-2 border-slate-200 text-slate-800 hover:bg-slate-100 rounded-none shadow-sm transition-colors cursor-pointer"
                >
                  Traiter / Répondre
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal: Process Claim -->
    <UModal v-model:open="processModalOpen" title="Traiter la réclamation">
      <template #content>
        <div v-if="selectedClaim" class="p-6 space-y-4 bg-white border border-slate-200 max-w-md mx-auto">
          <h2 class="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Répondre à la réclamation</h2>
          
          <div class="p-3 bg-slate-50 border border-slate-200 text-xs space-y-1">
            <p><span class="font-bold">Salarié :</span> {{ selectedClaim.salarie_prenom }} {{ selectedClaim.salarie_nom?.toUpperCase() }}</p>
            <p><span class="font-bold">Bulletin :</span> {{ getPeriodLabel(selectedClaim.bulletin_mois, selectedClaim.bulletin_annee) }}</p>
            <p><span class="font-bold">Motif :</span> {{ selectedClaim.sujet }}</p>
            <p class="mt-2 text-slate-650 leading-relaxed italic"><span class="font-bold not-italic">Message :</span> "{{ selectedClaim.description }}"</p>
          </div>

          <div class="space-y-3">
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Statut du traitement</label>
              <select v-model="claimStatus" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white select">
                <option value="en_attente">À traiter / En attente</option>
                <option value="traite">Acceptée & Traitée</option>
                <option value="rejete">Rejetée</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Commentaire / Réponse pour le salarié</label>
              <textarea v-model="managerComment" rows="4" placeholder="Indiquez au salarié les mesures prises ou la justification du traitement..." class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white" required></textarea>
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button type="button" @click="processModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-xs font-bold rounded-none hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
              Annuler
            </button>
            <button type="button" @click="handleSaveProcess" :disabled="submitting" class="px-4 py-2 text-xs font-bold bg-green-600 hover:bg-green-700 text-white rounded-none shadow-flat transition-colors uppercase tracking-wider cursor-pointer disabled:bg-slate-300">
              {{ submitting ? "Enregistrement..." : "Valider le traitement" }}
            </button>
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>
