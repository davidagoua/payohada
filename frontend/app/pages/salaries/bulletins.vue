<script setup>
const { get, post } = useApi()
const { user } = useSupabase()
const toast = useToast()

const bulletins = ref([])
const claims = ref([])
const loading = ref(true)
const selectedBulletin = ref(null)
const previewModalOpen = ref(false)

// Change password state
const showPasswordForm = ref(false)
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const changingPassword = ref(false)

// Claim state
const claimModalOpen = ref(false)
const claimSujet = ref('')
const claimDescription = ref('')
const submittingClaim = ref(false)

// Detect default password
const isUsingDefaultPassword = computed(() => {
  // If the user's password is the default one, or we show warning if they haven't changed it
  // We can let them dismiss it, or verify via email/status
  return true // For display purposes, we prompt them until they change it or we check their password.
})

const fetchMyData = async () => {
  loading.value = true
  try {
    bulletins.value = await get('/salaries/me/bulletins')
    claims.value = await get('/reclamations')
  } catch (e) {
    console.error("Error fetching employee data:", e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchMyData()
})

const getPeriodLabel = (mois, annee) => {
  const months = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
  ]
  return `${months[mois - 1]} ${annee}`
}

const formatXOF = (amount) => {
  if (amount === undefined || amount === null) return '0 FCFA'
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XOF', minimumFractionDigits: 0 }).format(amount).replace('XOF', 'FCFA')
}

const formatPercent = (val) => {
  if (!val) return '-'
  return `${val.toFixed(2)}%`
}

// Compute line subdivisions for preview
const grossLines = computed(() => {
  if (!selectedBulletin.value) return []
  return selectedBulletin.value.lignes.filter(l => {
    const code = l.code.toUpperCase()
    return code === 'BASE' || code === 'SURSALAIRE' || code.startsWith('10') || code.startsWith('11') || code.startsWith('12') || code.startsWith('13')
  })
})

const cotisationsLines = computed(() => {
  if (!selectedBulletin.value) return []
  return selectedBulletin.value.lignes.filter(l => {
    const code = l.code.toUpperCase()
    return code === 'IBS' || code === 'RICF' || code.startsWith('CNPS') || code.startsWith('CMU') || code === 'CN' || code === 'TA' || code === 'TFC'
  })
})

const otherLines = computed(() => {
  if (!selectedBulletin.value) return []
  const grossCodes = grossLines.value.map(l => l.code)
  const cotisationsCodes = cotisationsLines.value.map(l => l.code)
  return selectedBulletin.value.lignes.filter(l => !grossCodes.includes(l.code) && !cotisationsCodes.includes(l.code))
})

const handlePreview = (b) => {
  selectedBulletin.value = b
  previewModalOpen.value = true
}

const handleOpenClaimModal = (b) => {
  selectedBulletin.value = b
  claimSujet.value = `Réclamation - Bulletin de ${getPeriodLabel(b.mois, b.annee)}`
  claimDescription.value = ''
  claimModalOpen.value = true
}

const handleSendClaim = async () => {
  if (!claimSujet.value || !claimDescription.value) {
    toast.add({ title: 'Validation', description: 'Veuillez remplir le sujet et la description.', color: 'warning' })
    return
  }

  submittingClaim.value = true
  try {
    await post('/reclamations', {
      bulletin_id: selectedBulletin.value.id,
      sujet: claimSujet.value,
      description: claimDescription.value
    })
    toast.add({ title: 'Succès', description: 'Votre réclamation a été transmise avec succès.', color: 'success' })
    claimModalOpen.value = false
    await fetchMyData()
  } catch (e) {
    console.error("Error submitting claim:", e)
  } finally {
    submittingClaim.value = false
  }
}

const handleChangePassword = async () => {
  if (!oldPassword.value || !newPassword.value || !confirmPassword.value) {
    toast.add({ title: 'Validation', description: 'Veuillez remplir tous les champs.', color: 'warning' })
    return
  }

  if (newPassword.value !== confirmPassword.value) {
    toast.add({ title: 'Validation', description: 'Les nouveaux mots de passe ne correspondent pas.', color: 'warning' })
    return
  }

  changingPassword.value = true
  try {
    await post('/auth/change-password', {
      old_password: oldPassword.value,
      new_password: newPassword.value
    })
    toast.add({ title: 'Succès', description: 'Votre mot de passe a été modifié avec succès.', color: 'success' })
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    showPasswordForm.value = false
  } catch (e) {
    console.error("Error changing password:", e)
  } finally {
    changingPassword.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header Hero Banner -->
    <div class="bg-white border-2 border-slate-200 p-6 shadow-flat border-t-4 border-t-green-600 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <h1 class="text-2xl font-black text-slate-900 uppercase">Espace Salarié</h1>
        <p class="text-sm text-slate-500 font-medium mt-1">
          Bienvenue, <span class="font-bold text-slate-800">{{ user?.user_metadata?.first_name }} {{ user?.user_metadata?.last_name }}</span>. Consultez vos bulletins de paie et gérez votre compte.
        </p>
      </div>
      <div>
        <button 
          @click="showPasswordForm = !showPasswordForm" 
          class="px-4 py-2 border-2 border-slate-200 hover:bg-slate-50 text-slate-850 text-xs font-bold uppercase tracking-wider rounded-none shadow-flat transition-all cursor-pointer flex items-center gap-1.5"
        >
          <UIcon name="i-lucide-key" class="w-4 h-4 text-green-600" />
          {{ showPasswordForm ? "Masquer le formulaire" : "Modifier mon mot de passe" }}
        </button>
      </div>
    </div>

    <!-- Password Change Form -->
    <div v-if="showPasswordForm" class="bg-white border-2 border-slate-200 p-6 shadow-flat border-t-4 border-t-amber-500 max-w-lg">
      <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4">Modifier le mot de passe</h3>
      <form @submit.prevent="handleChangePassword" class="space-y-4">
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Mot de passe actuel</label>
          <input v-model="oldPassword" type="password" placeholder="Saisir l'ancien mot de passe" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white" required />
          <p class="text-[10px] text-amber-600 font-semibold mt-1">
            Si c'est votre première connexion, le mot de passe par défaut est <code class="bg-amber-50 px-1 py-0.5 border border-amber-200 font-bold font-mono text-[11px]">Payohada@123</code>.
          </p>
        </div>
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Nouveau mot de passe</label>
          <input v-model="newPassword" type="password" placeholder="Au moins 6 caractères" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white" required />
        </div>
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Confirmer le nouveau mot de passe</label>
          <input v-model="confirmPassword" type="password" placeholder="Ressaisir le nouveau mot de passe" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white" required />
        </div>
        <div class="flex justify-end pt-2">
          <button type="submit" :disabled="changingPassword" class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-xs font-bold uppercase tracking-wider rounded-none shadow-flat transition-colors cursor-pointer disabled:bg-slate-300">
            {{ changingPassword ? "Enregistrement..." : "Enregistrer" }}
          </button>
        </div>
      </form>
    </div>

    <!-- Main Workspace: Bulletins and Claims -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Left Column: Bulletins List (2/3 width) -->
      <div class="lg:col-span-2 space-y-6">
        <div class="bg-white border-2 border-slate-200 shadow-flat rounded-none">
          <!-- Table Header -->
          <div class="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider">Mes Bulletins de Salaire</h2>
            <span class="px-2 py-0.5 text-[10px] bg-green-50 text-green-700 border border-green-200 font-bold uppercase tracking-wider">
              {{ bulletins.length }} bulletins
            </span>
          </div>

          <!-- Table Content -->
          <div v-if="loading" class="p-12 text-center text-slate-500 font-medium">
            Chargement de vos bulletins...
          </div>
          <div v-else-if="bulletins.length === 0" class="p-12 text-center text-slate-500 font-medium">
            Aucun bulletin de salaire n'a été publié pour le moment.
          </div>
          <div v-else class="overflow-x-auto">
            <table class="min-w-full divide-y divide-slate-200">
              <thead class="bg-slate-50 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th scope="col" class="px-6 py-3 text-left">Période</th>
                  <th scope="col" class="px-6 py-3 text-right">Salaire Brut</th>
                  <th scope="col" class="px-6 py-3 text-right">Net à payer</th>
                  <th scope="col" class="px-6 py-3 class text-center">Statut</th>
                  <th scope="col" class="px-6 py-3 text-center">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-150 text-sm text-slate-700">
                <tr v-for="b in bulletins" :key="b.id" class="hover:bg-slate-50/50 transition-colors">
                  <td class="px-6 py-4 font-bold text-slate-900 uppercase">
                    {{ getPeriodLabel(b.mois, b.annee) }}
                  </td>
                  <td class="px-6 py-4 text-right font-mono font-medium">
                    {{ formatXOF(b.salaire_brut) }}
                  </td>
                  <td class="px-6 py-4 text-right font-mono font-bold text-green-700">
                    {{ formatXOF(b.net_a_payer) }}
                  </td>
                  <td class="px-6 py-4 text-center">
                    <span class="inline-block px-2.5 py-0.5 text-[9px] font-black uppercase border rounded-none tracking-wider"
                      :class="[
                        b.statut === 'valide'
                          ? 'bg-green-50 border-green-300 text-green-700'
                          : 'bg-amber-50 border-amber-300 text-amber-700'
                      ]"
                    >
                      {{ b.statut === 'valide' ? 'Validé' : 'Brouillon' }}
                    </span>
                  </td>
                  <td class="px-6 py-4 text-center space-x-2">
                    <button 
                      @click="handlePreview(b)" 
                      class="px-2.5 py-1 text-[11px] font-bold uppercase bg-slate-50 border-2 border-slate-200 text-slate-800 hover:bg-slate-100 rounded-none shadow-sm transition-colors cursor-pointer"
                    >
                      Visualiser
                    </button>
                    <button 
                      @click="handleOpenClaimModal(b)" 
                      class="px-2.5 py-1 text-[11px] font-bold uppercase bg-red-50 border-2 border-red-200 text-red-700 hover:bg-red-100 rounded-none shadow-sm transition-colors cursor-pointer"
                    >
                      Réclamation
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Right Column: Claims History (1/3 width) -->
      <div class="space-y-6">
        <div class="bg-white border-2 border-slate-200 shadow-flat rounded-none">
          <!-- Claims Header -->
          <div class="px-6 py-4 border-b border-slate-200 bg-slate-50/50">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider">Suivi de mes réclamations</h2>
          </div>

          <!-- Claims Content -->
          <div v-if="loading" class="p-6 text-center text-slate-400 text-xs">
            Chargement...
          </div>
          <div v-else-if="claims.length === 0" class="p-6 text-center text-slate-500 text-xs font-medium">
            Vous n'avez soumis aucune réclamation.
          </div>
          <div v-else class="divide-y divide-slate-150 max-h-[450px] overflow-y-auto">
            <div v-for="c in claims" :key="c.id" class="p-4 space-y-2 text-xs">
              <div class="flex justify-between items-start">
                <span class="font-bold text-slate-800 uppercase leading-snug">{{ c.sujet }}</span>
                <span class="px-2 py-0.5 text-[8px] font-black uppercase border rounded-none tracking-widest"
                  :class="[
                    c.statut === 'en_attente' ? 'bg-amber-50 border-amber-300 text-amber-700' :
                    c.statut === 'traite' ? 'bg-green-50 border-green-300 text-green-700' :
                    'bg-slate-100 border-slate-300 text-slate-650'
                  ]"
                >
                  {{ c.statut === 'en_attente' ? 'En cours' : c.statut === 'traite' ? 'Traitée' : 'Rejetée' }}
                </span>
              </div>
              <p class="text-slate-600 leading-normal">{{ c.description }}</p>
              <div v-if="c.commentaire_gestionnaire" class="mt-2 p-2 bg-slate-50 border-l-2 border-slate-350 text-slate-700">
                <span class="block font-bold text-[9px] uppercase text-slate-500">Réponse du gestionnaire :</span>
                {{ c.commentaire_gestionnaire }}
              </div>
              <span class="block text-[8px] text-slate-400 font-mono">Soumis le : {{ new Date(c.created_at).toLocaleDateString('fr-FR') }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: View Payslip -->
    <UModal v-model:open="previewModalOpen" title="Visualiser le bulletin">
      <template #content>
        <div v-if="selectedBulletin" class="p-6 space-y-4 bg-slate-50 border border-slate-200 max-h-[85vh] overflow-y-auto w-full max-w-4xl">
          <div class="flex justify-between items-center border-b border-slate-200 pb-2">
            <h2 class="text-md font-bold text-slate-900 uppercase">Aperçu du bulletin de paie</h2>
            <button @click="previewModalOpen = false" class="text-slate-500 hover:text-slate-800 font-bold text-sm">Fermer</button>
          </div>

          <!-- Payslip layout copied from the admin bulletin page -->
          <div class="bg-white border-2 border-slate-200 rounded-none p-6 shadow-flat text-slate-800 border-t-4 border-t-green-600 max-w-3xl mx-auto">
            <!-- Top columns: Employer / Employee -->
            <div class="grid grid-cols-2 gap-8 border-b-2 border-slate-200 pb-6 text-xs">
              <div class="space-y-1">
                <h3 class="text-sm font-black text-slate-900 uppercase">{{ selectedBulletin.contrat?.code_etablissement }}</h3>
                <p class="text-slate-650 leading-relaxed font-medium">
                  Établissement rattaché au dossier client.
                </p>
              </div>
              <div class="space-y-2">
                <div class="bg-slate-50 border-2 border-slate-200 rounded-none p-3 space-y-1.5 shadow-flat">
                  <div class="flex justify-between border-b border-slate-200 pb-1">
                    <span class="font-bold text-slate-900 uppercase">{{ user?.user_metadata?.first_name }} {{ user?.user_metadata?.last_name?.toUpperCase() }}</span>
                  </div>
                  <div class="grid grid-cols-1 gap-1 text-[10px] leading-tight">
                    <div>
                      <span class="text-slate-450 uppercase text-[8px] font-bold block">Emploi / Poste</span>
                      <span class="font-bold text-slate-800 uppercase">{{ selectedBulletin.contrat?.emploi || 'Non spécifié' }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Metadata period bar -->
            <div class="my-4 py-3 px-4 bg-slate-50 border-2 border-slate-200 rounded-none flex justify-between items-center text-xs font-semibold shadow-flat">
              <div>
                <span>PÉRIODE : </span>
                <span class="font-bold text-slate-900 uppercase">{{ getPeriodLabel(selectedBulletin.mois, selectedBulletin.annee) }}</span>
              </div>
              <div>
                <span>DATE DE PAIEMENT : </span>
                <span class="font-mono text-slate-900">{{ selectedBulletin.date_paiement ? new Date(selectedBulletin.date_paiement).toLocaleDateString('fr-FR') : '-' }}</span>
              </div>
            </div>

            <!-- Pay lines table -->
            <div class="overflow-x-auto border-2 border-slate-200 rounded-none shadow-flat">
              <table class="min-w-full divide-y divide-slate-250 text-xs">
                <thead class="bg-slate-100 text-slate-650 font-bold uppercase tracking-wider text-[8px] border-b-2 border-slate-200">
                  <tr>
                    <th scope="col" rowspan="2" class="px-3 py-2 text-left w-2/5 border-r border-slate-200 align-middle">
                      <div class="flex items-center">
                        <div class="inline-block px-1.5 py-0.5 bg-slate-200 border border-slate-350 text-[10px] font-mono text-slate-800 font-bold uppercase mr-2" title="Nombre de jours ou d'heures travaillés (Base de calcul)">
                          {{ selectedBulletin.cumuls?.mensuel?.heures_jours }} {{ selectedBulletin.contrat?.unite_temps === 'Jours' ? 'j' : 'h' }}
                        </div>
                        <span>Rubrique / Libellé</span>
                      </div>
                    </th>
                    <th scope="col" colspan="4" class="px-2 py-1 text-center bg-slate-50 border-r border-slate-200 border-b border-slate-200">Charges Employé</th>
                    <th scope="col" colspan="3" class="px-2 py-1 text-center bg-slate-100 border-b border-slate-200">Charges Patronales</th>
                  </tr>
                  <tr class="bg-slate-50/50">
                    <th scope="col" class="px-2 py-1 text-right border-r border-slate-200">Base</th>
                    <th scope="col" class="px-2 py-1 text-right border-r border-slate-200">Taux</th>
                    <th scope="col" class="px-2 py-1 text-right border-r border-slate-200">Retenue</th>
                    <th scope="col" class="px-2 py-1 text-right border-r border-slate-200">Gain</th>
                    <th scope="col" class="px-2 py-1 text-right border-r border-slate-200">Base</th>
                    <th scope="col" class="px-2 py-1 text-right border-r border-slate-200">Taux</th>
                    <th scope="col" class="px-2 py-1 text-right">Montant</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-150 font-mono text-slate-700 bg-white">
                  <!-- Section 1: Brut -->
                  <tr class="bg-slate-50 font-bold text-[9px] text-slate-650 uppercase tracking-wider">
                    <td colspan="8" class="px-3 py-1 text-left font-sans">1. Éléments de Salaire Brut</td>
                  </tr>
                  <tr v-for="line in grossLines" :key="line.code">
                    <td class="px-3 py-1.5 text-left font-sans font-medium text-slate-900 border-r border-slate-100">{{ line.libelle }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 text-slate-500">{{ line.base_s || '-' }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 text-slate-400">{{ line.taux_s > 0 ? formatPercent(line.taux_s) : '-' }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 text-slate-400">-</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 font-bold text-slate-900">{{ line.montant_pr !== 0 ? formatXOF(line.montant_pr) : '-' }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 text-slate-500">{{ line.base_p || '-' }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 text-slate-400">{{ line.taux_p > 0 ? formatPercent(line.taux_p) : '-' }}</td>
                    <td class="px-2 py-1.5 text-right">{{ line.montant_cp > 0 ? formatXOF(line.montant_cp) : '-' }}</td>
                  </tr>

                  <!-- Section 2: Cotisations -->
                  <tr class="bg-slate-50 font-bold text-[9px] text-slate-650 uppercase tracking-wider">
                    <td colspan="8" class="px-3 py-1 text-left font-sans">2. Cotisations & Impôts</td>
                  </tr>
                  <tr v-for="line in cotisationsLines" :key="line.code">
                    <td class="px-3 py-1.5 text-left font-sans font-medium text-slate-900 border-r border-slate-100">{{ line.libelle }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 text-slate-500">{{ line.base_s || '-' }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 text-slate-400">{{ line.taux_s > 0 ? formatPercent(line.taux_s) : '-' }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 font-bold text-slate-900">{{ line.montant_cs !== 0 ? formatXOF(line.montant_cs) : '-' }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 text-slate-400">-</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 text-slate-500">{{ line.base_p || '-' }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 text-slate-400">{{ line.taux_p > 0 ? formatPercent(line.taux_p) : '-' }}</td>
                    <td class="px-2 py-1.5 text-right">{{ line.montant_cp > 0 ? formatXOF(line.montant_cp) : '-' }}</td>
                  </tr>

                  <!-- Section 3: Others -->
                  <tr v-if="otherLines.length > 0" class="bg-slate-50 font-bold text-[9px] text-slate-650 uppercase tracking-wider">
                    <td colspan="8" class="px-3 py-1 text-left font-sans">3. Avantages / Autres Rubriques</td>
                  </tr>
                  <tr v-for="line in otherLines" :key="line.code">
                    <td class="px-3 py-1.5 text-left font-sans font-medium text-slate-900 border-r border-slate-100">{{ line.libelle }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 text-slate-500">{{ line.base_s || '-' }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 text-slate-400">{{ line.taux_s > 0 ? formatPercent(line.taux_s) : '-' }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100" :class="line.montant_cs > 0 ? 'font-bold text-slate-900' : 'text-slate-450'">{{ line.montant_cs > 0 ? formatXOF(line.montant_cs) : '-' }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100" :class="line.montant_pr !== 0 ? 'font-bold text-slate-900' : 'text-slate-450'">{{ line.montant_pr !== 0 ? formatXOF(line.montant_pr) : '-' }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 text-slate-500">{{ line.base_p || '-' }}</td>
                    <td class="px-2 py-1.5 text-right border-r border-slate-100 text-slate-400">{{ line.taux_p > 0 ? formatPercent(line.taux_p) : '-' }}</td>
                    <td class="px-2 py-1.5 text-right">{{ line.montant_cp > 0 ? formatXOF(line.montant_cp) : '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Net To Pay Footer Box -->
            <div class="mt-6 border-4 border-slate-900 p-4 grid grid-cols-2 gap-4 items-center bg-slate-50">
              <div class="space-y-1">
                <span class="block text-[8px] font-black text-slate-450 uppercase tracking-widest">Net à payer de référence</span>
                <span class="text-2xl font-black text-green-700 tracking-tight font-mono">{{ formatXOF(selectedBulletin.net_a_payer) }}</span>
              </div>
              <div class="text-right text-[10px] text-slate-500 leading-tight space-y-1">
                <p>Salaire Brut : {{ formatXOF(selectedBulletin.salaire_brut) }}</p>
                <p>Retenues salariales : {{ formatXOF(selectedBulletin.cotisations_salariales) }}</p>
                <p class="font-bold text-slate-800">Net imposable : {{ formatXOF(selectedBulletin.net_imposable) }}</p>
              </div>
            </div>
          </div>
        </div>
      </template>
    </UModal>

    <!-- Modal: Make a Claim -->
    <UModal v-model:open="claimModalOpen" title="Créer une réclamation">
      <template #content>
        <div class="p-6 space-y-4 bg-white border border-slate-200 max-w-md mx-auto">
          <h2 class="text-lg font-bold text-slate-900 border-b border-slate-200 pb-2 uppercase tracking-wider">Déposer une réclamation</h2>
          
          <div class="space-y-3">
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Sujet de la réclamation</label>
              <input v-model="claimSujet" type="text" class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white" required />
            </div>
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-500">Description détaillée de votre demande</label>
              <textarea v-model="claimDescription" rows="4" placeholder="Expliquez en détail l'anomalie ou l'erreur constatée sur votre bulletin..." class="mt-1 block w-full px-3 py-2 border border-slate-350 rounded-none text-sm bg-white" required></textarea>
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button type="button" @click="claimModalOpen = false" class="px-4 py-2 border-2 border-slate-200 text-xs font-bold rounded-none hover:bg-slate-50 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer">
              Annuler
            </button>
            <button type="button" @click="handleSendClaim" :disabled="submittingClaim" class="px-4 py-2 text-xs font-bold bg-green-600 hover:bg-green-700 text-white rounded-none shadow-flat transition-colors uppercase tracking-wider cursor-pointer disabled:bg-slate-300">
              {{ submittingClaim ? "Envoi..." : "Envoyer la réclamation" }}
            </button>
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>
