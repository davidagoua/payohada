<script setup>
/**
 * Tableau de bord de l'administrateur plateforme : usage du SaaS par cabinet.
 *
 * L'API ne renvoie que des effectifs agrégés (sociétés, salariés, bulletins) :
 * aucune donnée de paie ni aucun nom de société ou de salarié.
 */
const { get } = useApi()

const donnees = ref(null)
const chargement = ref(true)
const erreur = ref('')

const charger = async () => {
  chargement.value = true
  erreur.value = ''
  try {
    donnees.value = await get('/platform/tableau-de-bord')
  } catch (e) {
    console.error('Tableau de bord plateforme indisponible :', e)
    erreur.value = e?.data?.detail || 'Le tableau de bord n\'a pas pu être chargé.'
  } finally {
    chargement.value = false
  }
}

const nombre = valeur => new Intl.NumberFormat('fr-FR').format(valeur || 0)

const LIBELLES_ROLES = {
  cabinet: 'Administrateurs de cabinet',
  gestionnaire_paie: 'Gestionnaires de paie',
  client: 'Comptes entreprise',
  salarie: 'Comptes salarié'
}

const roles = computed(() => {
  const parRole = donnees.value?.utilisateurs_par_role || {}
  return Object.keys(LIBELLES_ROLES).map(role => ({
    role,
    libelle: LIBELLES_ROLES[role],
    total: parRole[role] || 0
  }))
})

const indicateurs = computed(() => {
  const d = donnees.value
  if (!d) return []
  return [
    {
      libelle: 'Cabinets actifs',
      valeur: nombre(d.cabinets.actifs),
      detail: d.cabinets.suspendus
        ? `${nombre(d.cabinets.suspendus)} suspendu(s) sur ${nombre(d.cabinets.total)}`
        : `sur ${nombre(d.cabinets.total)} cabinet(s)`,
      icone: 'i-lucide-building-2'
    },
    {
      libelle: 'Nouveaux cabinets',
      valeur: nombre(d.cabinets.nouveaux_30_jours),
      detail: 'sur les 30 derniers jours',
      icone: 'i-lucide-user-plus'
    },
    {
      libelle: 'Sociétés gérées',
      valeur: nombre(d.societes),
      detail: 'tous cabinets confondus',
      icone: 'i-lucide-briefcase'
    },
    {
      libelle: 'Salariés actifs',
      valeur: nombre(d.salaries_actifs),
      detail: 'base de facturation',
      icone: 'i-lucide-users'
    },
    {
      libelle: 'Bulletins du mois',
      valeur: nombre(d.bulletins_mois_courant),
      detail: getPeriodLabel(new Date().getMonth() + 1, new Date().getFullYear()),
      icone: 'i-lucide-file-text'
    }
  ]
})

// Histogramme d'activité : une seule série, donc ni légende ni couleur
// catégorielle ; le détail (validés) passe par l'infobulle.
const activite = computed(() => donnees.value?.activite || [])
const maxActivite = computed(() => Math.max(1, ...activite.value.map(a => a.bulletins)))
const moisSurvole = ref(null)
// « juin » et « juil. » : une troncature à trois lettres les confondrait.
const moisCourt = ({ mois, annee }) =>
  new Intl.DateTimeFormat('fr-FR', { month: 'short' }).format(new Date(annee, mois - 1, 1))

const formatDate = (valeur) => {
  if (!valeur) return '—'
  return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
    .format(new Date(valeur))
}

onMounted(charger)
</script>

<template>
  <div class="space-y-6">
    <div
      v-if="chargement"
      class="flex items-center justify-center py-16 text-sm text-slate-500 gap-3"
    >
      <UIcon
        name="i-lucide-loader-2"
        class="w-5 h-5 animate-spin text-green-600"
      />
      Chargement des indicateurs…
    </div>

    <div
      v-else-if="erreur"
      class="bg-white border border-red-200 rounded-xl p-6 text-sm text-red-700 flex items-center justify-between gap-4"
    >
      <span>{{ erreur }}</span>
      <button
        class="px-3 py-1.5 text-xs font-bold uppercase tracking-wider border border-red-300 hover:bg-red-50"
        @click="charger"
      >
        Réessayer
      </button>
    </div>

    <template v-else-if="donnees">
      <!-- Indicateurs clés -->
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div
          v-for="indicateur in indicateurs"
          :key="indicateur.libelle"
          class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm"
        >
          <div class="flex items-center justify-between">
            <p class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              {{ indicateur.libelle }}
            </p>
            <UIcon
              :name="indicateur.icone"
              class="w-4 h-4 text-slate-400"
            />
          </div>
          <p class="mt-2 text-2xl font-bold text-navy-900 tabular-nums">
            {{ indicateur.valeur }}
          </p>
          <p class="text-xs text-slate-500 mt-0.5">
            {{ indicateur.detail }}
          </p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Activité : bulletins calculés sur 6 mois -->
        <div class="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider">
            Bulletins calculés sur la plateforme
          </h2>
          <p class="text-xs text-slate-500">
            Six derniers mois, tous cabinets confondus.
          </p>

          <div
            class="mt-6 relative h-48 flex items-end gap-3 border-b border-slate-300"
            role="img"
            :aria-label="`Bulletins calculés par mois : ${activite.map(a => `${getPeriodLabel(a.mois, a.annee)} ${a.bulletins}`).join(', ')}`"
          >
            <div
              v-for="(periode, index) in activite"
              :key="`${periode.annee}-${periode.mois}`"
              class="relative flex-1 h-full flex items-end justify-center cursor-default"
              @mouseenter="moisSurvole = index"
              @mouseleave="moisSurvole = null"
            >
              <div
                class="w-full max-w-12 rounded-t-[4px] transition-colors"
                :class="moisSurvole === index ? 'bg-green-700' : 'bg-green-600'"
                :style="{ height: `${(periode.bulletins / maxActivite) * 100}%`, minHeight: periode.bulletins ? '2px' : '0' }"
              />
              <div
                v-if="moisSurvole === index"
                class="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 z-10 whitespace-nowrap bg-navy-900 text-white text-xs rounded-md px-3 py-2 shadow-lg pointer-events-none"
              >
                <p class="font-bold">
                  {{ getPeriodLabel(periode.mois, periode.annee) }}
                </p>
                <p class="tabular-nums">
                  {{ nombre(periode.bulletins) }} bulletin(s)
                </p>
                <p class="tabular-nums text-slate-300">
                  dont {{ nombre(periode.bulletins_valides) }} validé(s)
                </p>
              </div>
            </div>
          </div>
          <div class="flex gap-3 mt-2">
            <span
              v-for="periode in activite"
              :key="`l-${periode.annee}-${periode.mois}`"
              class="flex-1 text-center text-[11px] text-slate-500"
            >
              {{ moisCourt(periode) }}
              <span class="block font-semibold text-slate-700 tabular-nums">{{ nombre(periode.bulletins) }}</span>
            </span>
          </div>
        </div>

        <!-- Comptes par rôle -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider">
            Comptes utilisateurs
          </h2>
          <p class="text-xs text-slate-500">
            Hors administrateurs plateforme.
          </p>
          <ul class="mt-4 divide-y divide-slate-100">
            <li
              v-for="ligne in roles"
              :key="ligne.role"
              class="py-2.5 flex items-center justify-between text-sm"
            >
              <span class="text-slate-600">{{ ligne.libelle }}</span>
              <span class="font-bold text-navy-900 tabular-nums">{{ nombre(ligne.total) }}</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- Usage par cabinet -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div class="px-6 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 class="text-sm font-bold text-navy-900 uppercase tracking-wider">
              Usage par cabinet
            </h2>
            <p class="text-xs text-slate-500">
              Effectifs seulement : le contenu des dossiers reste privé à chaque cabinet.
            </p>
          </div>
          <NuxtLink
            to="/admin/cabinets"
            class="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-bold uppercase tracking-wider bg-navy-900 text-white hover:bg-navy-800"
          >
            <UIcon
              name="i-lucide-settings-2"
              class="w-4 h-4"
            />
            Gérer les cabinets
          </NuxtLink>
        </div>

        <div
          v-if="donnees.usage_cabinets.length === 0"
          class="px-6 py-10 text-center text-sm text-slate-500"
        >
          Aucun cabinet pour le moment.
        </div>
        <div
          v-else
          class="overflow-x-auto"
        >
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <thead class="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th class="px-6 py-3 text-left">
                  Cabinet
                </th>
                <th class="px-6 py-3 text-left">
                  Statut
                </th>
                <th class="px-6 py-3 text-right">
                  Utilisateurs
                </th>
                <th class="px-6 py-3 text-right">
                  Sociétés
                </th>
                <th class="px-6 py-3 text-right">
                  Salariés actifs
                </th>
                <th class="px-6 py-3 text-right">
                  Bulletins du mois
                </th>
                <th class="px-6 py-3 text-right">
                  Dernière activité
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr
                v-for="cabinet in donnees.usage_cabinets"
                :key="cabinet.id"
                class="hover:bg-slate-50"
              >
                <td class="px-6 py-3 font-semibold text-navy-900">
                  {{ cabinet.cabinet_nom || `Cabinet n° ${cabinet.id}` }}
                </td>
                <td class="px-6 py-3">
                  <span
                    class="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border"
                    :class="cabinet.suspendu
                      ? 'bg-red-50 text-red-700 border-red-200'
                      : 'bg-green-50 text-green-700 border-green-200'"
                  >
                    <UIcon
                      :name="cabinet.suspendu ? 'i-lucide-pause-circle' : 'i-lucide-check-circle'"
                      class="w-3 h-3"
                    />
                    {{ cabinet.suspendu ? 'Suspendu' : 'Actif' }}
                  </span>
                </td>
                <td class="px-6 py-3 text-right tabular-nums">
                  {{ nombre(cabinet.utilisateurs) }}
                </td>
                <td class="px-6 py-3 text-right tabular-nums">
                  {{ nombre(cabinet.societes) }}
                </td>
                <td class="px-6 py-3 text-right tabular-nums font-semibold">
                  {{ nombre(cabinet.salaries_actifs) }}
                </td>
                <td class="px-6 py-3 text-right tabular-nums">
                  {{ nombre(cabinet.bulletins_mois_courant) }}
                </td>
                <td class="px-6 py-3 text-right text-slate-500">
                  {{ formatDate(cabinet.derniere_activite) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
