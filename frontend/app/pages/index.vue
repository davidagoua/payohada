<script setup>
definePageMeta({
  layout: false
})
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-900 font-sans selection:bg-green-150 selection:text-green-900 flex flex-col">
    <!-- Top Green Stripe Accent -->
    <div class="h-1 bg-green-600 w-full" />

    <!-- Navigation Header -->
    <header class="sticky top-0 bg-white/80 backdrop-blur-md border-b border-slate-200 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <div class="w-8 h-8 rounded-lg bg-green-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
            P
          </div>
          <span class="text-xl font-bold tracking-tight text-slate-900">payohada</span>
        </div>
        <div class="flex items-center space-x-4">
          <NuxtLink to="/login" class="px-4 py-2 text-sm font-semibold text-slate-700 hover:text-green-600 transition-colors duration-150">
            Connexion
          </NuxtLink>
          <NuxtLink to="/login?register=true" class="px-4 py-2 text-sm font-semibold text-white bg-green-600 hover:bg-green-700 rounded-lg shadow-sm transition-colors duration-150">
            S'inscrire
          </NuxtLink>
        </div>
      </div>
    </header>

    <!-- Hero Section -->
    <section class="relative py-20 overflow-hidden bg-gradient-to-b from-white to-slate-50 flex-grow flex items-center">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        
        <!-- Hero Left Content (Text & Actions) -->
        <div class="space-y-8 animate-fade-in-up">
          <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-green-50 border border-green-200 text-green-700 text-xs font-semibold">
            <span class="w-1.5 h-1.5 rounded-full bg-green-600 animate-ping"></span>
            <span>Logiciel de Paie SAP-Style</span>
          </div>

          <h1 class="text-4xl sm:text-5xl font-extrabold text-slate-900 leading-tight">
            Gérez vos salariés et vos paies avec la rigueur de
            <span class="text-transparent bg-clip-text bg-gradient-to-r from-green-600 to-emerald-700">SAP</span>
          </h1>

          <p class="text-lg text-slate-600 leading-relaxed max-w-lg">
            Payohada offre une structure robuste inspirée des standards d'entreprise SAP, adaptée pour gérer vos dossiers clients, vos établissements administratifs, vos salariés et leurs contrats de travail en toute simplicité.
          </p>

          <div class="flex flex-col sm:flex-row gap-4">
            <NuxtLink to="/login" class="px-8 py-3.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center space-x-2">
              <span>Accéder à l'application</span>
              <UIcon name="i-lucide-arrow-right" class="w-5 h-5" />
            </NuxtLink>
            <a href="#features" class="px-8 py-3.5 bg-white border border-slate-200 text-slate-700 font-semibold rounded-lg hover:bg-slate-50 transition-colors duration-200 text-center">
              Découvrir les fonctionnalités
            </a>
          </div>

          <div class="flex items-center space-x-6 text-slate-500 text-sm">
            <div class="flex items-center space-x-2">
              <UIcon name="i-lucide-check-circle" class="w-5 h-5 text-green-600" />
              <span>Supabase Auth</span>
            </div>
            <div class="flex items-center space-x-2">
              <UIcon name="i-lucide-check-circle" class="w-5 h-5 text-green-600" />
              <span>Structure SAP Fiori</span>
            </div>
          </div>
        </div>

        <!-- Hero Right Content (Visual mockup representation) -->
        <div class="relative hidden lg:block animate-fade-in">
          <!-- Main mock frame -->
          <div class="relative bg-white border border-slate-200 rounded-xl shadow-2xl p-6 overflow-hidden">
            <!-- Header bar mock -->
            <div class="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
              <div class="flex items-center space-x-2">
                <div class="w-3 h-3 rounded-full bg-red-400"></div>
                <div class="w-3 h-3 rounded-full bg-yellow-400"></div>
                <div class="w-3 h-3 rounded-full bg-green-400"></div>
              </div>
              <div class="text-xs text-slate-400 bg-slate-50 px-8 py-1 rounded border border-slate-100">
                app.payohada.cloud/dossiers
              </div>
            </div>
            <!-- Mock App Grid -->
            <div class="space-y-4">
              <div class="flex justify-between items-center bg-slate-50 p-3 rounded-lg border border-slate-100">
                <div class="flex items-center space-x-3">
                  <div class="w-10 h-10 rounded bg-green-100 flex items-center justify-center text-green-800 font-bold text-sm">
                    E1
                  </div>
                  <div>
                    <p class="text-sm font-semibold text-slate-800">Etablissement Paris Nord</p>
                    <p class="text-xs text-slate-500 font-mono">SIRET: 123 456 789 00012</p>
                  </div>
                </div>
                <span class="text-xs px-2 py-0.5 rounded bg-green-50 border border-green-200 text-green-700 font-medium">
                  Actif
                </span>
              </div>
              <!-- Employees mini list -->
              <div class="space-y-2">
                <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Salariés & Contrats</div>
                <div class="grid grid-cols-2 gap-2">
                  <div class="bg-white border border-slate-150 p-2.5 rounded shadow-sm">
                    <p class="text-xs font-bold text-slate-800">Jean Dupont</p>
                    <p class="text-[10px] text-green-600 font-semibold">CDI • 35h/sem</p>
                  </div>
                  <div class="bg-white border border-slate-150 p-2.5 rounded shadow-sm">
                    <p class="text-xs font-bold text-slate-800">Sophie Martin</p>
                    <p class="text-[10px] text-green-600 font-semibold">CDD • Temps partiel</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </section>

    <!-- Features Section -->
    <section id="features" class="py-20 bg-white border-t border-slate-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div class="text-center max-w-2xl mx-auto mb-16">
          <h2 class="text-3xl font-bold text-slate-900 sm:text-4xl">
            L'excellence opérationnelle de SAP, simplifiée
          </h2>
          <p class="mt-4 text-slate-600">
            Payohada structure les données administratives clés de votre entreprise selon des normes standardisées et transparentes.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          <!-- Card 1 -->
          <div class="p-6 bg-slate-50 border border-slate-200 rounded-xl hover:border-green-500 hover:shadow-md transition-all duration-200 group">
            <div class="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center text-green-600 mb-4 group-hover:bg-green-600 group-hover:text-white transition-colors">
              <UIcon name="i-lucide-folder" class="w-6 h-6" />
            </div>
            <h3 class="font-bold text-slate-900 text-lg mb-2">Dossiers d'Entreprises</h3>
            <p class="text-sm text-slate-600">
              Gérez les informations d'identification, de contact et les liaisons NetEntreprise de vos clients et entités.
            </p>
          </div>

          <!-- Card 2 -->
          <div class="p-6 bg-slate-50 border border-slate-200 rounded-xl hover:border-green-500 hover:shadow-md transition-all duration-200 group">
            <div class="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center text-green-600 mb-4 group-hover:bg-green-600 group-hover:text-white transition-colors">
              <UIcon name="i-lucide-building" class="w-6 h-6" />
            </div>
            <h3 class="font-bold text-slate-900 text-lg mb-2">Établissements</h3>
            <p class="text-sm text-slate-600">
              Associez des adresses de facturation, des coordonnées bancaires IBAN/BIC et les caisses de cotisations sociales (URSSAF, Retraite).
            </p>
          </div>

          <!-- Card 3 -->
          <div class="p-6 bg-slate-50 border border-slate-200 rounded-xl hover:border-green-500 hover:shadow-md transition-all duration-200 group">
            <div class="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center text-green-600 mb-4 group-hover:bg-green-600 group-hover:text-white transition-colors">
              <UIcon name="i-lucide-users" class="w-6 h-6" />
            </div>
            <h3 class="font-bold text-slate-900 text-lg mb-2">Fiches Salariés</h3>
            <p class="text-sm text-slate-600">
              Suivi individuel complet : identité civile, immatriculation de sécurité sociale (NIR), et informations de versement de paie.
            </p>
          </div>

          <!-- Card 4 -->
          <div class="p-6 bg-slate-50 border border-slate-200 rounded-xl hover:border-green-500 hover:shadow-md transition-all duration-200 group">
            <div class="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center text-green-600 mb-4 group-hover:bg-green-600 group-hover:text-white transition-colors">
              <UIcon name="i-lucide-file-text" class="w-6 h-6" />
            </div>
            <h3 class="font-bold text-slate-900 text-lg mb-2">Contrats de Travail</h3>
            <p class="text-sm text-slate-600">
              Définissez la CCN (convention collective), le salaire brut (mensuel ou horaire), le type de contrat (CDI, CDD) et la gestion des temps partiels.
            </p>
          </div>
        </div>

      </div>
    </section>

    <!-- App CTA Section -->
    <section class="py-16 bg-green-600 text-white">
      <div class="max-w-4xl mx-auto px-4 text-center space-y-6">
        <h2 class="text-3xl font-extrabold">Prêt à simplifier vos processus RH ?</h2>
        <p class="text-green-100 max-w-xl mx-auto">
          Inscrivez-vous dès maintenant et découvrez la rigueur et la clarté du style SAP pour le pilotage de votre paie.
        </p>
        <div class="flex justify-center space-x-4 pt-2">
          <NuxtLink to="/login?register=true" class="px-6 py-3 bg-white text-green-700 font-bold rounded-lg hover:bg-slate-100 transition-colors">
            Créer un compte gratuitement
          </NuxtLink>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="bg-slate-900 text-slate-400 py-10 mt-auto">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center">
        <div class="flex items-center space-x-2 text-white">
          <div class="w-6 h-6 rounded bg-green-600 flex items-center justify-center font-bold text-xs text-white">P</div>
          <span class="font-bold text-lg">payohada</span>
        </div>
        <p class="mt-4 md:mt-0 text-sm">
          © {{ new Date().getFullYear() }} payohada. Tous droits réservés.
        </p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.animate-fade-in-up {
  animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.animate-fade-in {
  animation: fadeIn 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
</style>
