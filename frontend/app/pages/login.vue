<script setup>
definePageMeta({
  layout: false
})

const route = useRoute()
const router = useRouter()
const { user, login, signup, loading } = useSupabase()

const isRegister = ref(route.query.register === 'true')
const email = ref('')
const password = ref('')
const firstName = ref('')
const lastName = ref('')
const errorMsg = ref('')

// Watch query params to toggle mode
watch(() => route.query.register, (val) => {
  isRegister.value = val === 'true'
})

const handleSubmit = async () => {
  errorMsg.value = ''
  if (!email.value) {
    errorMsg.value = 'Veuillez saisir votre adresse email.'
    return
  }
  
  if (isRegister.value) {
    if (!password.value || password.value.length < 6) {
      errorMsg.value = 'Le mot de passe doit contenir au moins 6 caractères.'
      return
    }
    if (!firstName.value || !lastName.value) {
      errorMsg.value = 'Veuillez remplir votre nom et prénom.'
      return
    }

    const { error } = await signup(email.value, password.value, {
      first_name: firstName.value,
      last_name: lastName.value
    })

    if (error) {
      errorMsg.value = error
    } else {
      router.push('/dossiers')
    }
  } else {
    const { error } = await login(email.value, password.value)
    if (error) {
      errorMsg.value = error
    } else {
      router.push('/dossiers')
    }
  }
}

const handleMockLogin = async () => {
  errorMsg.value = ''
  // Use a default mock email or whatever the user entered
  const mockEmail = email.value || 'demo@payohada.cloud'
  const { error } = await login(mockEmail) // Without password = mock login
  if (!error) {
    router.push('/dossiers')
  }
}

// If already logged in, redirect to dossiers
onMounted(() => {
  if (user.value) {
    router.push('/dossiers')
  }
})
</script>

<template>
  <div class="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans selection:bg-green-100 selection:text-green-900">
    <div class="h-1 bg-green-600 fixed top-0 left-0 right-0 w-full" />

    <div class="sm:mx-auto sm:w-full sm:max-w-md text-center">
      <!-- Logo payohada -->
      <div class="inline-flex w-12 h-12 rounded-xl bg-green-600 items-center justify-center text-white font-bold text-2xl shadow-sm mb-4">
        P
      </div>
      <h2 class="text-3xl font-extrabold text-slate-900">
        {{ isRegister ? "Créer un compte" : "Connexion à payohada" }}
      </h2>
      <p class="mt-2 text-sm text-slate-600">
        {{ isRegister ? "Ou" : "Ou" }}
        <button 
          @click="isRegister = !isRegister; errorMsg = ''" 
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
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
              />
            </div>
            <div>
              <label for="last_name" class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Nom</label>
              <input 
                id="last_name" 
                v-model="lastName" 
                type="text" 
                required
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
              />
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
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
            />
          </div>

          <div v-if="!isRegister || password || true">
            <label for="password" class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Mot de Passe</label>
            <input 
              id="password" 
              v-model="password" 
              type="password" 
              :required="!isRegister"
              placeholder="••••••••"
              class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
            />
          </div>

          <div>
            <button 
              type="submit" 
              :disabled="loading"
              class="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors disabled:opacity-50"
            >
              <UIcon v-if="loading" name="i-lucide-loader-2" class="w-5 h-5 animate-spin mr-2" />
              {{ isRegister ? "Créer mon compte Supabase" : "Connexion avec Supabase" }}
            </button>
          </div>
        </form>

        <!-- Mock demo mode divider -->
        <div class="mt-6">
          <div class="relative">
            <div class="absolute inset-0 flex items-center">
              <div class="w-full border-t border-slate-200"></div>
            </div>
            <div class="relative flex justify-center text-xs uppercase">
              <span class="px-2 bg-white text-slate-400 font-semibold tracking-wider">Option Locale / Démo</span>
            </div>
          </div>

          <div class="mt-6">
            <button 
              type="button"
              @click="handleMockLogin"
              class="w-full flex items-center justify-center px-4 py-2.5 border border-dashed border-amber-300 rounded-lg text-sm font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 focus:outline-none transition-colors"
            >
              <UIcon name="i-lucide-shield-alert" class="w-5 h-5 mr-2 text-amber-500" />
              Accéder en Mode Démo (Sans Supabase)
            </button>
            <p class="mt-2 text-[11px] text-slate-400 text-center">
              Utilise des données locales fictives et génère un jeton accepté par le serveur backend FastAPI en mode débug.
            </p>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>
