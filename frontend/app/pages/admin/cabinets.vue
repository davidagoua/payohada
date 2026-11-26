<script setup>
/**
 * Administration plateforme : cabinets et leurs administrateurs.
 *
 * Réservé aux comptes `is_admin`. Permet de créer un cabinet avec son
 * administrateur propriétaire, d'ajouter des co-administrateurs, de suspendre
 * ou de réactiver un cabinet. La suspension bloque la connexion et l'API de
 * tous les membres, sans supprimer leurs données.
 */
definePageMeta({
  layout: 'default'
})

const { user } = useSupabase()
const { get, post, put } = useApi()
const toast = useToast()

const estAdminPlateforme = computed(() => !!user.value?.is_admin)

const cabinets = ref([])
const chargement = ref(true)
const formulaireOuvert = ref(false)
const creationEnCours = ref(false)
const adminEnCours = ref(false)
const adminCible = ref(null)
const compteCree = ref(null)

const creation = ref({
  type_cabinet: 'cabinet',
  sous_domaine: '',
  cabinet_nom: '',
  cabinet_telephone: '',
  cabinet_ville: '',
  prenom: '',
  nom: '',
  email: '',
  password: ''
})

const adminForm = ref({
  prenom: '',
  nom: '',
  email: '',
  password: ''
})

const formaterDate = (valeur) => {
  if (!valeur) return '—'
  const date = new Date(valeur)
  if (Number.isNaN(date.getTime())) return valeur
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

const charger = async () => {
  chargement.value = true
  try {
    cabinets.value = (await get('/platform/cabinets')) || []
  } catch (e) {
    console.error('Chargement des cabinets impossible :', e)
  } finally {
    chargement.value = false
  }
}

const reinitialiserCreation = () => {
  creation.value = {
    type_cabinet: 'cabinet', sous_domaine: '', cabinet_nom: '', cabinet_telephone: '', cabinet_ville: '',
    prenom: '', nom: '', email: '', password: ''
  }
}

const creerCabinet = async () => {
  if (!creation.value.cabinet_nom.trim() || !creation.value.prenom.trim()
      || !creation.value.nom.trim() || !creation.value.email.trim()) {
    toast.add({
      title: 'Champs requis',
      description: 'Le nom du cabinet, le prénom, le nom et l’email de l’administrateur sont obligatoires.',
      color: 'warning'
    })
    return
  }
  creationEnCours.value = true
  compteCree.value = null
  try {
    const cree = await post('/platform/cabinets', {
      cabinet_nom: creation.value.cabinet_nom.trim(),
      cabinet_telephone: creation.value.cabinet_telephone || null,
      cabinet_ville: creation.value.cabinet_ville || null,
      sous_domaine: creation.value.sous_domaine.trim() || null,
      type_cabinet: creation.value.type_cabinet,
      administrateur: {
        prenom: creation.value.prenom.trim(),
        nom: creation.value.nom.trim(),
        email: creation.value.email.trim(),
        password: creation.value.password || null
      }
    })
    compteCree.value = {
      titre: cree.type_cabinet === 'entreprise'
        ? `Entreprise « ${cree.cabinet_nom} » créée, avec son dossier et son établissement`
        : `Cabinet « ${cree.cabinet_nom} » créé`,
      email: cree.email,
      motDePasse: cree.mot_de_passe_initial,
      emailEnvoye: cree.email_envoye
    }
    formulaireOuvert.value = false
    reinitialiserCreation()
    await charger()
    toast.add({ title: 'Cabinet créé', description: cree.cabinet_nom, color: 'success' })
  } catch (e) {
    console.error('Création du cabinet impossible :', e)
  } finally {
    creationEnCours.value = false
  }
}

const ouvrirFormulaireAdmin = (cabinet) => {
  adminCible.value = cabinet
  adminForm.value = { prenom: '', nom: '', email: '', password: '' }
  formulaireOuvert.value = false
}

const ajouterAdministrateur = async () => {
  if (!adminCible.value) return
  if (!adminForm.value.prenom.trim() || !adminForm.value.nom.trim() || !adminForm.value.email.trim()) {
    toast.add({
      title: 'Champs requis',
      description: 'Le prénom, le nom et l’email sont obligatoires.',
      color: 'warning'
    })
    return
  }
  adminEnCours.value = true
  compteCree.value = null
  try {
    const cree = await post(`/platform/cabinets/${adminCible.value.id}/administrateurs`, {
      prenom: adminForm.value.prenom.trim(),
      nom: adminForm.value.nom.trim(),
      email: adminForm.value.email.trim(),
      password: adminForm.value.password || null
    })
    compteCree.value = {
      titre: `Administrateur ajouté à « ${adminCible.value.cabinet_nom} »`,
      email: cree.email,
      motDePasse: cree.mot_de_passe_initial,
      emailEnvoye: cree.email_envoye
    }
    adminCible.value = null
    await charger()
    toast.add({ title: 'Administrateur ajouté', description: cree.email, color: 'success' })
  } catch (e) {
    console.error('Ajout de l’administrateur impossible :', e)
  } finally {
    adminEnCours.value = false
  }
}

// Adresse de connexion du cabinet (sous-domaine) : proposée à partir du nom.
const suggestionSousDomaine = computed(() =>
  (creation.value.cabinet_nom || '')
    .normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 63)
)

const changerSousDomaine = async (cabinet) => {
  const saisie = prompt(
    `Nouvelle adresse de connexion du cabinet « ${cabinet.cabinet_nom || cabinet.email} » (sous-domaine).\n` +
    'Les comptes du cabinet devront se reconnecter à la nouvelle adresse.',
    cabinet.sous_domaine || ''
  )
  if (!saisie || saisie.trim() === cabinet.sous_domaine) return
  try {
    const maj = await put(`/platform/cabinets/${cabinet.id}/sous-domaine`, { sous_domaine: saisie.trim() })
    const index = cabinets.value.findIndex(c => c.id === cabinet.id)
    if (index !== -1) cabinets.value[index] = maj
    toast.add({ title: 'Adresse modifiée', description: maj.url_espace || maj.sous_domaine, color: 'success' })
  } catch (e) {
    console.error('Changement d’adresse impossible :', e)
  }
}

const changerStatut = async (cabinet) => {
  const action = cabinet.suspendu ? 'réactiver' : 'suspendre'
  if (!confirm(`Voulez-vous vraiment ${action} le cabinet « ${cabinet.cabinet_nom || cabinet.email} » ?`)) return
  try {
    const maj = await put(`/platform/cabinets/${cabinet.id}/statut`, { suspendu: !cabinet.suspendu })
    const index = cabinets.value.findIndex(c => c.id === cabinet.id)
    if (index !== -1) cabinets.value[index] = maj
    toast.add({
      title: cabinet.suspendu ? 'Cabinet réactivé' : 'Cabinet suspendu',
      description: maj.cabinet_nom || maj.email,
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
          <Icon name="i-lucide-building-2" class="w-6 h-6" />
        </div>
        <div>
          <div class="flex items-center gap-2 flex-wrap">
            <h1 class="text-2xl font-bold text-navy-900 leading-tight">Cabinets</h1>
            <span class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-navy-50 text-navy-700 border border-navy-200">
              {{ cabinets.length }} {{ cabinets.length > 1 ? 'cabinets' : 'cabinet' }}
            </span>
          </div>
          <p class="text-xs text-slate-500 mt-1">
            Créez les cabinets, ajoutez leurs administrateurs et suspendez un accès si nécessaire.
          </p>
        </div>
      </div>
      <button
        v-if="estAdminPlateforme"
        type="button"
        class="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-xs font-bold uppercase tracking-wider transition-colors shadow-flat shrink-0"
        @click="formulaireOuvert = !formulaireOuvert; adminCible = null"
      >
        <Icon :name="formulaireOuvert ? 'i-lucide-x' : 'i-lucide-plus'" class="w-4 h-4" />
        {{ formulaireOuvert ? 'Fermer' : 'Ajouter un cabinet' }}
      </button>
    </div>

    <AdminNav />

    <!-- Accès refusé (sécurité d'affichage ; l'API tranche) -->
    <div v-if="!estAdminPlateforme" class="bg-white border border-slate-200 rounded-xl p-8 text-center text-sm text-slate-500">
      <Icon name="i-lucide-lock" class="w-8 h-8 mx-auto mb-3 text-slate-400" />
      Cet espace est réservé à l'administrateur de la plateforme.
    </div>

    <template v-else>
      <!-- Identifiants du compte créé -->
      <div v-if="compteCree" class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div class="flex items-start justify-between gap-4">
          <div class="flex items-start gap-3">
            <div class="w-9 h-9 bg-green-50 border border-green-200 text-green-700 rounded-lg flex items-center justify-center shrink-0">
              <Icon name="i-lucide-mail-check" class="w-4 h-4" />
            </div>
            <div class="text-xs leading-relaxed">
              <p class="font-bold text-navy-900 text-sm">{{ compteCree.titre }}</p>
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

      <!-- Formulaire de création d'un cabinet -->
      <div v-if="formulaireOuvert" class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider mb-4">Nouveau cabinet et son administrateur</h2>
        <form class="grid grid-cols-1 md:grid-cols-2 gap-4" @submit.prevent="creerCabinet">
          <fieldset class="md:col-span-2">
            <legend class="block text-xs font-bold uppercase tracking-wider text-slate-500">Type de compte</legend>
            <!-- Libellés sans classe : la charte force `display: block` sur `label[class]`. -->
            <div class="mt-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label for="type-cabinet">
                <span class="flex items-start gap-3 p-3 h-full border rounded-lg cursor-pointer"
                  :class="creation.type_cabinet === 'cabinet' ? 'border-green-600 bg-green-50' : 'border-slate-200'">
                  <RadioButton v-model="creation.type_cabinet" input-id="type-cabinet" value="cabinet" class="mt-0.5 shrink-0" />
                  <span>
                    <span class="block text-sm font-bold text-navy-900">Cabinet de paie</span>
                    <span class="block text-xs text-slate-500">Gère la paie de plusieurs entreprises.</span>
                  </span>
                </span>
              </label>
              <label for="type-entreprise">
                <span class="flex items-start gap-3 p-3 h-full border rounded-lg cursor-pointer"
                  :class="creation.type_cabinet === 'entreprise' ? 'border-green-600 bg-green-50' : 'border-slate-200'">
                  <RadioButton v-model="creation.type_cabinet" input-id="type-entreprise" value="entreprise" class="mt-0.5 shrink-0" />
                  <span>
                    <span class="block text-sm font-bold text-navy-900">Entreprise</span>
                    <span class="block text-xs text-slate-500">Gère sa propre paie : son dossier et son établissement sont créés avec le compte.</span>
                  </span>
                </span>
              </label>
            </div>
          </fieldset>
          <div class="md:col-span-2">
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="cabinet_nom">{{ creation.type_cabinet === 'entreprise' ? 'Nom de l’entreprise' : 'Nom du cabinet' }}</label>
            <InputText
              id="cabinet_nom"
              v-model="creation.cabinet_nom"
              required
              placeholder="Cabinet Audit & Paie"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          <div class="md:col-span-2">
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="cabinet_sous_domaine">Adresse de connexion (sous-domaine)</label>
            <InputText
              id="cabinet_sous_domaine"
              v-model="creation.sous_domaine"
              :placeholder="suggestionSousDomaine || 'cabinet-audit-paie'"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <p class="mt-1 text-[11px] text-slate-500">
              Les comptes du cabinet ne se connecteront qu'à cette adresse. Laissez vide pour la déduire du nom
              (« {{ suggestionSousDomaine || '…' }} »).
            </p>
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="cabinet_ville">Ville</label>
            <InputText
              id="cabinet_ville"
              v-model="creation.cabinet_ville"
              placeholder="Abidjan"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="cabinet_telephone">Téléphone</label>
            <InputText
              id="cabinet_telephone"
              v-model="creation.cabinet_telephone"
              placeholder="+225 07 00 00 00 00"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          <div class="md:col-span-2 border-t border-slate-100 pt-3">
            <p class="text-xs font-bold uppercase tracking-wider text-navy-900">Administrateur propriétaire</p>
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="admin_prenom">Prénom</label>
            <InputText
              id="admin_prenom"
              v-model="creation.prenom"
              required
              placeholder="Awa"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="admin_nom">Nom</label>
            <InputText
              id="admin_nom"
              v-model="creation.nom"
              required
              placeholder="Kouassi"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="admin_email">Email professionnel</label>
            <InputText
              id="admin_email"
              v-model="creation.email"
              type="email"
              required
              placeholder="direction@cabinet.ci"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="admin_password">Mot de passe (facultatif)</label>
            <InputText
              id="admin_password"
              v-model="creation.password"
              type="password"
              minlength="8"
              placeholder="Généré et envoyé si vide"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          <div class="md:col-span-2 flex justify-end gap-3">
            <button type="button" class="px-4 py-2 border border-slate-300 text-slate-600 hover:bg-slate-50 text-xs font-bold uppercase tracking-wider"
              @click="formulaireOuvert = false; reinitialiserCreation()">
              Annuler
            </button>
            <button type="submit" :disabled="creationEnCours"
              class="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white text-xs font-bold uppercase tracking-wider">
              <Icon v-if="creationEnCours" name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
              <Icon v-else name="i-lucide-building-2" class="w-4 h-4" />
              Créer le cabinet
            </button>
          </div>
        </form>
      </div>

      <!-- Formulaire d'ajout d'un administrateur -->
      <div v-if="adminCible" class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div class="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider">Ajouter un administrateur</h2>
            <p class="text-xs text-slate-500 mt-1">{{ adminCible.cabinet_nom || adminCible.email }}</p>
          </div>
          <button type="button" class="text-slate-400 hover:text-slate-700" @click="adminCible = null">
            <Icon name="i-lucide-x" class="w-4 h-4" />
          </button>
        </div>
        <form class="grid grid-cols-1 md:grid-cols-2 gap-4" @submit.prevent="ajouterAdministrateur">
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="co_prenom">Prénom</label>
            <InputText
              id="co_prenom"
              v-model="adminForm.prenom"
              required
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="co_nom">Nom</label>
            <InputText
              id="co_nom"
              v-model="adminForm.nom"
              required
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="co_email">Email professionnel</label>
            <InputText
              id="co_email"
              v-model="adminForm.email"
              type="email"
              required
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-500" for="co_password">Mot de passe (facultatif)</label>
            <InputText
              id="co_password"
              v-model="adminForm.password"
              type="password"
              minlength="8"
              placeholder="Généré et envoyé si vide"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          <div class="md:col-span-2 flex justify-end gap-3">
            <button type="button" class="px-4 py-2 border border-slate-300 text-slate-600 hover:bg-slate-50 text-xs font-bold uppercase tracking-wider" @click="adminCible = null">
              Annuler
            </button>
            <button type="submit" :disabled="adminEnCours"
              class="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white text-xs font-bold uppercase tracking-wider">
              <Icon v-if="adminEnCours" name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
              <Icon v-else name="i-lucide-user-plus" class="w-4 h-4" />
              Ajouter l'administrateur
            </button>
          </div>
        </form>
      </div>

      <!-- Liste des cabinets -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div v-if="chargement" class="p-10 flex flex-col items-center gap-3 text-slate-500">
          <Icon name="i-lucide-loader-2" class="w-6 h-6 animate-spin text-green-600" />
          <span class="text-sm">Chargement des cabinets…</span>
        </div>

        <div v-else-if="cabinets.length === 0" class="p-10 text-center text-sm text-slate-500">
          Aucun cabinet pour l'instant. Utilisez « Ajouter un cabinet » pour créer le premier.
        </div>

        <div v-else class="overflow-x-auto">
          <DataTable
            class="min-w-full text-sm"
            :value="cabinets"
            data-key="id"
            row-hover
          >
            <Column header="Cabinet" header-class="px-5 py-3 text-left" body-class="px-5 py-4">
              <template #body="{ data: cabinet }">
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 bg-navy-50 border border-navy-200 text-navy-700 rounded-lg flex items-center justify-center font-bold text-xs shrink-0">
                    {{ (cabinet.cabinet_nom || cabinet.email || '?').charAt(0).toUpperCase() }}
                  </div>
                  <div>
                    <p class="font-bold text-navy-900">
                      {{ cabinet.cabinet_nom || 'Cabinet sans nom' }}
                      <span v-if="cabinet.type_cabinet === 'entreprise'"
                        class="ml-1 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider bg-green-50 text-green-700 border border-green-200 rounded">Entreprise</span>
                    </p>
                    <p class="text-xs text-slate-500">{{ cabinet.email }}</p>
                    <p class="text-[11px] text-slate-400 mt-0.5">
                      {{ cabinet.ville || '—' }} · créé le {{ formaterDate(cabinet.created_at) }}
                    </p>
                    <p v-if="cabinet.sous_domaine" class="text-[11px] mt-0.5">
                      <a v-if="cabinet.url_espace" :href="`${cabinet.url_espace}/login`" target="_blank" rel="noopener"
                        class="font-mono text-green-700 hover:underline">{{ cabinet.url_espace.replace(/^https?:\/\//, '') }}</a>
                      <span v-else class="font-mono text-slate-500">{{ cabinet.sous_domaine }}</span>
                    </p>
                  </div>
                </div>
              </template>
            </Column>
            <Column header="Administrateurs" header-class="px-5 py-3 text-left" body-class="px-5 py-4">
              <template #body="{ data: cabinet }">
                <div class="flex flex-wrap gap-1.5">
                  <span v-for="admin in cabinet.administrateurs" :key="admin.id"
                    class="px-2 py-0.5 text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                    {{ admin.prenom }} {{ admin.nom }}
                    <span v-if="admin.est_proprietaire" class="text-navy-600">· propriétaire</span>
                  </span>
                </div>
              </template>
            </Column>
            <Column header="Membres / Sociétés" header-class="px-5 py-3 text-left" body-class="px-5 py-4 text-slate-600">
              <template #body="{ data: cabinet }">
                <span class="font-bold text-navy-900">{{ cabinet.membres }}</span> membre(s)
                <span class="mx-1 text-slate-300">·</span>
                <span class="font-bold text-navy-900">{{ cabinet.dossiers }}</span> société(s)
              </template>
            </Column>
            <Column header="Statut" header-class="px-5 py-3 text-left" body-class="px-5 py-4">
              <template #body="{ data: cabinet }">
                <span class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border"
                  :class="cabinet.suspendu
                    ? 'bg-red-50 text-red-700 border-red-200'
                    : 'bg-green-50 text-green-700 border-green-200'">
                  {{ cabinet.suspendu ? 'Suspendu' : 'Actif' }}
                </span>
              </template>
            </Column>
            <Column header="Actions" header-class="px-5 py-3 text-right" body-class="px-5 py-4 text-right">
              <template #body="{ data: cabinet }">
                <div class="flex flex-wrap items-center justify-end gap-3">
                  <button type="button" class="text-xs font-semibold text-navy-700 hover:text-navy-900"
                    @click="ouvrirFormulaireAdmin(cabinet)">
                    + Administrateur
                  </button>
                  <button type="button" class="text-xs font-semibold text-navy-700 hover:text-navy-900"
                    @click="changerSousDomaine(cabinet)">
                    Adresse
                  </button>
                  <button type="button"
                    class="text-xs font-semibold"
                    :class="cabinet.suspendu ? 'text-green-700 hover:text-green-900' : 'text-red-600 hover:text-red-800'"
                    @click="changerStatut(cabinet)">
                    {{ cabinet.suspendu ? 'Réactiver' : 'Suspendre' }}
                  </button>
                </div>
              </template>
            </Column>
          </DataTable>
        </div>
      </div>

      <!-- Rappel -->
      <div class="bg-slate-50 border border-slate-200 rounded-xl p-5 text-xs text-slate-600 leading-relaxed space-y-2">
        <p class="font-bold text-navy-900 text-sm">Suspension d'un cabinet</p>
        <p>
          Un cabinet suspendu ne peut plus se connecter ni appeler l'API, pour le propriétaire
          comme pour ses administrateurs et gestionnaires. Les données, les sociétés et les
          bulletins sont conservés ; la réactivation rétablit l'accès.
        </p>
        <p>
          Les constantes de paie et le plan de paie restent accessibles dans les onglets
          <NuxtLink to="/admin/constantes" class="font-semibold text-navy-700 hover:underline">Constantes</NuxtLink>
          et <NuxtLink to="/admin/plan-paie" class="font-semibold text-navy-700 hover:underline">Plan de paie</NuxtLink>.
        </p>
      </div>
    </template>
  </div>
</template>
