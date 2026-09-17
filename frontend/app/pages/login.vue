<script setup>
definePageMeta({
  layout: false
})

const route = useRoute()
const router = useRouter()
const { user, login, signupCabinet, loading, getDefaultRedirect } = useSupabase()

const isRegister = ref(route.query.register === 'true')
const currentStep = ref(1) // Étape 1 : Infos Cabinet, Étape 2 : Identifiants Gestionnaire

// Champs de connexion
const loginEmail = ref('')
const loginPassword = ref('')

// Champs d'inscription Cabinet
const cabinetNom = ref('')
const cabinetTelephone = ref('')
const cabinetVille = ref('')
const cabinetPays = ref('Côte d\'Ivoire')

const firstName = ref('')
const lastName = ref('')
const email = ref('')
const password = ref('')
const passwordConfirm = ref('')

const showPassword = ref(false)
const errorMsg = ref('')
const successMsg = ref('')
const fieldErrors = ref({})

// Watch query params to toggle mode
watch(() => route.query.register, (val) => {
  isRegister.value = val === 'true'
  currentStep.value = 1
  fieldErrors.value = {}
  errorMsg.value = ''
  successMsg.value = ''
})

const redirectToPlatform = () => {
  const dest = getDefaultRedirect(user.value)
  router.push(dest)
}

const validateStep1 = () => {
  fieldErrors.value = {}
  errorMsg.value = ''
  let hasError = false

  if (!cabinetNom.value.trim()) {
    fieldErrors.value.cabinetNom = 'Le nom de votre cabinet ou société est obligatoire.'
    hasError = true
  }

  if (hasError) return false
  return true
}

const goToStep2 = () => {
  if (validateStep1()) {
    currentStep.value = 2
  }
}

const handleLogin = async () => {
  errorMsg.value = ''
  fieldErrors.value = {}

  let hasError = false
  if (!loginEmail.value) {
    fieldErrors.value.loginEmail = 'Veuillez saisir votre adresse email.'
    hasError = true
  }
  if (!loginPassword.value) {
    fieldErrors.value.loginPassword = 'Veuillez saisir votre mot de passe.'
    hasError = true
  }

  if (hasError) return

  const { error } = await login(loginEmail.value, loginPassword.value)
  if (error) {
    errorMsg.value = error
  } else {
    redirectToPlatform()
  }
}

const handleRegisterCabinet = async () => {
  errorMsg.value = ''
  fieldErrors.value = {}

  let hasError = false

  if (!cabinetNom.value.trim()) {
    currentStep.value = 1
    fieldErrors.value.cabinetNom = 'Le nom de votre cabinet est obligatoire.'
    return
  }

  if (!firstName.value.trim()) {
    fieldErrors.value.firstName = 'Veuillez renseigner votre prénom.'
    hasError = true
  }

  if (!lastName.value.trim()) {
    fieldErrors.value.lastName = 'Veuillez renseigner votre nom.'
    hasError = true
  }

  if (!email.value.trim()) {
    fieldErrors.value.email = 'Veuillez renseigner votre adresse email professionnelle.'
    hasError = true
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
    fieldErrors.value.email = 'Veuillez renseigner une adresse email valide.'
    hasError = true
  }

  if (!password.value || password.value.length < 8) {
    fieldErrors.value.password = 'Le mot de passe doit contenir au moins 8 caractères.'
    hasError = true
  }

  if (password.value !== passwordConfirm.value) {
    fieldErrors.value.passwordConfirm = 'Les mots de passe ne correspondent pas.'
    hasError = true
  }

  if (hasError) return

  const res = await signupCabinet({
    prenom: firstName.value.trim(),
    nom: lastName.value.trim(),
    email: email.value.trim().toLowerCase(),
    password: password.value,
    cabinet_nom: cabinetNom.value.trim(),
    cabinet_telephone: cabinetTelephone.value.trim() || undefined,
    cabinet_ville: cabinetVille.value.trim() ? `${cabinetVille.value.trim()} (${cabinetPays.value})` : cabinetPays.value
  })

  if (res.error) {
    errorMsg.value = res.error
  } else {
    successMsg.value = 'Votre espace Cabinet a été créé avec succès ! Redirection en cours...'
    setTimeout(() => {
      redirectToPlatform()
    }, 1200)
  }
}

onMounted(() => {
  if (user.value) {
    redirectToPlatform()
  }
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-emerald-50/30 flex flex-col justify-center py-10 px-4 sm:px-6 lg:px-8 font-sans selection:bg-emerald-100 selection:text-emerald-900">
    <!-- Top accent bar -->
    <div class="h-1.5 bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-500 fixed top-0 left-0 right-0 w-full shadow-sm" />

    <div class="sm:mx-auto sm:w-full sm:max-w-xl text-center">
      <!-- Logo payohada -->
      <div class="flex justify-center mb-4">
        <img
          src="/payohada-logo.png"
          alt="payohada"
          class="h-12 sm:h-14 w-auto object-contain drop-shadow-sm transition-transform hover:scale-105"
        >
      </div>

      <!-- Titre contextuel -->
      <template v-if="isRegister">
        <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-semibold mb-3">
          <UIcon
            name="i-lucide-building-2"
            class="w-3.5 h-3.5"
          />
          <span>Espace Cabinet Comptable & RH</span>
        </div>
        <h1 class="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Créer un compte Cabinet
        </h1>
        <p class="mt-2 text-sm text-slate-600 max-w-md mx-auto">
          Gérez l'ensemble de vos dossiers clients, calculez vos bulletins conformes OHADA et pilotez vos déclarations sociales en toute simplicité.
        </p>
      </template>

      <template v-else>
        <h1 class="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Connexion à payohada
        </h1>
        <p class="mt-2 text-sm text-slate-600">
          Accédez à vos dossiers d'entreprises, vos simulations et bulletins de paie.
        </p>
      </template>

      <!-- Toggle inscription / connexion -->
      <div class="mt-3 text-sm">
        <span class="text-slate-500">
          {{ isRegister ? "Vous avez déjà un compte ?" : "Vous représentez un cabinet ou un gestionnaire ?" }}
        </span>
        <button
          class="ml-1.5 font-semibold text-emerald-600 hover:text-emerald-700 hover:underline transition-colors"
          @click="isRegister = !isRegister; errorMsg = ''; successMsg = ''; fieldErrors = {}; currentStep = 1"
        >
          {{ isRegister ? "Connectez-vous ici" : "Inscrivez votre cabinet" }}
        </button>
      </div>
    </div>

    <!-- Main Card Container -->
    <div class="mt-6 sm:mx-auto sm:w-full sm:max-w-xl">
      <div class="bg-white py-8 px-6 shadow-xl border border-slate-200/80 rounded-2xl sm:px-10 relative overflow-hidden backdrop-blur-sm">
        <!-- Alerts -->
        <div
          v-if="errorMsg"
          class="mb-5 p-3.5 bg-red-50/90 border border-red-200 text-red-700 rounded-xl text-sm flex items-start space-x-2.5"
        >
          <UIcon
            name="i-lucide-alert-circle"
            class="w-5 h-5 text-red-500 shrink-0 mt-0.5"
          />
          <span class="font-medium">{{ errorMsg }}</span>
        </div>

        <div
          v-if="successMsg"
          class="mb-5 p-3.5 bg-emerald-50/90 border border-emerald-200 text-emerald-700 rounded-xl text-sm flex items-start space-x-2.5"
        >
          <UIcon
            name="i-lucide-check-circle"
            class="w-5 h-5 text-emerald-600 shrink-0 mt-0.5"
          />
          <span class="font-medium">{{ successMsg }}</span>
        </div>

        <!-- ============================================== -->
        <!-- FORMULAIRE INSCRIPTION CABINET (WIZARD 2 ÉTAPES) -->
        <!-- ============================================== -->
        <div v-if="isRegister">
          <!-- Stepper Indicator -->
          <div class="mb-8">
            <div class="flex items-center justify-between relative">
              <div class="absolute left-0 top-1/2 -translate-y-1/2 h-0.5 bg-slate-200 w-full z-0" />
              <div
                class="absolute left-0 top-1/2 -translate-y-1/2 h-0.5 bg-emerald-500 transition-all duration-300 z-0"
                :style="{ width: currentStep === 1 ? '50%' : '100%' }"
              />

              <!-- Step 1 Button -->
              <button
                type="button"
                class="relative z-10 flex items-center gap-2 bg-white px-3 py-1 rounded-full border transition-all text-xs font-medium"
                :class="currentStep === 1 ? 'border-emerald-500 text-emerald-700 ring-2 ring-emerald-100 shadow-sm' : 'border-slate-300 text-slate-600 hover:border-slate-400'"
                @click="currentStep = 1"
              >
                <span
                  class="w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold text-white"
                  :class="currentStep === 1 ? 'bg-emerald-600' : 'bg-emerald-500'"
                >
                  1
                </span>
                <span>Votre Cabinet</span>
              </button>

              <!-- Step 2 Button -->
              <button
                type="button"
                class="relative z-10 flex items-center gap-2 bg-white px-3 py-1 rounded-full border transition-all text-xs font-medium"
                :class="currentStep === 2 ? 'border-emerald-500 text-emerald-700 ring-2 ring-emerald-100 shadow-sm' : 'border-slate-300 text-slate-500 hover:border-slate-400'"
                @click="goToStep2"
              >
                <span
                  class="w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold"
                  :class="currentStep === 2 ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'"
                >
                  2
                </span>
                <span>Gestionnaire Référent</span>
              </button>
            </div>
          </div>

          <!-- Étape 1 : Informations du Cabinet -->
          <div
            v-show="currentStep === 1"
            class="space-y-5"
          >
            <div class="border-b border-slate-100 pb-3 mb-4">
              <h2 class="text-base font-bold text-slate-800 flex items-center gap-2">
                <UIcon
                  name="i-lucide-briefcase"
                  class="w-4 h-4 text-emerald-600"
                />
                Informations sur la structure
              </h2>
              <p class="text-xs text-slate-500 mt-0.5">
                Renseignez les coordonnées professionnelles de votre cabinet d'expertise ou fiduciaire.
              </p>
            </div>

            <div>
              <label
                for="cabinet_nom"
                class="block text-xs font-bold uppercase tracking-wider text-slate-700"
              >
                Nom du Cabinet ou de la Société <span class="text-red-500">*</span>
              </label>
              <div class="mt-1 relative">
                <input
                  id="cabinet_nom"
                  v-model="cabinetNom"
                  type="text"
                  required
                  placeholder="Ex: Cabinet Audit & Paie Afrique, FIDUCO..."
                  :class="[
                    'block w-full px-3.5 py-2.5 border rounded-xl focus:outline-none text-sm transition-all',
                    fieldErrors.cabinetNom ? 'border-red-300 focus:ring-2 focus:ring-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500'
                  ]"
                >
              </div>
              <p
                v-if="fieldErrors.cabinetNom"
                class="mt-1 text-xs text-red-600 font-medium"
              >
                {{ fieldErrors.cabinetNom }}
              </p>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label
                  for="cabinet_telephone"
                  class="block text-xs font-bold uppercase tracking-wider text-slate-700"
                >
                  Téléphone professionnel
                </label>
                <div class="mt-1 relative">
                  <input
                    id="cabinet_telephone"
                    v-model="cabinetTelephone"
                    type="tel"
                    placeholder="Ex: +225 07 00 00 00 00"
                    class="block w-full px-3.5 py-2.5 border border-slate-300 rounded-xl focus:outline-none text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all"
                  >
                </div>
              </div>

              <div>
                <label
                  for="cabinet_ville"
                  class="block text-xs font-bold uppercase tracking-wider text-slate-700"
                >
                  Ville / Commune
                </label>
                <div class="mt-1 relative">
                  <input
                    id="cabinet_ville"
                    v-model="cabinetVille"
                    type="text"
                    placeholder="Ex: Abidjan, Cocody"
                    class="block w-full px-3.5 py-2.5 border border-slate-300 rounded-xl focus:outline-none text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all"
                  >
                </div>
              </div>
            </div>

            <div>
              <label
                for="cabinet_pays"
                class="block text-xs font-bold uppercase tracking-wider text-slate-700"
              >
                Zone OHADA / Pays principal
              </label>
              <select
                id="cabinet_pays"
                v-model="cabinetPays"
                class="mt-1 block w-full px-3.5 py-2.5 border border-slate-300 rounded-xl focus:outline-none text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 bg-white"
              >
                <option value="Côte d'Ivoire">
                  Côte d'Ivoire (Conforme CNPS / CMU / Barème IGR)
                </option>
                <option value="Sénégal">
                  Sénégal (Zone UEMOA / OHADA)
                </option>
                <option value="Cameroun">
                  Cameroun (Zone CEMAC / OHADA)
                </option>
                <option value="Bénin">
                  Bénin (Zone UEMOA / OHADA)
                </option>
                <option value="Togo">
                  Togo (Zone UEMOA / OHADA)
                </option>
                <option value="Mali">
                  Mali (Zone UEMOA / OHADA)
                </option>
                <option value="Burkina Faso">
                  Burkina Faso (Zone UEMOA / OHADA)
                </option>
                <option value="Gabon">
                  Gabon (Zone CEMAC / OHADA)
                </option>
                <option value="Congo">
                  Congo (Zone CEMAC / OHADA)
                </option>
                <option value="Autre">
                  Autre pays espace OHADA
                </option>
              </select>
            </div>

            <div class="pt-2">
              <button
                type="button"
                class="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl shadow-md text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 transition-all"
                @click="goToStep2"
              >
                <span>Étape suivante : Identifiants administrateur</span>
                <UIcon
                  name="i-lucide-arrow-right"
                  class="w-4 h-4"
                />
              </button>
            </div>
          </div>

          <!-- Étape 2 : Responsable du Cabinet & Identifiants -->
          <form
            v-show="currentStep === 2"
            class="space-y-4"
            @submit.prevent="handleRegisterCabinet"
          >
            <div class="border-b border-slate-100 pb-3 mb-2">
              <h2 class="text-base font-bold text-slate-800 flex items-center gap-2">
                <UIcon
                  name="i-lucide-user-check"
                  class="w-4 h-4 text-emerald-600"
                />
                Compte du Gestionnaire Référent
              </h2>
              <p class="text-xs text-slate-500 mt-0.5">
                Ces accès vous permettront d'administrer votre cabinet et vos dossiers d'entreprises.
              </p>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label
                  for="first_name"
                  class="block text-xs font-bold uppercase tracking-wider text-slate-700"
                >
                  Prénom <span class="text-red-500">*</span>
                </label>
                <input
                  id="first_name"
                  v-model="firstName"
                  type="text"
                  required
                  placeholder="Jean"
                  :class="[
                    'mt-1 block w-full px-3.5 py-2.5 border rounded-xl focus:outline-none text-sm transition-all',
                    fieldErrors.firstName ? 'border-red-300 focus:ring-2 focus:ring-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500'
                  ]"
                >
                <p
                  v-if="fieldErrors.firstName"
                  class="mt-1 text-xs text-red-600 font-medium"
                >
                  {{ fieldErrors.firstName }}
                </p>
              </div>

              <div>
                <label
                  for="last_name"
                  class="block text-xs font-bold uppercase tracking-wider text-slate-700"
                >
                  Nom <span class="text-red-500">*</span>
                </label>
                <input
                  id="last_name"
                  v-model="lastName"
                  type="text"
                  required
                  placeholder="Kouassi"
                  :class="[
                    'mt-1 block w-full px-3.5 py-2.5 border rounded-xl focus:outline-none text-sm transition-all',
                    fieldErrors.lastName ? 'border-red-300 focus:ring-2 focus:ring-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500'
                  ]"
                >
                <p
                  v-if="fieldErrors.lastName"
                  class="mt-1 text-xs text-red-600 font-medium"
                >
                  {{ fieldErrors.lastName }}
                </p>
              </div>
            </div>

            <div>
              <label
                for="reg_email"
                class="block text-xs font-bold uppercase tracking-wider text-slate-700"
              >
                Email professionnel (Identifiant de connexion) <span class="text-red-500">*</span>
              </label>
              <input
                id="reg_email"
                v-model="email"
                type="email"
                required
                placeholder="direction@votre-cabinet.com"
                :class="[
                  'mt-1 block w-full px-3.5 py-2.5 border rounded-xl focus:outline-none text-sm transition-all',
                  fieldErrors.email ? 'border-red-300 focus:ring-2 focus:ring-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500'
                ]"
              >
              <p
                v-if="fieldErrors.email"
                class="mt-1 text-xs text-red-600 font-medium"
              >
                {{ fieldErrors.email }}
              </p>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label
                  for="reg_password"
                  class="block text-xs font-bold uppercase tracking-wider text-slate-700"
                >
                  Mot de passe <span class="text-red-500">*</span>
                </label>
                <div class="mt-1 relative">
                  <input
                    id="reg_password"
                    v-model="password"
                    :type="showPassword ? 'text' : 'password'"
                    required
                    placeholder="8 caractères min."
                    :class="[
                      'block w-full px-3.5 py-2.5 pr-10 border rounded-xl focus:outline-none text-sm transition-all',
                      fieldErrors.password ? 'border-red-300 focus:ring-2 focus:ring-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500'
                    ]"
                  >
                  <button
                    type="button"
                    class="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
                    @click="showPassword = !showPassword"
                  >
                    <UIcon
                      :name="showPassword ? 'i-lucide-eye-off' : 'i-lucide-eye'"
                      class="w-4 h-4"
                    />
                  </button>
                </div>
                <p
                  v-if="fieldErrors.password"
                  class="mt-1 text-xs text-red-600 font-medium"
                >
                  {{ fieldErrors.password }}
                </p>
              </div>

              <div>
                <label
                  for="password_confirm"
                  class="block text-xs font-bold uppercase tracking-wider text-slate-700"
                >
                  Confirmer le mot de passe <span class="text-red-500">*</span>
                </label>
                <input
                  id="password_confirm"
                  v-model="passwordConfirm"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  placeholder="Répétez le mot de passe"
                  :class="[
                    'mt-1 block w-full px-3.5 py-2.5 border rounded-xl focus:outline-none text-sm transition-all',
                    fieldErrors.passwordConfirm ? 'border-red-300 focus:ring-2 focus:ring-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500'
                  ]"
                >
                <p
                  v-if="fieldErrors.passwordConfirm"
                  class="mt-1 text-xs text-red-600 font-medium"
                >
                  {{ fieldErrors.passwordConfirm }}
                </p>
              </div>
            </div>

            <!-- Récapitulatif Cabinet -->
            <div class="mt-3 p-3 bg-slate-50 border border-slate-200/80 rounded-xl flex items-center justify-between text-xs text-slate-600">
              <div class="flex items-center gap-2">
                <UIcon
                  name="i-lucide-shield-check"
                  class="w-4 h-4 text-emerald-600 shrink-0"
                />
                <span>Cabinet : <strong class="text-slate-800">{{ cabinetNom || 'Non renseigné' }}</strong></span>
              </div>
              <button
                type="button"
                class="text-emerald-600 hover:text-emerald-700 font-semibold underline"
                @click="currentStep = 1"
              >
                Modifier
              </button>
            </div>

            <div class="pt-3 flex gap-3">
              <button
                type="button"
                class="w-1/3 py-2.5 px-4 border border-slate-300 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none transition-colors"
                @click="currentStep = 1"
              >
                Retour
              </button>
              <button
                type="submit"
                :disabled="loading"
                class="w-2/3 flex justify-center items-center py-2.5 px-4 rounded-xl shadow-md text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 transition-colors disabled:opacity-50"
              >
                <UIcon
                  v-if="loading"
                  name="i-lucide-loader-2"
                  class="w-5 h-5 animate-spin mr-2"
                />
                <span>Créer mon espace Cabinet</span>
              </button>
            </div>
          </form>
        </div>

        <!-- ============================================== -->
        <!-- FORMULAIRE DE CONNEXION                        -->
        <!-- ============================================== -->
        <form
          v-else
          class="space-y-5"
          @submit.prevent="handleLogin"
        >
          <div>
            <label
              for="login_email"
              class="block text-xs font-bold uppercase tracking-wider text-slate-700"
            >
              Adresse Email
            </label>
            <input
              id="login_email"
              v-model="loginEmail"
              type="email"
              required
              placeholder="votre@email.com"
              :class="[
                'mt-1 block w-full px-3.5 py-2.5 border rounded-xl focus:outline-none text-sm transition-all',
                fieldErrors.loginEmail ? 'border-red-300 focus:ring-2 focus:ring-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500'
              ]"
            >
            <p
              v-if="fieldErrors.loginEmail"
              class="mt-1 text-xs text-red-600 font-medium"
            >
              {{ fieldErrors.loginEmail }}
            </p>
          </div>

          <div>
            <div class="flex items-center justify-between">
              <label
                for="login_password"
                class="block text-xs font-bold uppercase tracking-wider text-slate-700"
              >
                Mot de Passe
              </label>
            </div>
            <div class="mt-1 relative">
              <input
                id="login_password"
                v-model="loginPassword"
                :type="showPassword ? 'text' : 'password'"
                required
                placeholder="••••••••"
                :class="[
                  'block w-full px-3.5 py-2.5 pr-10 border rounded-xl focus:outline-none text-sm transition-all',
                  fieldErrors.loginPassword ? 'border-red-300 focus:ring-2 focus:ring-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500'
                ]"
              >
              <button
                type="button"
                class="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
                @click="showPassword = !showPassword"
              >
                <UIcon
                  :name="showPassword ? 'i-lucide-eye-off' : 'i-lucide-eye'"
                  class="w-4 h-4"
                />
              </button>
            </div>
            <p
              v-if="fieldErrors.loginPassword"
              class="mt-1 text-xs text-red-600 font-medium"
            >
              {{ fieldErrors.loginPassword }}
            </p>
          </div>

          <div class="pt-2">
            <button
              type="submit"
              :disabled="loading"
              class="w-full flex justify-center items-center py-2.5 px-4 rounded-xl shadow-md text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 transition-all disabled:opacity-50"
            >
              <UIcon
                v-if="loading"
                name="i-lucide-loader-2"
                class="w-5 h-5 animate-spin mr-2"
              />
              <span>Se connecter</span>
            </button>
          </div>
        </form>

        <!-- Bas de carte : Rappels de conformité & sécurité -->
        <div class="mt-6 pt-5 border-t border-slate-100 text-xs text-slate-500 grid grid-cols-3 gap-2 text-center">
          <div class="flex flex-col items-center">
            <UIcon
              name="i-lucide-scale"
              class="w-4 h-4 text-emerald-600 mb-1"
            />
            <span class="font-medium">Conformité OHADA</span>
          </div>
          <div class="flex flex-col items-center">
            <UIcon
              name="i-lucide-shield-alert"
              class="w-4 h-4 text-emerald-600 mb-1"
            />
            <span class="font-medium">Données Chiffrées</span>
          </div>
          <div class="flex flex-col items-center">
            <UIcon
              name="i-lucide-folder-git-2"
              class="w-4 h-4 text-emerald-600 mb-1"
            />
            <span class="font-medium">Multi-entreprises</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
