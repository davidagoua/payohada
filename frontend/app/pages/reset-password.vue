<script setup lang="ts">
definePageMeta({
  layout: false
})

const config = useRuntimeConfig()
const route = useRoute()
const router = useRouter()

const apiBase = computed(() => config.public.apiBase || 'http://localhost:8000')
const token = computed(() => (route.query.token as string) || '')

const verification = ref<'en_cours' | 'valide' | 'invalide'>('en_cours')
const emailMasque = ref<string | null>(null)

const nouveauMotDePasse = ref('')
const confirmation = ref('')
const afficherMotDePasse = ref(false)
const submitting = ref(false)
const errorMessage = ref('')
const termine = ref(false)

const regles = computed(() => ({
  longueur: nouveauMotDePasse.value.length >= 8,
  chiffre: /[0-9]/.test(nouveauMotDePasse.value),
  lettre: /[A-Za-z]/.test(nouveauMotDePasse.value)
}))
const motDePasseValide = computed(() => Object.values(regles.value).every(Boolean))
const correspond = computed(
  () => !confirmation.value || nouveauMotDePasse.value === confirmation.value
)

// Vérifie le jeton AVANT d'afficher le formulaire : évite de saisir deux fois
// un mot de passe pour découvrir ensuite que le lien était expiré.
onMounted(async () => {
  if (!token.value) {
    verification.value = 'invalide'
    return
  }
  try {
    const reponse = await $fetch<any>(`${apiBase.value}/auth/reset-password/valider`, {
      params: { token: token.value }
    })
    if (reponse?.valide) {
      emailMasque.value = reponse.email_masque || null
      verification.value = 'valide'
    } else {
      verification.value = 'invalide'
    }
  } catch {
    verification.value = 'invalide'
  }
})

const handleSubmit = async () => {
  errorMessage.value = ''

  if (!motDePasseValide.value) {
    errorMessage.value = 'Le mot de passe doit contenir au moins 8 caractères, des lettres et des chiffres.'
    return
  }
  if (nouveauMotDePasse.value !== confirmation.value) {
    errorMessage.value = 'Les deux mots de passe ne correspondent pas.'
    return
  }

  submitting.value = true
  try {
    const reponse = await $fetch<any>(`${apiBase.value}/auth/reset-password`, {
      method: 'POST',
      body: { token: token.value, new_password: nouveauMotDePasse.value }
    })
    termine.value = true
    // Laisse le temps de lire la confirmation avant de renvoyer vers la connexion.
    setTimeout(() => router.push('/login'), 2500)
    void reponse
  } catch (e: any) {
    if (e?.status === 429) {
      errorMessage.value = e?.data?.detail
        || 'Trop de tentatives. Patientez quelques minutes.'
    } else {
      errorMessage.value = e?.data?.detail
        || 'Ce lien est invalide, déjà utilisé ou expiré. Demandez-en un nouveau.'
      // Un jeton refusé ne doit pas laisser croire qu'il est encore valable.
      if (!e?.data?.detail?.includes('lettres et chiffres')
          && !e?.data?.detail?.includes('différent de l\'ancien')) {
        verification.value = 'invalide'
      }
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-emerald-50/30 flex flex-col justify-center py-10 px-4 sm:px-6 lg:px-8 font-sans">
    <div class="h-1.5 bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-500 fixed top-0 left-0 right-0 w-full shadow-sm" />

    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <div class="flex justify-center mb-5">
        <img src="/payohada-logo.png" alt="payohada" class="h-11 w-auto object-contain">
      </div>

      <div class="bg-white border border-slate-200 rounded-2xl shadow-sm p-7 sm:p-8">
        <!-- Vérification en cours -->
        <div v-if="verification === 'en_cours'" class="flex flex-col items-center gap-3 py-6 text-center">
          <UIcon name="i-lucide-loader-2" class="w-7 h-7 animate-spin text-emerald-600" />
          <p class="text-sm text-slate-600">Vérification de votre lien…</p>
        </div>

        <!-- Lien invalide / expiré -->
        <div v-else-if="verification === 'invalide'" class="text-center">
          <div class="w-12 h-12 mx-auto rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 mb-4">
            <UIcon name="i-lucide-link-2-off" class="w-6 h-6" />
          </div>
          <h1 class="text-base font-bold text-slate-900">Lien inutilisable</h1>
          <p class="mt-2 text-sm text-slate-600 leading-relaxed">
            Ce lien de réinitialisation est invalide, déjà utilisé ou expiré.
            Les liens ne sont valables que 30 minutes et une seule fois.
          </p>
          <NuxtLink
            to="/forgot-password"
            class="mt-6 inline-flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold rounded-xl shadow-sm transition-colors"
          >
            <UIcon name="i-lucide-refresh-cw" class="w-4 h-4" />
            Demander un nouveau lien
          </NuxtLink>
          <NuxtLink to="/login" class="mt-3 block text-xs font-semibold text-slate-500 hover:text-emerald-700">
            Retour à la connexion
          </NuxtLink>
        </div>

        <!-- Succès -->
        <div v-else-if="termine" class="text-center">
          <div class="w-12 h-12 mx-auto rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 mb-4">
            <UIcon name="i-lucide-shield-check" class="w-6 h-6" />
          </div>
          <h1 class="text-base font-bold text-slate-900">Mot de passe mis à jour</h1>
          <p class="mt-2 text-sm text-slate-600">
            Vous pouvez désormais vous connecter avec votre nouveau mot de passe.
          </p>
          <NuxtLink
            to="/login"
            class="mt-6 inline-flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold rounded-xl shadow-sm transition-colors"
          >
            <UIcon name="i-lucide-log-in" class="w-4 h-4" />
            Se connecter
          </NuxtLink>
        </div>

        <!-- Formulaire -->
        <div v-else>
          <div class="flex items-center gap-3 mb-5">
            <div class="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 shrink-0">
              <UIcon name="i-lucide-lock-keyhole" class="w-5 h-5" />
            </div>
            <div>
              <h1 class="text-base font-bold text-slate-900">
                Nouveau mot de passe
              </h1>
              <p v-if="emailMasque" class="text-xs text-slate-500 mt-0.5">
                Compte : <span class="font-mono">{{ emailMasque }}</span>
              </p>
            </div>
          </div>

          <div
            v-if="errorMessage"
            class="mb-5 p-3.5 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2.5 text-red-700 text-xs font-semibold"
            role="alert"
          >
            <UIcon name="i-lucide-alert-circle" class="w-4 h-4 text-red-600 shrink-0" />
            <span>{{ errorMessage }}</span>
          </div>

          <form class="space-y-4" @submit.prevent="handleSubmit">
            <div>
              <label for="nouveau" class="block text-xs font-bold uppercase tracking-wider text-slate-700">
                Nouveau mot de passe
              </label>
              <div class="mt-1 relative">
                <input
                  id="nouveau"
                  v-model="nouveauMotDePasse"
                  :type="afficherMotDePasse ? 'text' : 'password'"
                  autocomplete="new-password"
                  required
                  placeholder="••••••••"
                  class="block w-full px-3.5 py-2.5 pr-10 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm"
                >
                <button
                  type="button"
                  class="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
                  :aria-label="afficherMotDePasse ? 'Masquer' : 'Afficher'"
                  @click="afficherMotDePasse = !afficherMotDePasse"
                >
                  <UIcon :name="afficherMotDePasse ? 'i-lucide-eye-off' : 'i-lucide-eye'" class="w-4 h-4" />
                </button>
              </div>
              <ul class="mt-2 space-y-1 text-[11px]">
                <li :class="regles.longueur ? 'text-emerald-700 font-semibold' : 'text-slate-500'">
                  {{ regles.longueur ? '✓' : '•' }} Au moins 8 caractères
                </li>
                <li :class="regles.lettre && regles.chiffre ? 'text-emerald-700 font-semibold' : 'text-slate-500'">
                  {{ regles.lettre && regles.chiffre ? '✓' : '•' }} Lettres et chiffres
                </li>
              </ul>
            </div>

            <div>
              <label for="confirmation" class="block text-xs font-bold uppercase tracking-wider text-slate-700">
                Confirmer le mot de passe
              </label>
              <input
                id="confirmation"
                v-model="confirmation"
                :type="afficherMotDePasse ? 'text' : 'password'"
                autocomplete="new-password"
                required
                placeholder="••••••••"
                :class="[
                  'mt-1 block w-full px-3.5 py-2.5 border rounded-xl focus:outline-none text-sm',
                  correspond
                    ? 'border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500'
                    : 'border-red-300 focus:ring-2 focus:ring-red-500 bg-red-50/30'
                ]"
              >
              <p v-if="!correspond" class="mt-1.5 text-[11px] text-red-600 font-semibold">
                Les mots de passe ne correspondent pas.
              </p>
            </div>

            <button
              type="submit"
              :disabled="submitting || !motDePasseValide || !correspond"
              class="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white text-sm font-bold rounded-xl shadow-sm transition-colors"
            >
              <UIcon v-if="submitting" name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
              <UIcon v-else name="i-lucide-check" class="w-4 h-4" />
              {{ submitting ? 'Enregistrement…' : 'Enregistrer le nouveau mot de passe' }}
            </button>
          </form>

          <div class="mt-6 pt-5 border-t border-slate-200">
            <NuxtLink to="/login" class="text-xs font-semibold text-slate-600 hover:text-emerald-700 inline-flex items-center gap-1.5">
              <UIcon name="i-lucide-arrow-left" class="w-3.5 h-3.5" />
              Retour à la connexion
            </NuxtLink>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
