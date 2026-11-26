<script setup>
/**
 * Administration plateforme : comptes administrateurs de la plateforme.
 *
 * Un administrateur crée d'autres administrateurs avec exactement les mêmes
 * droits que lui (gestion des cabinets, référentiels, tableau de bord). Ces
 * comptes ne sont rattachés à aucun cabinet : ils se connectent sur l'adresse
 * principale. On ne peut pas se désactiver soi-même, et la plateforme garde
 * toujours au moins un administrateur actif (contrôlé par l'API).
 */
definePageMeta({
  layout: 'default'
})

const { user } = useSupabase()
const { get, post, put } = useApi()
const toast = useToast()

const estAdminPlateforme = computed(() => !!user.value?.is_admin)

const administrateurs = ref([])
const chargement = ref(true)
const formulaireOuvert = ref(false)
const enCours = ref(false)
const compteCree = ref(null)
const formulaire = ref({ prenom: '', nom: '', email: '', password: '' })

const actifs = computed(() => administrateurs.value.filter(a => a.is_active).length)

const formaterDate = (valeur) => {
  if (!valeur) return '—'
  const date = new Date(valeur)
  if (Number.isNaN(date.getTime())) return valeur
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

const charger = async () => {
  chargement.value = true
  try {
    administrateurs.value = (await get('/platform/administrateurs')) || []
  } catch (e) {
    console.error('Chargement des administrateurs impossible :', e)
  } finally {
    chargement.value = false
  }
}

const reinitialiser = () => {
  formulaire.value = { prenom: '', nom: '', email: '', password: '' }
}

const creer = async () => {
  const f = formulaire.value
  if (!f.prenom.trim() || !f.nom.trim() || !f.email.trim()) {
    toast.add({ title: 'Champs requis', description: 'Le prénom, le nom et l’email sont obligatoires.', color: 'warning' })
    return
  }
  enCours.value = true
  compteCree.value = null
  try {
    const cree = await post('/platform/administrateurs', {
      prenom: f.prenom.trim(),
      nom: f.nom.trim(),
      email: f.email.trim(),
      password: f.password || null
    })
    compteCree.value = {
      email: cree.email,
      motDePasse: cree.mot_de_passe_initial,
      emailEnvoye: cree.email_envoye
    }
    formulaireOuvert.value = false
    reinitialiser()
    await charger()
    toast.add({ title: 'Administrateur créé', description: cree.email, color: 'success' })
  } catch (e) {
    console.error('Création de l’administrateur impossible :', e)
  } finally {
    enCours.value = false
  }
}

const changerStatut = async (admin) => {
  const action = admin.is_active ? 'désactiver' : 'réactiver'
  if (!confirm(`Voulez-vous vraiment ${action} l’administrateur ${admin.prenom} ${admin.nom} (${admin.email}) ?`)) return
  try {
    const maj = await put(`/platform/administrateurs/${admin.id}/statut`, { actif: !admin.is_active })
    const index = administrateurs.value.findIndex(a => a.id === admin.id)
    if (index !== -1) administrateurs.value[index] = maj
    toast.add({
      title: maj.is_active ? 'Administrateur réactivé' : 'Administrateur désactivé',
      description: maj.email,
      color: 'success'
    })
  } catch (e) {
    console.error('Changement de statut impossible :', e)
  }
}

onMounted(() => {
  if (estAdminPlateforme.value) charger()
})
</script>

<template>
  <div class="space-y-6">
    <!-- En-tête -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-navy-50 text-navy-700 rounded-lg flex items-center justify-center border border-navy-200">
          <Icon name="i-lucide-shield-check" class="w-6 h-6" />
        </div>
        <div>
          <div class="flex items-center gap-2 flex-wrap">
            <h1 class="text-2xl font-bold text-navy-900 leading-tight">Administrateurs</h1>
            <span class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-navy-50 text-navy-700 border border-navy-200">
              {{ actifs }} {{ actifs > 1 ? 'actifs' : 'actif' }}
            </span>
          </div>
          <p class="text-xs text-slate-500 mt-1">
            Comptes qui administrent la plateforme, avec les mêmes droits que vous.
          </p>
        </div>
      </div>
      <button
        v-if="estAdminPlateforme"
        type="button"
        class="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-xs font-bold uppercase tracking-wider transition-colors shadow-flat shrink-0"
        @click="formulaireOuvert = !formulaireOuvert"
      >
        <Icon :name="formulaireOuvert ? 'i-lucide-x' : 'i-lucide-user-plus'" class="w-4 h-4" />
        {{ formulaireOuvert ? 'Fermer' : 'Ajouter un administrateur' }}
      </button>
    </div>

    <div v-if="!estAdminPlateforme" class="bg-white border border-slate-200 rounded-xl p-8 text-center text-sm text-slate-500">
      <Icon name="i-lucide-lock" class="w-8 h-8 mx-auto mb-3 text-slate-400" />
      Cet espace est réservé à l'administrateur de la plateforme.
    </div>

    <template v-else>
      <!-- Identifiants du compte créé (mot de passe généré affiché une seule fois) -->
      <div v-if="compteCree" class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div class="flex items-start justify-between gap-4">
          <div class="flex items-start gap-3">
            <div class="w-9 h-9 bg-green-50 border border-green-200 text-green-700 rounded-lg flex items-center justify-center shrink-0">
              <Icon name="i-lucide-mail-check" class="w-4 h-4" />
            </div>
            <div class="text-xs leading-relaxed">
              <p class="font-bold text-navy-900 text-sm">Administrateur de la plateforme créé</p>
              <p v-if="compteCree.emailEnvoye" class="text-slate-600">
                Les identifiants ont été envoyés à <span class="font-semibold">{{ compteCree.email }}</span>.
              </p>
              <p v-else class="text-slate-600">
                Envoi automatique indisponible : transmettez ces identifiants par un autre canal.
              </p>
              <p v-if="compteCree.motDePasse" class="mt-1 font-mono text-sm bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 inline-block">
                {{ compteCree.email }} — {{ compteCree.motDePasse }}
              </p>
            </div>
          </div>
          <button type="button" class="text-slate-400 hover:text-slate-700" aria-label="Fermer" @click="compteCree = null">
            <Icon name="i-lucide-x" class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Formulaire de création -->
      <div v-if="formulaireOuvert" class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider mb-1">Nouvel administrateur de la plateforme</h2>
        <p class="text-xs text-slate-500 mb-4">
          Il aura les mêmes droits que vous : gestion des cabinets, des référentiels et des administrateurs.
        </p>
        <form class="grid grid-cols-1 md:grid-cols-2 gap-4" @submit.prevent="creer">
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="pa_prenom">Prénom</label>
            <InputText id="pa_prenom" v-model="formulaire.prenom" required
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500" />
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="pa_nom">Nom</label>
            <InputText id="pa_nom" v-model="formulaire.nom" required
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500" />
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="pa_email">Email professionnel</label>
            <InputText id="pa_email" v-model="formulaire.email" type="email" required placeholder="prenom.nom@payohada.ci"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500" />
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="pa_password">Mot de passe (facultatif)</label>
            <InputText id="pa_password" v-model="formulaire.password" type="password" minlength="8" placeholder="Généré et envoyé si vide"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500" />
          </div>
          <div class="md:col-span-2 flex justify-end gap-3">
            <button type="button" class="px-4 py-2 border border-slate-300 text-slate-600 hover:bg-slate-50 text-xs font-bold uppercase tracking-wider"
              @click="formulaireOuvert = false; reinitialiser()">
              Annuler
            </button>
            <button type="submit" :disabled="enCours"
              class="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white text-xs font-bold uppercase tracking-wider">
              <Icon v-if="enCours" name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
              <Icon v-else name="i-lucide-user-plus" class="w-4 h-4" />
              Créer l'administrateur
            </button>
          </div>
        </form>
      </div>

      <!-- Liste -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div v-if="chargement" class="p-10 flex flex-col items-center gap-3 text-slate-500">
          <Icon name="i-lucide-loader-2" class="w-6 h-6 animate-spin text-green-600" />
          <span class="text-sm">Chargement des administrateurs…</span>
        </div>

        <div v-else class="overflow-x-auto">
          <DataTable class="min-w-full text-sm" :value="administrateurs" data-key="id" row-hover>
            <Column header="Administrateur" header-class="px-5 py-3 text-left" body-class="px-5 py-4">
              <template #body="{ data: admin }">
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 bg-navy-50 border border-navy-200 text-navy-700 rounded-lg flex items-center justify-center font-bold text-xs shrink-0">
                    {{ (admin.prenom || admin.email || '?').charAt(0).toUpperCase() }}
                  </div>
                  <div>
                    <p class="font-bold text-navy-900">
                      {{ admin.prenom }} {{ admin.nom }}
                      <span v-if="admin.est_moi"
                        class="ml-1 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider bg-navy-50 text-navy-700 border border-navy-200 rounded">Vous</span>
                    </p>
                    <p class="text-xs text-slate-500">{{ admin.email }}</p>
                  </div>
                </div>
              </template>
            </Column>
            <Column header="Créé le" header-class="px-5 py-3 text-left" body-class="px-5 py-4 text-slate-600">
              <template #body="{ data: admin }">
                {{ formaterDate(admin.created_at) }}
                <p v-if="admin.must_change_password" class="text-[11px] text-amber-700">Mot de passe provisoire</p>
              </template>
            </Column>
            <Column header="Statut" header-class="px-5 py-3 text-left" body-class="px-5 py-4">
              <template #body="{ data: admin }">
                <span class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border"
                  :class="admin.is_active
                    ? 'bg-green-50 text-green-700 border-green-200'
                    : 'bg-red-50 text-red-700 border-red-200'">
                  {{ admin.is_active ? 'Actif' : 'Désactivé' }}
                </span>
              </template>
            </Column>
            <Column header="Actions" header-class="px-5 py-3 text-right" body-class="px-5 py-4 text-right">
              <template #body="{ data: admin }">
                <button v-if="!admin.est_moi" type="button" class="text-xs font-semibold"
                  :class="admin.is_active ? 'text-red-600 hover:text-red-800' : 'text-green-700 hover:text-green-900'"
                  @click="changerStatut(admin)">
                  {{ admin.is_active ? 'Désactiver' : 'Réactiver' }}
                </button>
                <span v-else class="text-xs text-slate-400">—</span>
              </template>
            </Column>
          </DataTable>
        </div>
      </div>

      <div class="bg-slate-50 border border-slate-200 rounded-xl p-5 text-xs text-slate-600 leading-relaxed space-y-2">
        <p class="font-bold text-navy-900 text-sm">Accès des administrateurs</p>
        <p>
          Les administrateurs de la plateforme se connectent uniquement sur l'adresse principale,
          jamais sur l'adresse d'un cabinet. Un compte désactivé ne peut plus se connecter ; vous ne
          pouvez pas désactiver votre propre compte, et la plateforme garde toujours au moins un
          administrateur actif.
        </p>
      </div>
    </template>
  </div>
</template>
