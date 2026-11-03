<script setup>
/**
 * Utilisateurs du cabinet : membres, rôles et accès.
 *
 * Le propriétaire (gestionnaire référent) invite ses collaborateurs. Un
 * « administrateur du cabinet » accède à toutes les sociétés du propriétaire
 * et à cette page ; un « gestionnaire de paie » ne voit que les sociétés qui
 * lui sont affectées. L'administrateur plateforme voit tous les cabinets.
 */
definePageMeta({
  layout: 'default'
})

const { user } = useSupabase()
const { get, post, put } = useApi()
const toast = useToast()

const membres = ref([])
const chargement = ref(true)
const enregistrement = ref(false)
const formulaireOuvert = ref(false)
const motDePasseInitial = ref(null)
const emailEnvoye = ref(null)
const compteCree = ref(null)

const form = ref({
  prenom: '',
  nom: '',
  email: '',
  role: 'gestionnaire_paie',
  password: ''
})

const estAdminPlateforme = computed(() => !!user.value?.is_admin)
const peutAdministrer = computed(
  () => estAdminPlateforme.value || user.value?.role === 'cabinet'
)

const libelleRole = (role) =>
  role === 'cabinet' ? 'Administrateur du cabinet' : 'Gestionnaire de paie'

const peutModifier = (membre) => {
  if (!membre || membre.id === user.value?.id) return false
  if (estAdminPlateforme.value) return true
  return !membre.est_proprietaire
}

// Le rôle du propriétaire est figé, même pour l'administrateur plateforme :
// le rétrograder laisserait son cabinet sans référent.
const peutChangerRole = (membre) =>
  peutModifier(membre) && !membre.est_proprietaire

const charger = async () => {
  chargement.value = true
  try {
    membres.value = (await get('/admin/utilisateurs')) || []
  } catch (e) {
    console.error('Chargement des utilisateurs du cabinet impossible :', e)
  } finally {
    chargement.value = false
  }
}

const reinitialiserForm = () => {
  form.value = { prenom: '', nom: '', email: '', role: 'gestionnaire_paie', password: '' }
}

const creerMembre = async () => {
  if (!form.value.prenom.trim() || !form.value.nom.trim() || !form.value.email.trim()) {
    toast.add({
      title: 'Champs requis',
      description: 'Le prénom, le nom et l’adresse email sont obligatoires.',
      color: 'warning'
    })
    return
  }
  enregistrement.value = true
  motDePasseInitial.value = null
  emailEnvoye.value = null
  try {
    const cree = await post('/admin/utilisateurs', {
      prenom: form.value.prenom.trim(),
      nom: form.value.nom.trim(),
      email: form.value.email.trim(),
      role: form.value.role,
      password: form.value.password || null
    })
    compteCree.value = cree
    motDePasseInitial.value = cree.mot_de_passe_initial || null
    emailEnvoye.value = cree.email_envoye
    formulaireOuvert.value = false
    reinitialiserForm()
    await charger()
    toast.add({
      title: 'Membre ajouté',
      description: `${cree.prenom} ${cree.nom} a rejoint le cabinet.`,
      color: 'success'
    })
  } catch (e) {
    console.error('Création du membre impossible :', e)
  } finally {
    enregistrement.value = false
  }
}

const changerRole = async (membre, role) => {
  if (!peutModifier(membre) || role === membre.role) return
  try {
    const maj = await put(`/admin/utilisateurs/${membre.id}`, { role })
    const index = membres.value.findIndex((m) => m.id === membre.id)
    if (index !== -1) membres.value[index] = maj
    toast.add({
      title: 'Rôle mis à jour',
      description: `${maj.prenom} ${maj.nom} : ${libelleRole(maj.role)}.`,
      color: 'success'
    })
  } catch (e) {
    console.error('Changement de rôle impossible :', e)
    await charger()
  }
}

const basculerActif = async (membre) => {
  if (!peutModifier(membre)) return
  try {
    const maj = await put(`/admin/utilisateurs/${membre.id}`, { is_active: !membre.is_active })
    const index = membres.value.findIndex((m) => m.id === membre.id)
    if (index !== -1) membres.value[index] = maj
    toast.add({
      title: maj.is_active ? 'Compte réactivé' : 'Compte désactivé',
      description: `${maj.prenom} ${maj.nom}`,
      color: 'success'
    })
  } catch (e) {
    console.error('Changement de statut impossible :', e)
    await charger()
  }
}

onMounted(() => {
  if (peutAdministrer.value) charger()
})
</script>

<template>
  <div class="space-y-6">
    <!-- En-tête -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-navy-50 text-navy-700 rounded-lg flex items-center justify-center border border-navy-200">
          <UIcon name="i-lucide-users" class="w-6 h-6" />
        </div>
        <div>
          <div class="flex items-center gap-2 flex-wrap">
            <h1 class="text-2xl font-bold text-navy-900 leading-tight">Utilisateurs du cabinet</h1>
            <span class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-navy-50 text-navy-700 border border-navy-200">
              {{ membres.length }} {{ membres.length > 1 ? 'membres' : 'membre' }}
            </span>
          </div>
          <p class="text-xs text-slate-500 mt-1">
            Invitez vos collaborateurs et attribuez-leur le bon niveau d'accès.
          </p>
        </div>
      </div>
      <button
        v-if="peutAdministrer"
        type="button"
        class="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-xs font-bold uppercase tracking-wider transition-colors shadow-flat shrink-0"
        @click="formulaireOuvert = !formulaireOuvert"
      >
        <UIcon :name="formulaireOuvert ? 'i-lucide-x' : 'i-lucide-user-plus'" class="w-4 h-4" />
        {{ formulaireOuvert ? 'Fermer' : 'Ajouter un membre' }}
      </button>
    </div>

    <AdminNav />

    <!-- Accès refusé (sécurité d'affichage : l'API tranche) -->
    <div
      v-if="!peutAdministrer"
      class="bg-white border border-slate-200 rounded-xl p-8 text-center text-sm text-slate-500"
    >
      <UIcon name="i-lucide-lock" class="w-8 h-8 mx-auto mb-3 text-slate-400" />
      L'administration des utilisateurs est réservée au propriétaire du cabinet.
    </div>

    <template v-else>
      <!-- Identifiants du membre créé -->
      <div
        v-if="compteCree"
        class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex items-start gap-3">
            <div class="w-9 h-9 bg-green-50 border border-green-200 text-green-700 rounded-lg flex items-center justify-center shrink-0">
              <UIcon name="i-lucide-mail-check" class="w-4 h-4" />
            </div>
            <div class="text-xs leading-relaxed">
              <p class="font-bold text-navy-900 text-sm">
                Compte créé pour {{ compteCree.prenom }} {{ compteCree.nom }}
              </p>
              <p v-if="emailEnvoye" class="text-slate-600">
                Les identifiants ont été envoyés à <span class="font-semibold">{{ compteCree.email }}</span>.
              </p>
              <p v-else class="text-slate-600">
                L'envoi automatique a échoué (SMTP indisponible). Transmettez ces identifiants
                par un autre canal :
              </p>
              <p v-if="motDePasseInitial" class="mt-1 font-mono text-sm bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 inline-block">
                {{ compteCree.email }} — {{ motDePasseInitial }}
              </p>
            </div>
          </div>
          <button
            type="button"
            class="text-slate-400 hover:text-slate-700"
            aria-label="Fermer"
            @click="compteCree = null; motDePasseInitial = null; emailEnvoye = null"
          >
            <UIcon name="i-lucide-x" class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Formulaire d'invitation -->
      <div v-if="formulaireOuvert" class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider mb-4">
          Ajouter un membre du cabinet
        </h2>
        <form class="grid grid-cols-1 md:grid-cols-2 gap-4" @submit.prevent="creerMembre">
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="membre_prenom">Prénom</label>
            <input
              id="membre_prenom"
              v-model="form.prenom"
              type="text"
              required
              placeholder="Adjoua"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            >
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="membre_nom">Nom</label>
            <input
              id="membre_nom"
              v-model="form.nom"
              type="text"
              required
              placeholder="Yao"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            >
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="membre_email">Email professionnel</label>
            <input
              id="membre_email"
              v-model="form.email"
              type="email"
              required
              placeholder="prenom.nom@cabinet.ci"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            >
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="membre_role">Rôle</label>
            <select
              id="membre_role"
              v-model="form.role"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="gestionnaire_paie">Gestionnaire de paie</option>
              <option value="cabinet">Administrateur du cabinet</option>
            </select>
          </div>
          <div class="md:col-span-2">
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="membre_password">
              Mot de passe (facultatif)
            </label>
            <input
              id="membre_password"
              v-model="form.password"
              type="password"
              minlength="8"
              placeholder="Laisser vide pour générer et envoyer un mot de passe"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            >
          </div>
          <div class="md:col-span-2 flex justify-end gap-3">
            <button
              type="button"
              class="px-4 py-2 border border-slate-300 text-slate-600 hover:bg-slate-50 text-xs font-bold uppercase tracking-wider transition-colors"
              @click="formulaireOuvert = false; reinitialiserForm()"
            >
              Annuler
            </button>
            <button
              type="submit"
              :disabled="enregistrement"
              class="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white text-xs font-bold uppercase tracking-wider transition-colors"
            >
              <UIcon v-if="enregistrement" name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
              <UIcon v-else name="i-lucide-user-plus" class="w-4 h-4" />
              Créer le compte
            </button>
          </div>
        </form>
      </div>

      <!-- Liste -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div v-if="chargement" class="p-10 flex flex-col items-center gap-3 text-slate-500">
          <UIcon name="i-lucide-loader-2" class="w-6 h-6 animate-spin text-green-600" />
          <span class="text-sm">Chargement des utilisateurs…</span>
        </div>

        <div v-else-if="membres.length === 0" class="p-10 text-center text-sm text-slate-500">
          Aucun membre pour l'instant. Utilisez « Ajouter un membre » pour inviter votre premier collaborateur.
        </div>

        <div v-else class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr>
                <th scope="col" class="px-5 py-3 text-left">Membre</th>
                <th scope="col" class="px-5 py-3 text-left">Rôle</th>
                <th scope="col" class="px-5 py-3 text-left">Sociétés</th>
                <th scope="col" class="px-5 py-3 text-left">Statut</th>
                <th scope="col" class="px-5 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="membre in membres" :key="membre.id" class="hover:bg-slate-50">
                <td class="px-5 py-4">
                  <div class="flex items-center gap-3">
                    <div class="w-9 h-9 bg-navy-50 border border-navy-200 text-navy-700 rounded-full flex items-center justify-center font-bold text-xs shrink-0">
                      {{ (membre.prenom || membre.email || '?').charAt(0).toUpperCase() }}
                    </div>
                    <div>
                      <div class="flex items-center gap-2 flex-wrap">
                        <span class="font-bold text-navy-900">
                          {{ [membre.prenom, membre.nom].filter(Boolean).join(' ') || membre.email }}
                        </span>
                        <span
                          v-if="membre.est_proprietaire"
                          class="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider bg-navy-50 text-navy-700 border border-navy-200"
                        >
                          Propriétaire
                        </span>
                        <span
                          v-if="membre.id === user?.id"
                          class="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider bg-green-50 text-green-700 border border-green-200"
                        >
                          Vous
                        </span>
                      </div>
                      <p class="text-xs text-slate-500">{{ membre.email }}</p>
                    </div>
                  </div>
                </td>
                <td class="px-5 py-4">
                  <select
                    :value="membre.role"
                    :disabled="!peutChangerRole(membre)"
                    class="px-2 py-1.5 border border-slate-300 rounded-md text-xs bg-white disabled:bg-slate-50 disabled:text-slate-500"
                    @change="changerRole(membre, $event.target.value)"
                  >
                    <option value="gestionnaire_paie">Gestionnaire de paie</option>
                    <option value="cabinet">Administrateur du cabinet</option>
                  </select>
                </td>
                <td class="px-5 py-4 text-slate-600">
                  <span class="font-bold text-navy-900">{{ membre.nombre_societes }}</span>
                  <span class="text-xs text-slate-500"> société{{ membre.nombre_societes > 1 ? 's' : '' }}</span>
                </td>
                <td class="px-5 py-4">
                  <span
                    class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border"
                    :class="membre.is_active
                      ? 'bg-green-50 text-green-700 border-green-200'
                      : 'bg-slate-100 text-slate-600 border-slate-200'"
                  >
                    {{ membre.is_active ? 'Actif' : 'Désactivé' }}
                  </span>
                </td>
                <td class="px-5 py-4 text-right">
                  <button
                    type="button"
                    :disabled="!peutModifier(membre)"
                    class="text-xs font-semibold transition-colors disabled:text-slate-300 disabled:cursor-not-allowed"
                    :class="membre.is_active ? 'text-red-600 hover:text-red-800' : 'text-green-700 hover:text-green-800'"
                    @click="basculerActif(membre)"
                  >
                    {{ membre.is_active ? 'Désactiver' : 'Réactiver' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Rappel des rôles -->
      <div class="bg-slate-50 border border-slate-200 rounded-xl p-5 text-xs text-slate-600 leading-relaxed space-y-2">
        <p class="font-bold text-navy-900 text-sm">Comment fonctionnent les rôles ?</p>
        <p>
          <span class="font-semibold text-navy-900">Administrateur du cabinet</span> : accède à toutes
          les sociétés du cabinet, peut inviter des membres et gérer leurs rôles.
        </p>
        <p>
          <span class="font-semibold text-navy-900">Gestionnaire de paie</span> : accède uniquement aux
          sociétés qui lui sont affectées (fiche société, onglet Gestionnaires).
        </p>
        <p>
          Le propriétaire du cabinet — le compte créé à l'inscription — ne peut être ni rétrogradé ni
          désactivé.
        </p>
      </div>
    </template>
  </div>
</template>
