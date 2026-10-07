export const useChangePasswordModal = () => {
  const isOpen = useState<boolean>('change-password-modal-open', () => false)
  const dismissedInSession = useState<boolean>('change-password-dismissed-session', () => false)
  // Vrai lorsque l'utilisateur doit définir son propre mot de passe.
  const mustChangePassword = useState<boolean>('change-password-required', () => false)

  const openModal = () => {
    isOpen.value = true
  }

  const closeModal = () => {
    isOpen.value = false
  }

  const dismissModal = () => {
    // Tant que le mot de passe provisoire n'a pas été remplacé, la
    // fermeture du modal n'est pas autorisée.
    if (mustChangePassword.value) return
    isOpen.value = false
    dismissedInSession.value = true
    if (typeof window !== 'undefined') {
      try {
        sessionStorage.setItem('dismissed-password-modal', 'true')
      } catch (e) {
        console.warn('Unable to write to sessionStorage:', e)
      }
    }
  }

  const checkAndSuggest = (currentUser: any) => {
    if (!currentUser) return
    const isClientOrSalarie = currentUser.role === 'client' || currentUser.role === 'salarie' || !!currentUser.salarie_id
    if (!isClientOrSalarie) return

    mustChangePassword.value = !!currentUser.is_default_password

    // Vérifier si le mot de passe provisoire est encore actif
    if (currentUser.is_default_password) {
      if (typeof window !== 'undefined') {
        try {
          const alreadyDismissed = sessionStorage.getItem('dismissed-password-modal') === 'true'
          if (!alreadyDismissed && !dismissedInSession.value) {
            isOpen.value = true
          }
        } catch (e) {
          if (!dismissedInSession.value) {
            isOpen.value = true
          }
        }
      } else {
        isOpen.value = true
      }
    }
  }

  return {
    isOpen,
    dismissedInSession,
    mustChangePassword,
    openModal,
    closeModal,
    dismissModal,
    checkAndSuggest
  }
}
