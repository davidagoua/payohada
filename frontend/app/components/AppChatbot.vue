<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted } from 'vue'

const {
  isOpen,
  isLoading,
  messages,
  initChat,
  toggleChat,
  closeChat,
  clearHistory,
  sendMessage
} = useChatbot()

// Contexte actif de l'application (Dossier / Établissement courant)
const currentDossier = useState<Record<string, unknown> | null>('current-dossier', () => null)
const currentEtablissement = useState<Record<string, unknown> | null>('current-etablissement', () => null)

const inputText = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const copiedId = ref<string | null>(null)

const suggestedPrompts = [
  'Comment calculer le salaire brut ?',
  'Comment fonctionne le mode Net vers Brut ?',
  'Quels sont les plafonds et taux de cotisation CNPS ?',
  'Comment établir un Solde de Tout Compte (STC) ?'
]

onMounted(() => {
  initChat()
})

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// Défilement automatique lors de nouveaux messages ou du streaming
watch(
  () => messages.value.map(m => m.content).join(''),
  () => {
    scrollToBottom()
  }
)

watch(isOpen, (newVal) => {
  if (newVal) {
    scrollToBottom()
    nextTick(() => {
      textareaRef.value?.focus()
    })
  }
})

const handleSend = () => {
  if (!inputText.value.trim() || isLoading.value) return
  const text = inputText.value
  inputText.value = ''
  sendMessage(text)
  scrollToBottom()
}

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

const selectPrompt = (prompt: string) => {
  sendMessage(prompt)
}

const copyMessage = async (id: string, text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    copiedId.value = id
    setTimeout(() => {
      if (copiedId.value === id) copiedId.value = null
    }, 2000)
  } catch (err) {
    console.error('Erreur copie:', err)
  }
}

const renderMarkdown = (content: string): string => {
  if (!content) return ''
  // 1. Échapper le HTML brut pour la sécurité
  let html = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // 2. Blocs de code
  html = html.replace(/```([\s\S]*?)```/g, '<pre class="bg-slate-900 text-slate-100 p-2.5 rounded-md text-xs font-mono overflow-x-auto my-2"><code>$1</code></pre>')

  // 3. Code en ligne
  html = html.replace(/`([^`]+)`/g, '<code class="bg-slate-100 text-emerald-800 px-1 py-0.5 rounded text-xs font-mono font-semibold">$1</code>')

  // 4. Titres
  html = html.replace(/^### (.*$)/gim, '<h4 class="text-xs font-bold uppercase tracking-wider text-slate-800 mt-2.5 mb-1">$1</h4>')
  html = html.replace(/^## (.*$)/gim, '<h3 class="text-sm font-bold text-slate-900 mt-3 mb-1">$1</h3>')
  html = html.replace(/^# (.*$)/gim, '<h2 class="text-base font-bold text-slate-900 mt-3 mb-1.5">$1</h2>')

  // 5. Gras et Italique
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-bold text-slate-900">$1</strong>')
  html = html.replace(/\*([^*]+)\*/g, '<em class="italic text-slate-800">$1</em>')

  // 6. Lignes horizontales
  html = html.replace(/^---$/gim, '<hr class="my-2.5 border-slate-200" />')

  // 7. Puces de liste
  html = html.replace(/^\s*[-*]\s+(.*)$/gim, '<li class="ml-4 list-disc text-slate-700 my-0.5">$1</li>')

  // 8. Listes numérotées
  html = html.replace(/^\s*(\d+)\.\s+(.*)$/gim, '<li class="ml-4 list-decimal text-slate-700 my-0.5"><span class="font-semibold text-slate-800">$1.</span> $2</li>')

  // 9. Retours à la ligne
  html = html.replace(/\n\n/g, '<div class="h-2"></div>')
  html = html.replace(/\n/g, '<br />')

  return html
}

const activeContextLabel = computed(() => {
  if (currentEtablissement.value?.raison_sociale) {
    return `${currentEtablissement.value.raison_sociale}`
  }
  if (currentDossier.value?.nom_dossier) {
    return `${currentDossier.value.nom_dossier}`
  }
  return null
})
</script>

<template>
  <!-- Conteneur global du Chatbot (exclu à l'impression) -->
  <aside
    aria-label="Assistant IA PayOHADA"
    class="fixed bottom-5 right-5 z-50 flex flex-col items-end print:hidden select-none"
  >
    <!-- Fenêtre de dialogue du Chatbot -->
    <Transition
      enter-active-class="transition duration-250 ease-out"
      enter-from-class="opacity-0 translate-y-4 scale-95"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 translate-y-4 scale-95"
    >
      <div
        v-if="isOpen"
        class="w-[92vw] sm:w-[420px] md:w-[460px] h-[580px] max-h-[82vh] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden mb-3.5 select-text"
      >
        <!-- En-tête du Chatbot -->
        <header class="bg-gradient-to-r from-emerald-700 via-green-700 to-emerald-800 text-white p-3.5 flex items-center justify-between shadow-sm select-none">
          <div class="flex items-center space-x-2.5">
            <div class="relative flex-shrink-0">
              <div class="w-9 h-9 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 flex items-center justify-center p-1 shadow-inner">
                <img
                  src="/payohada-icon.png"
                  alt="PayOHADA"
                  class="w-6 h-6 object-contain"
                >
              </div>
              <span class="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-400 border-2 border-emerald-800 rounded-full animate-pulse" />
            </div>
            <div class="flex flex-col">
              <div class="flex items-center space-x-1.5">
                <h3 class="font-bold text-sm tracking-wide leading-tight">
                  Assistant PayOHADA
                </h3>
                <span class="text-[10px] font-semibold uppercase bg-white/20 px-1.5 py-0.5 rounded-full text-white/90">IA</span>
              </div>
              <span class="text-[11px] text-emerald-100/90 leading-tight">Expert Paie & Droit Social OHADA</span>
            </div>
          </div>

          <!-- Boutons d'action de l'en-tête -->
          <div class="flex items-center space-x-1">
            <!-- Bouton nouveau chat / vider l'historique -->
            <button
              type="button"
              title="Nouvelle conversation"
              class="p-1.5 rounded-lg text-emerald-100 hover:text-white hover:bg-white/15 transition-colors cursor-pointer"
              @click="clearHistory"
            >
              <UIcon
                name="i-lucide-trash-2"
                class="w-4 h-4"
              />
            </button>

            <!-- Bouton fermer -->
            <button
              type="button"
              title="Fermer le chat"
              class="p-1.5 rounded-lg text-emerald-100 hover:text-white hover:bg-white/15 transition-colors cursor-pointer"
              @click="closeChat"
            >
              <UIcon
                name="i-lucide-x"
                class="w-5 h-5"
              />
            </button>
          </div>
        </header>

        <!-- Bandeau de contexte actif (si dossier/établissement sélectionné) -->
        <div
          v-if="activeContextLabel"
          class="bg-emerald-50/80 border-b border-emerald-150 px-3.5 py-1.5 flex items-center justify-between text-[11px] text-emerald-900 select-none"
        >
          <div class="flex items-center space-x-1.5 truncate">
            <UIcon
              name="i-lucide-building-2"
              class="w-3.5 h-3.5 text-emerald-600 flex-shrink-0"
            />
            <span class="truncate font-medium">Dossier : <strong class="font-bold text-emerald-950">{{ activeContextLabel }}</strong></span>
          </div>
          <span class="text-[10px] bg-emerald-200/60 text-emerald-800 font-semibold px-1.5 py-0.2 rounded">Actif</span>
        </div>

        <!-- Corps des messages -->
        <div
          ref="messagesContainer"
          class="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/50"
        >
          <!-- Suggestions rapides au début si 1 seul message -->
          <div
            v-if="messages.length <= 1"
            class="mb-2"
          >
            <div class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center space-x-1">
              <UIcon
                name="i-lucide-sparkles"
                class="w-3 h-3 text-emerald-600"
              />
              <span>Questions fréquentes</span>
            </div>
            <div class="grid grid-cols-1 gap-1.5">
              <button
                v-for="(prompt, idx) in suggestedPrompts"
                :key="idx"
                type="button"
                class="text-left text-xs text-slate-700 bg-white hover:bg-emerald-50/80 hover:text-emerald-800 border border-slate-200/90 hover:border-emerald-300 rounded-xl px-3 py-2 transition-all duration-150 shadow-xs flex items-center justify-between group cursor-pointer"
                @click="selectPrompt(prompt)"
              >
                <span>{{ prompt }}</span>
                <UIcon
                  name="i-lucide-corner-down-left"
                  class="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-600 opacity-0 group-hover:opacity-100 transition-opacity"
                />
              </button>
            </div>
          </div>

          <!-- Liste des messages -->
          <div
            v-for="msg in messages"
            :key="msg.id"
            class="flex flex-col"
            :class="msg.role === 'user' ? 'items-end' : 'items-start'"
          >
            <div
              class="max-w-[88%] sm:max-w-[84%] rounded-2xl p-3.5 text-xs shadow-xs leading-relaxed"
              :class="[
                msg.role === 'user'
                  ? 'bg-gradient-to-br from-emerald-600 to-green-700 text-white rounded-br-xs font-medium'
                  : 'bg-white border border-slate-200 text-slate-800 rounded-bl-xs'
              ]"
            >
              <!-- En-tête d'un message assistant -->
              <div
                v-if="msg.role === 'assistant'"
                class="flex items-center justify-between pb-1.5 mb-1.5 border-b border-slate-100 text-[10px] text-slate-400"
              >
                <div class="flex items-center space-x-1.5 font-semibold text-emerald-700">
                  <UIcon
                    name="i-lucide-bot"
                    class="w-3.5 h-3.5"
                  />
                  <span>Assistant PayOHADA</span>
                </div>
                <!-- Bouton copier la réponse -->
                <button
                  type="button"
                  title="Copier la réponse"
                  class="p-1 hover:text-slate-700 transition-colors flex items-center space-x-1"
                  @click="copyMessage(msg.id, msg.content)"
                >
                  <UIcon
                    :name="copiedId === msg.id ? 'i-lucide-check' : 'i-lucide-copy'"
                    class="w-3 h-3"
                  />
                  <span
                    v-if="copiedId === msg.id"
                    class="text-[9px] text-emerald-600 font-bold"
                  >Copié</span>
                </button>
              </div>

              <!-- Contenu du message -->
              <!-- eslint-disable-next-line vue/no-v-html -->
              <div
                v-if="msg.role === 'assistant'"
                class="prose prose-xs max-w-none text-slate-800 space-y-1"
                v-html="renderMarkdown(msg.content)"
              />
              <div
                v-else
                class="whitespace-pre-wrap"
              >
                {{ msg.content }}
              </div>

              <!-- Indicateur de streaming ou de chargement -->
              <div
                v-if="msg.status === 'streaming' && !msg.content"
                class="flex items-center space-x-1.5 py-1 text-emerald-600"
              >
                <span
                  class="w-2 h-2 rounded-full bg-emerald-600 animate-bounce"
                  style="animation-delay: 0ms"
                />
                <span
                  class="w-2 h-2 rounded-full bg-emerald-600 animate-bounce"
                  style="animation-delay: 150ms"
                />
                <span
                  class="w-2 h-2 rounded-full bg-emerald-600 animate-bounce"
                  style="animation-delay: 300ms"
                />
                <span class="text-[11px] font-medium text-slate-500 ml-1">Réflexion en cours...</span>
              </div>
            </div>

            <!-- Horodatage discret -->
            <span class="text-[9px] text-slate-400 mt-1 px-1">
              {{ new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}
            </span>
          </div>
        </div>

        <!-- Zone de saisie du message -->
        <footer class="p-3 bg-white border-t border-slate-200">
          <form
            class="relative flex items-center bg-slate-100 rounded-xl border border-slate-200 focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500/20 transition-all shadow-inner"
            @submit.prevent="handleSend"
          >
            <textarea
              ref="textareaRef"
              v-model="inputText"
              rows="1"
              placeholder="Posez une question sur la paie, un salarié, un calcul..."
              class="w-full text-xs bg-transparent py-2.5 pl-3 pr-10 resize-none outline-none text-slate-800 placeholder-slate-400 leading-normal max-h-28"
              :disabled="isLoading"
              @keydown="handleKeydown"
            />
            <button
              type="submit"
              :disabled="!inputText.trim() || isLoading"
              title="Envoyer le message"
              class="absolute right-1.5 p-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 disabled:hover:bg-emerald-600 text-white transition-all cursor-pointer disabled:cursor-not-allowed shadow-xs"
            >
              <UIcon
                :name="isLoading ? 'i-lucide-loader-2' : 'i-lucide-send'"
                class="w-4 h-4"
                :class="{ 'animate-spin': isLoading }"
              />
            </button>
          </form>

          <p class="text-[10px] text-center text-slate-400 mt-2 select-none">
            Assistant spécialisé PayOHADA • Conforme réglementation OHADA / UEMOA
          </p>
        </footer>
      </div>
    </Transition>

    <!-- Bouton flottant déclencheur du Chatbot -->
    <button
      type="button"
      class="group relative flex items-center space-x-2.5 bg-gradient-to-r from-emerald-600 to-green-700 hover:from-emerald-700 hover:to-green-800 text-white font-medium px-4 py-3 rounded-full shadow-lg hover:shadow-emerald-500/25 transition-all duration-200 hover:scale-105 active:scale-95 border border-emerald-500/40 cursor-pointer"
      :aria-expanded="isOpen"
      @click="toggleChat"
    >
      <!-- Logo / Icône avec effet pulsation -->
      <div class="relative w-6 h-6 flex items-center justify-center">
        <img
          src="/payohada-icon.png"
          alt="PayOHADA"
          class="w-5 h-5 object-contain"
        >
        <span class="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-300 rounded-full border-2 border-emerald-700 animate-ping" />
        <span class="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-300 rounded-full border-2 border-emerald-700" />
      </div>

      <span class="text-xs font-bold tracking-wide">Assistant Paie</span>

      <UIcon
        :name="isOpen ? 'i-lucide-x' : 'i-lucide-sparkles'"
        class="w-4 h-4 text-emerald-200 group-hover:rotate-12 transition-transform"
      />
    </button>
  </aside>
</template>

<style scoped>
/* Personnalisation fine de la scrollbar pour le chat */
::-webkit-scrollbar {
  width: 5px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 9999px;
}
::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
