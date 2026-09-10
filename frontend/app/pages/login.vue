<script setup>
definePageMeta({
  layout: false
})

const route = useRoute()
const router = useRouter()
const { user, login, signup, loading, getDefaultRedirect } = useSupabase()

const isRegister = ref(route.query.register === 'true')
const email = ref('')
const password = ref('')
const firstName = ref('')
const lastName = ref('')
const errorMsg = ref('')
const fieldErrors = ref({})

// Watch query params to toggle mode
watch(() => route.query.register, (val) => {
  isRegister.value = val === 'true'
  fieldErrors.value = {}
  errorMsg.value = ''
})

const redirectToPlatform = () => {
  const dest = getDefaultRedirect(user.value)
  router.push(dest)
}

const handleSubmit = async () => {
  errorMsg.value = ''
  fieldErrors.value = {}
  
  let hasError = false
  if (!email.value) {
    fieldErrors.value.email = 'Veuillez saisir votre adresse email.'
    hasError = true
  }
  
  if (isRegister.value) {
    if (!password.value || password.value.length < 6) {
      fieldErrors.value.password = 'Le mot de passe doit contenir au moins 6 caractères.'
      hasError = true
    }
    if (!firstName.value) {
      fieldErrors.value.firstName = 'Veuillez remplir votre prénom.'
      hasError = true
    }
    if (!lastName.value) {
      fieldErrors.value.lastName = 'Veuillez remplir votre nom.'
      hasError = true
    }
    if (hasError) return

    const { error } = await signup(email.value, password.value, {
      first_name: firstName.value,
      last_name: lastName.value
    })

    if (error) {
      errorMsg.value = error
    } else {
      redirectToPlatform()
    }
  } else {
    if (!password.value) {
      fieldErrors.value.password = 'Veuillez saisir votre mot de passe.'
      hasError = true
    }
    if (hasError) return

    const { error } = await login(email.value, password.value)
    if (error) {
      errorMsg.value = error
    } else {
      redirectToPlatform()
    }
  }
}

const quickLoginRole = async (targetEmail) => {
  errorMsg.value = ''
  fieldErrors.value = {}
  email.value = targetEmail
  password.value = 'Payohada@123'
  const { error } = await login(targetEmail, 'Payohada@123')
  if (error) {
    // Si échec mot de passe, fallback mock
    await login(targetEmail)
  }
  redirectToPlatform()
}

onMounted(() => {
  if (user.value) {
    redirectToPlatform()
  }
})
</script>

<template>
  <div class="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans selection:bg-green-100 selection:text-green-900">
    <div class="h-1 bg-green-600 fixed top-0 left-0 right-0 w-full" />

    <div class="sm:mx-auto sm:w-full sm:max-w-md text-center">
      <!-- Logo payohada -->
      <div class="flex justify-center mb-6">
        <img 
          src="/payohada-logo.png" 
          alt="payohada" 
          class="h-12 sm:h-14 w-auto object-contain drop-shadow-sm" 
        />
      </div>
      <h2 class="text-2xl sm:text-3xl font-extrabold text-slate-900">
        {{ isRegister ? "Créer un compte" : "Connexion à payohada" }}
      </h2>
      <p class="mt-2 text-sm text-slate-600">
        {{ isRegister ? "Ou" : "Ou" }}
        <button 
          @click="isRegister = !isRegister; errorMsg = ''; fieldErrors = {}" 
          class="font-medium text-green-600 hover:text-green-500 underline"
        >
          {{ isRegister ? "se connecter à un compte existant" : "créer un nouveau compte" }}
        </button>
      </p>
    </div>

    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-white py-8 px-4 shadow-md border border-slate-200 sm:rounded-lg sm:px-10">
        
        <!-- Error Message Alert -->
        <div v-if="errorMsg" class="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex items-center space-x-2">
          <UIcon name="i-lucide-alert-circle" class="w-5 h-5 text-red-500 shrink-0" />
          <span>{{ errorMsg }}</span>
        </div>

        <form @submit.prevent="handleSubmit" class="space-y-6">
          <!-- Register specific fields -->
          <div v-if="isRegister" class="grid grid-cols-2 gap-4">
            <div>
              <label for="first_name" class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Prénom</label>
              <input 
                id="first_name" 
                v-model="firstName" 
                type="text" 
                required
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg focus:outline-none text-sm transition-colors',
                  fieldErrors.firstName ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.firstName" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.firstName }}</p>
            </div>
            <div>
              <label for="last_name" class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom</label>
              <input 
                id="last_name" 
                v-model="lastName" 
                type="text" 
                required
                :class="[
                  'mt-1 block w-full px-3 py-2 border rounded-lg focus:outline-none text-sm transition-colors',
                  fieldErrors.lastName ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
                ]"
              />
              <p v-if="fieldErrors.lastName" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.lastName }}</p>
            </div>
          </div>

          <div>
            <label for="email" class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Adresse Email</label>
            <input 
              id="email" 
              v-model="email" 
              type="email" 
              required
              placeholder="votre@email.com"
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg focus:outline-none text-sm transition-colors',
                fieldErrors.email ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.email" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.email }}</p>
          </div>

          <div v-if="!isRegister || password || true">
            <label for="password" class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Mot de Passe</label>
            <input 
              id="password" 
              v-model="password" 
              type="password" 
              :required="!isRegister"
              placeholder="••••••••"
              :class="[
                'mt-1 block w-full px-3 py-2 border rounded-lg focus:outline-none text-sm transition-colors',
                fieldErrors.password ? 'border-red-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50/30' : 'border-slate-300 focus:ring-2 focus:ring-green-500 focus:border-green-500'
              ]"
            />
            <p v-if="fieldErrors.password" class="mt-1 text-xs text-red-600 font-medium">{{ fieldErrors.password }}</p>
          </div>

          <div>
            <button 
              type="submit" 
              :disabled="loading"
              class="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors disabled:opacity-50"
            >
              <UIcon v-if="loading" name="i-lucide-loader-2" class="w-5 h-5 animate-spin mr-2" />
              {{ isRegister ? "Créer mon compte " : "Connexion" }}
            </button>
          </div>
        </form>

        <!-- 3 Plateformes Démo -->
        <div class="mt-6">
          <div class="relative">
            <div class="absolute inset-0 flex items-center">
              <div class="w-full border-t border-slate-200"></div>
            </div>
            <div class="relative flex justify-center text-xs uppercase">
              <span class="px-2 bg-white text-slate-400 font-bold tracking-wider">Accès Rapide par Plateforme</span>
            </div>
          </div>

          <div class="mt-4 grid grid-cols-3 gap-2">
            <!-- Cabinet -->
            <button 
              type="button"
              class="flex flex-col items-center justify-center p-2.5 rounded-lg border border-slate-250 bg-slate-50 hover:bg-green-50 hover:border-green-300 transition-all cursor-pointer group"
              title="Connexion Gestionnaire / Cabinet"
              @click="quickLoginRole('demo@payohada.cloud')"
            >
              <span class="text-base mb-1">🏢</span>
              <span class="text-[11px] font-bold text-slate-800 group-hover:text-green-800">Cabinet</span>
              <span class="text-[9px] text-slate-500">Multi-dossiers</span>
            </button>

            <!-- Client Entreprise -->
            <button 
              type="button"
              class="flex flex-col items-center justify-center p-2.5 rounded-lg border border-slate-250 bg-slate-50 hover:bg-blue-50 hover:border-blue-300 transition-all cursor-pointer group"
              title="Connexion Entreprise / Client (Saisie variables)"
              @click="quickLoginRole('client.liugong@payohada.com')"
            >
              <span class="text-base mb-1">🏬</span>
              <span class="text-[11px] font-bold text-slate-800 group-hover:text-blue-800">Client</span>
              <span class="text-[9px] text-slate-500">Entreprise</span>
            </button>

            <!-- Salarié -->
            <button 
              type="button"
              class="flex flex-col items-center justify-center p-2.5 rounded-lg border border-slate-250 bg-slate-50 hover:bg-purple-50 hover:border-purple-300 transition-all cursor-pointer group"
              title="Connexion Salarié (Bulletins & Réclamations)"
              @click="quickLoginRole('employee.test@payohada.com')"
            >
              <span class="text-base mb-1">👤</span>
              <span class="text-[11px] font-bold text-slate-800 group-hover:text-purple-800">Salarié</span>
              <span class="text-[9px] text-slate-500">Mes Bulletins</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>
