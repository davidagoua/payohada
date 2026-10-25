<script setup lang="ts">
definePageMeta({
  layout: false
})

const config = useRuntimeConfig()

const email = ref('')
const submitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const emailInvalide = computed(
  () => !!email.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)
)

const handleSubmit = async () => {
  errorMessage.value = ''
  successMessage.value = ''

  if (!email.value.trim()) {
    errorMessage.value = 'Veuillez saisir votre adresse email.'
    return
  }
  if (emailInvalide.value) {
    errorMessage.value = 'Cette adresse email n\'est pas valide.'
    return
  }

  submitting.value = true
  try {
    const apiBase = config.public.apiBase || 'http://localhost:8000'
    // Appel direct (sans useApi) : cette page est publique, une réponse 401
    // ne doit pas déclencher de déconnexion.
    const reponse = await $fetch<any>(`${apiBase}/auth/forgot-password`, {
      method: 'POST',
      body: { email: email.value.trim() }
    })
    successMessage.value = reponse?.message
      || 'Si un compte est associé à cette adresse, un email vient d\'être envoyé.'
  } catch (e: any) {
    if (e?.status === 429) {
      errorMessage.value = e?.data?.detail
        || 'Trop de demandes. Patientez quelques minutes avant de réessayer.'
    } else {
      errorMessage.value = 'Impossible de traiter la demande pour le moment. Réessayez plus tard.'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthShell>
    <!-- En-tête de la carte -->
    <div class="flex items-center gap-3 mb-6">
      <div class="w-11 h-11 bg-navy-50 border border-navy-200 flex items-center justify-center text-navy-700 shrink-0">
        <UIcon name="i-lucide-key-round" class="w-5 h-5" />
      </div>
      <div>
        <h1 class="text-xl font-bold text-navy-900 tracking-tight">
          Mot de passe oublié
        </h1>
        <p class="text-xs text-slate-500 mt-0.5">
          Recevez un lien pour choisir un nouveau mot de passe
        </p>
      </div>
    </div>

    <div class="bg-white border border-slate-200 border-t-4 border-t-navy-900 shadow-flat p-7 sm:p-8">
      <!-- Confirmation -->
      <div
        v-if="successMessage"
        class="mb-5 p-4 bg-green-50 border border-green-200 flex items-start gap-3"
      >
        <UIcon name="i-lucide-mail-check" class="w-5 h-5 text-green-600 shrink-0 mt-0.5" />
        <div class="text-xs text-green-900 leading-relaxed space-y-1.5">
          <p class="font-bold">Demande enregistrée</p>
          <p>{{ successMessage }}</p>
          <p class="text-green-800/80">
            Le lien est valable 30 minutes et ne peut servir qu'une fois.
          </p>
        </div>
      </div>

      <!-- Erreur -->
      <div
        v-if="errorMessage"
        class="mb-5 p-3.5 bg-red-50 border border-red-200 flex items-center gap-2.5 text-red-700 text-xs font-semibold"
        role="alert"
      >
        <UIcon name="i-lucide-alert-circle" class="w-4 h-4 text-red-600 shrink-0" />
        <span>{{ errorMessage }}</span>
      </div>

      <form v-if="!successMessage" class="space-y-4" @submit.prevent="handleSubmit">
        <div>
          <label for="email" class="block text-xs font-bold uppercase tracking-wider text-slate-700">
            Adresse email du compte
          </label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="username"
            required
            placeholder="vous@entreprise.ci"
            :class="[
              'mt-1 block w-full px-3.5 py-2.5 border focus:outline-none text-sm transition-all',
              emailInvalide
                ? 'border-red-300 bg-red-50/30'
                : 'border-slate-300'
            ]"
          >
          <p class="mt-1.5 text-[11px] text-slate-500">
            Utilisez l'adresse avec laquelle vous vous connectez habituellement.
          </p>
        </div>

        <button
          type="submit"
          :disabled="submitting"
          class="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white text-sm font-bold shadow-flat transition-colors"
        >
          <UIcon v-if="submitting" name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
          <UIcon v-else name="i-lucide-send" class="w-4 h-4" />
          {{ submitting ? 'Envoi en cours…' : 'Envoyer le lien de réinitialisation' }}
        </button>
      </form>

      <div class="mt-6 pt-5 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs">
        <NuxtLink to="/login" class="font-semibold text-navy-700 hover:text-navy-900 inline-flex items-center gap-1.5">
          <UIcon name="i-lucide-arrow-left" class="w-3.5 h-3.5" />
          Retour à la connexion
        </NuxtLink>
        <span class="text-slate-400">Besoin d'aide ? Contactez votre gestionnaire</span>
      </div>
    </div>

    <p class="mt-5 text-center text-[11px] text-slate-500">
      Pour votre sécurité, cette page n'indique jamais si une adresse est enregistrée.
    </p>
  </AuthShell>
</template>
