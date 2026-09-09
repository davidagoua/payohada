export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  status?: 'sending' | 'streaming' | 'complete' | 'error'
}

const STORAGE_KEY_MESSAGES = 'payohada_chatbot_messages'
const STORAGE_KEY_SESSION = 'payohada_chatbot_session_id'

const DEFAULT_WELCOME_MESSAGE: ChatMessage = {
  id: 'welcome-0',
  role: 'assistant',
  content: `Bonjour ! Je suis l'assistant IA officiel de **PayOHADA**.\n\nJe suis là pour vous accompagner dans la gestion de vos dossiers, salariés, contrats, éléments variables de paie, solde de tout compte et la compréhension de vos bulletins conformes aux normes OHADA / UEMOA.\n\nComment puis-je vous aider aujourd'hui ?`,
  timestamp: new Date().toISOString(),
  status: 'complete'
}

export const useChatbot = () => {
  const config = useRuntimeConfig()
  const webhookUrl = computed(() => config.public.n8nChatWebhook as string || 'https://n8n-m4ymolk1iglny3uabdpli4sa.songon.shop/webhook/4edd13ea-6fd0-44c3-b5f8-49bac1c51902/chat')

  const isOpen = useState<boolean>('chatbot_is_open', () => false)
  const isMinimized = useState<boolean>('chatbot_is_minimized', () => false)
  const isLoading = useState<boolean>('chatbot_is_loading', () => false)
  const messages = useState<ChatMessage[]>('chatbot_messages', () => [DEFAULT_WELCOME_MESSAGE])
  const sessionId = useState<string>('chatbot_session_id', () => '')

  // Initialise session et historique depuis le localStorage côté client
  const initChat = () => {
    if (import.meta.server) return

    // Session ID
    let savedSession = localStorage.getItem(STORAGE_KEY_SESSION)
    if (!savedSession) {
      savedSession = `payohada_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
      localStorage.setItem(STORAGE_KEY_SESSION, savedSession)
    }
    sessionId.value = savedSession

    // Messages
    const savedMessages = localStorage.getItem(STORAGE_KEY_MESSAGES)
    if (savedMessages) {
      try {
        const parsed = JSON.parse(savedMessages)
        if (Array.isArray(parsed) && parsed.length > 0) {
          messages.value = parsed
        }
      } catch (e) {
        console.error('Erreur chargement messages chat:', e)
      }
    }
  }

  const saveMessages = () => {
    if (import.meta.server) return
    try {
      localStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(messages.value))
    } catch (e) {
      console.error('Erreur sauvegarde messages chat:', e)
    }
  }

  const toggleChat = () => {
    isOpen.value = !isOpen.value
    if (isOpen.value) {
      isMinimized.value = false
    }
  }

  const openChat = (initialPrompt?: string) => {
    isOpen.value = true
    isMinimized.value = false
    if (initialPrompt) {
      sendMessage(initialPrompt)
    }
  }

  const closeChat = () => {
    isOpen.value = false
  }

  const clearHistory = () => {
    if (import.meta.server) return
    const newSession = `payohada_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
    sessionId.value = newSession
    localStorage.setItem(STORAGE_KEY_SESSION, newSession)
    messages.value = [{
      ...DEFAULT_WELCOME_MESSAGE,
      timestamp: new Date().toISOString()
    }]
    saveMessages()
  }

  const sendMessage = async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || isLoading.value) return

    // Ajouter le message utilisateur
    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
      status: 'complete'
    }
    messages.value.push(userMsg)

    // Préparer le message assistant en attente
    const botMsgId = `bot_${Date.now()}`
    const botMsg: ChatMessage = {
      id: botMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      status: 'streaming'
    }
    messages.value.push(botMsg)
    isLoading.value = true

    try {
      const response = await fetch(webhookUrl.value, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action: 'sendMessage',
          chatInput: trimmed,
          sessionId: sessionId.value
        })
      })

      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status} ${response.statusText}`)
      }

      if (!response.body) {
        // Fallback si pas de streaming body
        const rawText = await response.text()
        const target = messages.value.find(m => m.id === botMsgId)
        if (target) {
          target.content = rawText
          target.status = 'complete'
        }
        saveMessages()
        return
      }

      // Lecture du flux en streaming (NDJSON de n8n)
      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Garde la ligne incomplète en cours

        for (const line of lines) {
          const cleanLine = line.trim()
          if (!cleanLine) continue

          try {
            const data = JSON.parse(cleanLine)
            const target = messages.value.find(m => m.id === botMsgId)
            if (!target) continue

            if (data.type === 'item' && data.content) {
              target.content += data.content
            } else if (data.type === 'end') {
              target.status = 'complete'
            } else if (data.output) {
              target.content += data.output
            } else if (data.text) {
              target.content += data.text
            }
          } catch {
            // Si la ligne n'est pas du JSON, on l'ajoute si pertinent
            const target = messages.value.find(m => m.id === botMsgId)
            if (target && cleanLine && !cleanLine.startsWith('{')) {
              target.content += cleanLine
            }
          }
        }
      }

      // Traiter le reliquat du buffer
      if (buffer.trim()) {
        try {
          const data = JSON.parse(buffer.trim())
          const target = messages.value.find(m => m.id === botMsgId)
          if (target && data.type === 'item' && data.content) {
            target.content += data.content
          }
        } catch {
          // ignorer
        }
      }

      const target = messages.value.find(m => m.id === botMsgId)
      if (target) {
        if (!target.content) {
          target.content = 'Désolé, aucune réponse n\'a été retournée par le serveur.'
        }
        target.status = 'complete'
      }
    } catch (err: unknown) {
      console.error('Erreur chatbot n8n:', err)
      const target = messages.value.find(m => m.id === botMsgId)
      if (target) {
        const errorMsg = err instanceof Error ? err.message : 'Erreur réseau'
        target.content = `Une erreur s'est produite lors de la communication avec l'assistant (${errorMsg}). Veuillez vérifier que le workflow n8n est actif.`
        target.status = 'error'
      }
    } finally {
      isLoading.value = false
      saveMessages()
    }
  }

  return {
    isOpen,
    isMinimized,
    isLoading,
    messages,
    sessionId,
    initChat,
    toggleChat,
    openChat,
    closeChat,
    clearHistory,
    sendMessage
  }
}
