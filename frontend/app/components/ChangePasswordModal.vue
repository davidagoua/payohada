<script setup lang="ts">
const { user, changePassword, loading: authLoading } = useSupabase()
const { isOpen, dismissModal, closeModal } = useChangePasswordModal()
const toast = useToast()

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')

const showOldPassword = ref(false)
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)

const submitting = ref(false)
const errorMessage = ref('')

// Reset fields when opening modal
watch(isOpen, (val) => {
  if (val) {
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    errorMessage.value = ''
    showOldPassword.value = false
    showNewPassword.value = false
    showConfirmPassword.value = false
  }
})

const isDefault = computed(() => !!user.value?.is_default_password)

const handleSubmit = async () => {
  errorMessage.value = ''

  if (!oldPassword.value) {
    errorMessage.value = 'Veuillez saisir votre mot de passe actuel.'
    return
  }

  if (!newPassword.value) {
    errorMessage.value = 'Veuillez saisir votre nouveau mot de passe.'
    return
  }

  if (newPassword.value.length < 6) {
    errorMessage.value = 'Le nouveau mot de passe doit contenir au moins 6 caractères.'
    return
  }

  if (newPassword.value === 'Payohada@123') {
    errorMessage.value = 'Le nouveau mot de passe doit être différent du mot de passe par défaut (Payohada@123).'
    return
  }

  if (newPassword.value !== confirmPassword.value) {
    errorMessage.value = 'Les nouveaux mots de passe ne correspondent pas.'
    return
  }

  submitting.value = true
  try {
    const { error, message } = await changePassword(oldPassword.value, newPassword.value)
    if (error) {
      errorMessage.value = error
    } else {
      toast.add({
        title: 'Mot de passe mis à jour',
        description: message || 'Votre mot de passe a été modifié avec succès.',
        color: 'success'
      })
      closeModal()
    }
  } catch (e: any) {
    errorMessage.value = e?.message || 'Une erreur inattendue est survenue.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <UModal v-model:open="isOpen" title="Modification du mot de passe">
    <template #content>
      <div class="p-6 bg-white border border-slate-200 max-w-lg w-full mx-auto shadow-flat">
        <!-- Header -->
        <div class="flex items-start justify-between border-b border-slate-200 pb-4 mb-4">
          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 rounded-lg bg-green-50 border border-green-200 flex items-center justify-center text-green-700 shrink-0">
              <UIcon name="i-lucide-shield-check" class="w-5 h-5" />
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900 uppercase tracking-wider">
                Modifier mon mot de passe
              </h2>
              <p class="text-xs text-slate-500 font-medium mt-0.5">
                {{ isDefault ? 'Sécurisation recommandée de votre compte' : 'Gestion de la sécurité de votre compte' }}
              </p>
            </div>
          </div>
          <button
            type="button"
            @click="dismissModal"
            class="text-slate-400 hover:text-slate-650 p-1 transition-colors cursor-pointer rounded"
            title="Fermer (Échap)"
          >
            <UIcon name="i-lucide-x" class="w-5 h-5" />
          </button>
        </div>

        <!-- Suggestion Banner for Default Password -->
        <div
          v-if="isDefault"
          class="mb-5 p-3.5 bg-amber-50/90 border border-amber-300/80 rounded-none flex items-start gap-3 text-amber-900"
        >
          <UIcon name="i-lucide-shield-alert" class="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div class="text-xs leading-relaxed space-y-1">
            <p class="font-bold text-amber-950">
              Mot de passe par défaut actif
            </p>
            <p class="text-amber-850 text-[11px]">
              Votre compte utilise actuellement le mot de passe provisoire. Pour protéger la confidentialité de vos données de paie, nous vous recommandons vivement de choisir votre propre mot de passe.
            </p>
          </div>
        </div>

        <!-- Error Alert -->
        <div
          v-if="errorMessage"
          class="mb-4 p-3 bg-red-50 border border-red-200 rounded-none flex items-center gap-2.5 text-red-700 text-xs font-semibold"
        >
          <UIcon name="i-lucide-alert-circle" class="w-4 h-4 text-red-600 shrink-0" />
          <span>{{ errorMessage }}</span>
        </div>

        <!-- Form -->
        <form @submit.prevent="handleSubmit" class="space-y-4">
          <!-- Mot de passe actuel -->
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-650 mb-1">
              Mot de passe actuel <span class="text-red-500">*</span>
            </label>
            <div class="relative">
              <input
                v-model="oldPassword"
                :type="showOldPassword ? 'text' : 'password'"
                placeholder="Saisissez votre mot de passe actuel"
                class="block w-full px-3 py-2 pr-10 border border-slate-350 rounded-none text-sm bg-white focus:outline-none focus:border-green-600"
                required
              />
              <button
                type="button"
                @click="showOldPassword = !showOldPassword"
                class="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-650 cursor-pointer"
              >
                <UIcon :name="showOldPassword ? 'i-lucide-eye-off' : 'i-lucide-eye'" class="w-4 h-4" />
              </button>
            </div>
            <p v-if="isDefault" class="text-[11px] text-slate-500 mt-1">
              💡 Votre mot de passe initial est <code class="bg-amber-100/70 text-amber-900 px-1 py-0.5 border border-amber-200 font-mono font-bold text-[10px]">Payohada@123</code>.
            </p>
          </div>

          <!-- Nouveau mot de passe -->
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-650 mb-1">
              Nouveau mot de passe <span class="text-red-500">*</span>
            </label>
            <div class="relative">
              <input
                v-model="newPassword"
                :type="showNewPassword ? 'text' : 'password'"
                placeholder="Au moins 6 caractères"
                class="block w-full px-3 py-2 pr-10 border border-slate-350 rounded-none text-sm bg-white focus:outline-none focus:border-green-600"
                required
              />
              <button
                type="button"
                @click="showNewPassword = !showNewPassword"
                class="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-650 cursor-pointer"
              >
                <UIcon :name="showNewPassword ? 'i-lucide-eye-off' : 'i-lucide-eye'" class="w-4 h-4" />
              </button>
            </div>
            <div class="flex items-center gap-3 mt-1 text-[11px] text-slate-500">
              <span :class="newPassword.length >= 6 ? 'text-emerald-700 font-bold' : ''">
                ✓ Au moins 6 caractères
              </span>
              <span v-if="newPassword === 'Payohada@123'" class="text-red-600 font-bold">
                ✕ Doit être différent de Payohada@123
              </span>
            </div>
          </div>

          <!-- Confirmer le nouveau mot de passe -->
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-650 mb-1">
              Confirmer le nouveau mot de passe <span class="text-red-500">*</span>
            </label>
            <div class="relative">
              <input
                v-model="confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                placeholder="Ressaisissez le nouveau mot de passe"
                class="block w-full px-3 py-2 pr-10 border border-slate-350 rounded-none text-sm bg-white focus:outline-none focus:border-green-600"
                required
              />
              <button
                type="button"
                @click="showConfirmPassword = !showConfirmPassword"
                class="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-650 cursor-pointer"
              >
                <UIcon :name="showConfirmPassword ? 'i-lucide-eye-off' : 'i-lucide-eye'" class="w-4 h-4" />
              </button>
            </div>
            <p
              v-if="confirmPassword && newPassword !== confirmPassword"
              class="text-[11px] text-red-600 font-semibold mt-1"
            >
              Les mots de passe ne correspondent pas.
            </p>
          </div>

          <!-- Footer Actions -->
          <div class="flex items-center justify-between pt-4 border-t border-slate-200 mt-6">
            <button
              type="button"
              @click="dismissModal"
              class="px-4 py-2 border-2 border-slate-200 text-xs font-bold rounded-none hover:bg-slate-100 text-slate-700 transition-colors uppercase tracking-wider cursor-pointer"
            >
              {{ isDefault ? "Modifier plus tard" : "Annuler" }}
            </button>
            <button
              type="submit"
              :disabled="submitting || authLoading"
              class="px-4 py-2 text-xs font-bold bg-green-600 hover:bg-green-700 text-white rounded-none shadow-flat transition-colors uppercase tracking-wider cursor-pointer flex items-center gap-1.5 disabled:opacity-50"
            >
              <UIcon v-if="submitting || authLoading" name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
              {{ submitting ? "Enregistrement..." : "Enregistrer" }}
            </button>
          </div>
        </form>
      </div>
    </template>
  </UModal>
</template>
