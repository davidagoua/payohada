export const useChangePasswordModal = () => {
  const isOpen = useState<boolean>('change-password-modal-open', () => false)
  const dismissedInSession = useState<boolean>('change-password-dismissed-session', () => false)

  const openModal = () => {
    isOpen.value = true
  }

  const closeModal = () => {
    isOpen.value = false
  }

  const dismissModal = () => {
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

    // Vérifier si le mot de passe est celui par défaut
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
    openModal,
    closeModal,
    dismissModal,
    checkAndSuggest
  }
}
