<script setup>
/**
 * Coque des écrans d'authentification (connexion, inscription,
 * mot de passe oublié, réinitialisation).
 *
 * Elle porte la charte de la marque : un panneau latéral à l'encre navy
 * (#01173a), la deuxième couleur du logo, et le vert réservé aux points
 * d'action et de confiance. Le contenu est fourni par la page via le slot.
 */
const annee = new Date().getFullYear()

const garanties = [
  { icone: 'i-lucide-scale', libelle: 'Conformité OHADA' },
  { icone: 'i-lucide-shield-check', libelle: 'Données chiffrées' },
  { icone: 'i-lucide-folder-git-2', libelle: 'Multi-entreprises' }
]
</script>

<template>
  <div class="min-h-screen bg-slate-50 font-sans lg:grid lg:grid-cols-[minmax(0,44%)_1fr]">
    <!-- Panneau de marque : encre navy -->
    <aside class="relative hidden lg:flex flex-col justify-between overflow-hidden bg-navy-950 p-12 text-white">
      <!-- Trame technique discrète -->
      <div
        class="absolute inset-0 pointer-events-none"
        style="background-image: linear-gradient(to right, rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.04) 1px, transparent 1px); background-size: 52px 52px;"
      />
      <!-- Halos : vert de la marque et navy plus clair -->
      <div class="absolute -top-32 -right-24 w-[420px] h-[420px] rounded-full bg-green-600/10 blur-3xl pointer-events-none" />
      <div class="absolute -bottom-40 -left-20 w-[380px] h-[380px] rounded-full bg-navy-600/25 blur-3xl pointer-events-none" />

      <NuxtLink to="/" class="relative z-10 flex items-center" aria-label="payohada — accueil">
        <img
          src="/payohada-logo-light.png"
          alt="payohada"
          class="h-9 w-auto object-contain"
        >
      </NuxtLink>

      <div class="relative z-10 space-y-7">
        <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-green-400">
          La paie conforme pour l'Afrique de l'Ouest
        </p>
        <h2 class="text-3xl font-bold leading-snug text-white">
          La rigueur de la paie,<br>
          <span class="text-green-400">la simplicité en plus.</span>
        </h2>
        <p class="max-w-sm text-sm leading-relaxed text-slate-300">
          Dossiers d'entreprises, établissements, salariés, contrats et
          bulletins : un seul registre, conforme et traçable.
        </p>

        <ul class="space-y-3 pt-2">
          <li
            v-for="g in garanties"
            :key="g.libelle"
            class="flex items-center gap-3 text-sm text-slate-200"
          >
            <span class="flex h-7 w-7 items-center justify-center border border-green-500/30 bg-green-500/10 text-green-400">
              <UIcon :name="g.icone" class="h-4 w-4" />
            </span>
            {{ g.libelle }}
          </li>
        </ul>
      </div>

      <p class="relative z-10 text-[11px] text-slate-400">
        © {{ annee }} payohada — ERP Paie Solution
      </p>
    </aside>

    <!-- Colonne de contenu -->
    <div class="flex min-h-screen flex-col">
      <!-- Bandeau de marque sur mobile -->
      <div class="flex items-center justify-between bg-navy-950 px-5 py-4 lg:hidden">
        <NuxtLink to="/" class="flex items-center" aria-label="payohada — accueil">
          <img
            src="/payohada-logo-light.png"
            alt="payohada"
            class="h-7 w-auto object-contain"
          >
        </NuxtLink>
        <span class="text-[10px] font-bold uppercase tracking-widest text-green-400">
          Paie OHADA
        </span>
      </div>

      <main class="flex flex-1 flex-col justify-center px-4 py-10 sm:px-6 lg:px-12">
        <div class="mx-auto w-full max-w-xl">
          <slot />
        </div>
      </main>

      <footer class="hidden lg:block px-12 pb-6 text-[11px] text-slate-500">
        © {{ annee }} payohada — La paie conforme pour l'Afrique de l'Ouest
      </footer>
    </div>
  </div>
</template>
