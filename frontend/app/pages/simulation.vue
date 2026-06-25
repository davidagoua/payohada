<script setup>
const { post } = useApi()
const toast = useToast()

definePageMeta({
  layout: 'default'
})

// Input State
const typeSalaire = ref('Mensuel')
const salaireMensuel = ref(500000)
const salaireHoraire = ref(3000)
const horaireStandard = ref(173.33)
const tauxAt = ref(3.0)

const uniteTemps = ref('Heures')
const sursalaire = ref(0)
const expatrie = ref(false)
const indemniteTransport = ref(0)
const dotationTelephonique = ref(0)
const acompte = ref(0)

// Lists of variables
const absenceTypes = [
  'ABSENCES NON AUTORISEE',
  'CONGES ANNUELLES',
  'CONGES DE MATERNITE',
  'CONVENANCES PERSONNELLES',
  'DECES',
  'MALADIES'
]

const absences = ref([
  { id: Date.now() + 1, code: 'MALADIES', nbr_heures: 4, nbr_jours: 0 }
])
const heuresSup = ref([
  { id: Date.now() + 2, code: 'HS_25', nombre: 8 }
])
const primes = ref([
  { id: Date.now() + 3, code: 'RENDEMENT', libelle: 'Prime de rendement', montant: 50000 }
])

// Result state
const result = ref(null)
const loading = ref(false)

// Formatting helper
const formatXOF = (value) => {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'XOF',
    maximumFractionDigits: 0
  }).format(value).replace('XOF', 'FCFA')
}

// Format percent
const formatPercent = (value) => {
  if (!value) return '0 %'
  return `${value.toFixed(2)} %`
}

// Add/Remove Helpers
const addAbsence = () => {
  absences.value.push({ id: Date.now(), code: 'CONGES ANNUELLES', nbr_heures: 0, nbr_jours: 0 })
}
const removeAbsence = (id) => {
  absences.value = absences.value.filter(a => a.id !== id)
}

const addHeureSup = () => {
  heuresSup.value.push({ id: Date.now(), code: 'HS_25', nombre: 0 })
}
const removeHeureSup = (id) => {
  heuresSup.value = heuresSup.value.filter(h => h.id !== id)
}

const addPrime = () => {
  primes.value.push({ id: Date.now(), code: 'ANCIENNETE', libelle: 'Prime d\'ancienneté', montant: 0 })
}
const removePrime = (id) => {
  primes.value = primes.value.filter(p => p.id !== id)
}

// Calculate simulation
const handleSimulate = async () => {
  loading.value = true
  result.value = null
  try {
    const payload = {
      salaire_mensuel: typeSalaire.value === 'Mensuel' ? Number(salaireMensuel.value) : 0,
      salaire_horaire: typeSalaire.value === 'Horaire' ? Number(salaireHoraire.value) : 0,
      type_salaire: typeSalaire.value,
      horaire_mensuel_standard: Number(horaireStandard.value),
      taux_at: Number(tauxAt.value),
      unite_temps: uniteTemps.value,
      sursalaire: Number(sursalaire.value) || 0,
      expatrie: expatrie.value,
      indemnite_transport: Number(indemniteTransport.value) || 0,
      dotation_telephonique: Number(dotationTelephonique.value) || 0,
      acompte: Number(acompte.value) || 0,
      absences: absences.value.map(a => ({
        code: a.code || 'ABS',
        nbr_heures: Number(a.nbr_heures) || 0,
        nbr_jours: Number(a.nbr_jours) || 0
      })),
      heures_sup: heuresSup.value.map(h => ({
        code: h.code,
        nombre: Number(h.nombre) || 0
      })),
      primes: primes.value.map(p => ({
        code: p.code || 'PRIME',
        libelle: p.libelle || 'Autre prime',
        montant: Number(p.montant) || 0
      }))
    }

    const res = await post('/bulletins/simuler', payload)
    if (res) {
      result.value = res
      toast.add({
        title: 'Simulation calculée',
        description: 'Le bulletin de salaire fictif a été généré avec succès.',
        color: 'success'
      })
    }
  } catch (e) {
    console.error(e)
    toast.add({
      title: 'Erreur',
      description: 'Une erreur s\'est produite lors de la simulation de paie.',
      color: 'danger'
    })
  } finally {
    loading.value = false
  }
}

// Auto-run on mount
onMounted(() => {
  handleSimulate()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header Object page -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 bg-green-50 text-green-700 rounded-lg flex items-center justify-center font-bold text-xl border border-green-200">
          <UIcon name="i-lucide-calculator" class="w-6 h-6" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-900 leading-tight">Simulateur de Bulletin de Paie</h1>
          <p class="text-xs text-slate-500 mt-1">Calculez instantanément les salaires, retenues et cotisations CNPS de la zone UEMOA.</p>
        </div>
      </div>
      
      <button 
        @click="handleSimulate"
        :disabled="loading"
        class="w-full md:w-auto px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
      >
        <UIcon v-if="loading" name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
        <UIcon v-else name="i-lucide-play" class="w-4 h-4" />
        <span>Lancer le calcul</span>
      </button>
    </div>

    <!-- Main Simulator Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      <!-- Left Column: Form Parameters (5 cols) -->
      <div class="lg:col-span-5 space-y-6">
        
        <!-- Base Salary Config -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <h2 class="text-sm font-bold text-slate-950 uppercase tracking-wider border-b border-slate-100 pb-2">Rémunération de base</h2>
          
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Base de calcul</label>
              <select v-model="typeSalaire" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500">
                <option value="Mensuel">Salaire Mensuel</option>
                <option value="Horaire">Taux Horaire</option>
              </select>
            </div>
            
            <div v-if="typeSalaire === 'Mensuel'">
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Salaire Mensuel Brut</label>
              <input 
                v-model="salaireMensuel" 
                type="number" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-green-500" 
              />
            </div>
            <div v-else>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Taux Horaire Brut</label>
              <input 
                v-model="salaireHoraire" 
                type="number" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-green-500" 
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Heures standard (Mois)</label>
              <input 
                v-model="horaireStandard" 
                type="number" 
                step="0.01" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-green-500" 
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Taux AT Patronal (%)</label>
              <input 
                v-model="tauxAt" 
                type="number" 
                step="0.1" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-green-500" 
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4 border-t border-slate-100 pt-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Unité de Temps</label>
              <select v-model="uniteTemps" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500">
                <option value="Heures">Heures</option>
                <option value="Jours">Jours</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Sursalaire (FCFA)</label>
              <input 
                v-model="sursalaire" 
                type="number" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-green-500" 
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Régime Expatrié</label>
              <select v-model="expatrie" class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white select focus:outline-none focus:ring-2 focus:ring-green-500">
                <option :value="false">Non (Local)</option>
                <option :value="true">Oui (Expatrié)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Acompte déduit (FCFA)</label>
              <input 
                v-model="acompte" 
                type="number" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-green-500" 
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Transport (FCFA)</label>
              <input 
                v-model="indemniteTransport" 
                type="number" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-green-500" 
              />
            </div>
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500">Dotation Tél. (FCFA)</label>
              <input 
                v-model="dotationTelephonique" 
                type="number" 
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-green-500" 
              />
            </div>
          </div>
        </div>

        <!-- Absences Config -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <div class="flex justify-between items-center border-b border-slate-100 pb-2">
            <h2 class="text-sm font-bold text-slate-950 uppercase tracking-wider">Absences à déduire</h2>
            <button 
              @click="addAbsence" 
              class="text-xs text-green-600 hover:text-green-700 font-bold flex items-center gap-1"
            >
              <UIcon name="i-lucide-plus" class="w-3.5 h-3.5" /> Ajouter
            </button>
          </div>

          <div v-if="absences.length === 0" class="text-xs text-slate-450 italic py-2">
            Aucune absence renseignée. Le salarié a travaillé la totalité du mois.
          </div>
          <div v-else class="space-y-3">
            <div v-for="(abs, index) in absences" :key="abs.id" class="flex gap-2 items-center bg-slate-50 p-3 rounded-lg border border-slate-200">
              <div class="flex-grow grid grid-cols-3 gap-2">
                <div>
                  <label class="text-[9px] uppercase tracking-wider font-semibold text-slate-400">Motif</label>
                  <select v-model="abs.code" class="block w-full px-2 py-1 border border-slate-300 rounded text-xs bg-white select focus:outline-none focus:ring-2 focus:ring-green-500">
                    <option v-for="type in absenceTypes" :key="type" :value="type">
                      {{ type }}
                    </option>
                  </select>
                </div>
                <div>
                  <label class="text-[9px] uppercase tracking-wider font-semibold text-slate-400">Nbr Heures</label>
                  <input v-model="abs.nbr_heures" type="number" class="block w-full px-2 py-1 border border-slate-300 rounded text-xs font-mono" />
                </div>
                <div>
                  <label class="text-[9px] uppercase tracking-wider font-semibold text-slate-400">Nbr Jours</label>
                  <input v-model="abs.nbr_jours" type="number" class="block w-full px-2 py-1 border border-slate-300 rounded text-xs font-mono" />
                </div>
              </div>
              <button 
                @click="removeAbsence(abs.id)" 
                class="mt-4 p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded"
              >
                <UIcon name="i-lucide-x" class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <!-- Overtime (Heures Sup) Config -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <div class="flex justify-between items-center border-b border-slate-100 pb-2">
            <h2 class="text-sm font-bold text-slate-950 uppercase tracking-wider">Heures Supplémentaires</h2>
            <button 
              @click="addHeureSup" 
              class="text-xs text-green-600 hover:text-green-700 font-bold flex items-center gap-1"
            >
              <UIcon name="i-lucide-plus" class="w-3.5 h-3.5" /> Ajouter
            </button>
          </div>

          <div v-if="heuresSup.length === 0" class="text-xs text-slate-450 italic py-2">
            Aucune heure supplémentaire à majorer.
          </div>
          <div v-else class="space-y-3">
            <div v-for="(hs, index) in heuresSup" :key="hs.id" class="flex gap-2 items-center bg-slate-50 p-3 rounded-lg border border-slate-200">
              <div class="flex-grow grid grid-cols-2 gap-2">
                <div>
                  <label class="text-[9px] uppercase tracking-wider font-semibold text-slate-400">Type Majoré</label>
                  <select v-model="hs.code" class="block w-full px-2 py-1 border border-slate-300 rounded text-xs bg-white">
                    <option value="HS_25">HS Majorées à 25 %</option>
                    <option value="HS_50">HS Majorées à 50 %</option>
                  </select>
                </div>
                <div>
                  <label class="text-[9px] uppercase tracking-wider font-semibold text-slate-400">Nombre d'heures</label>
                  <input v-model="hs.nombre" type="number" class="block w-full px-2 py-1 border border-slate-300 rounded text-xs font-mono" />
                </div>
              </div>
              <button 
                @click="removeHeureSup(hs.id)" 
                class="mt-4 p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded"
              >
                <UIcon name="i-lucide-x" class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <!-- Primes Config -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <div class="flex justify-between items-center border-b border-slate-100 pb-2">
            <h2 class="text-sm font-bold text-slate-950 uppercase tracking-wider">Primes & Indemnités</h2>
            <button 
              @click="addPrime" 
              class="text-xs text-green-600 hover:text-green-700 font-bold flex items-center gap-1"
            >
              <UIcon name="i-lucide-plus" class="w-3.5 h-3.5" /> Ajouter
            </button>
          </div>

          <div v-if="primes.length === 0" class="text-xs text-slate-450 italic py-2">
            Aucune prime ou indemnité ce mois-ci.
          </div>
          <div v-else class="space-y-3">
            <div v-for="(p, index) in primes" :key="p.id" class="flex gap-2 items-center bg-slate-50 p-3 rounded-lg border border-slate-200">
              <div class="flex-grow grid grid-cols-3 gap-2">
                <div>
                  <label class="text-[9px] uppercase tracking-wider font-semibold text-slate-400">Code</label>
                  <input v-model="p.code" type="text" class="block w-full px-2 py-1 border border-slate-300 rounded text-xs font-mono" />
                </div>
                <div>
                  <label class="text-[9px] uppercase tracking-wider font-semibold text-slate-400">Libellé</label>
                  <input v-model="p.libelle" type="text" class="block w-full px-2 py-1 border border-slate-300 rounded text-xs" />
                </div>
                <div>
                  <label class="text-[9px] uppercase tracking-wider font-semibold text-slate-400">Montant (FCFA)</label>
                  <input v-model="p.montant" type="number" class="block w-full px-2 py-1 border border-slate-300 rounded text-xs font-mono" />
                </div>
              </div>
              <button 
                @click="removePrime(p.id)" 
                class="mt-4 p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded"
              >
                <UIcon name="i-lucide-x" class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

      </div>

      <!-- Right Column: Simulated Payslip Preview (7 cols) -->
      <div class="lg:col-span-7">
        
        <div v-if="loading" class="bg-white border border-slate-200 rounded-xl p-16 text-center space-y-4 shadow-sm flex flex-col items-center justify-center">
          <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
          <span class="text-sm font-semibold text-slate-650">Calcul en cours et génération du bulletin...</span>
        </div>

        <div v-else-if="result" class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden divide-y divide-slate-150">
          
          <!-- Payslip Header -->
          <div class="p-6 bg-slate-50 flex justify-between items-start">
            <div class="space-y-1">
              <span class="text-[10px] font-bold uppercase tracking-widest text-green-700 bg-green-50 px-2 py-0.5 border border-green-200 rounded">
                Zone UEMOA
              </span>
              <h3 class="text-lg font-extrabold text-slate-900">BULLETIN DE PAIE SIMULÉ</h3>
              <p class="text-xs text-slate-500">Calculateur d'exercice local</p>
            </div>
            
            <div class="text-right text-xs text-slate-500 font-mono space-y-1">
              <p>Type de calcul : Simulation</p>
              <p>Devise : Franc CFA (XOF)</p>
            </div>
          </div>

          <!-- Employee Card Dummy Details -->
          <div class="p-4 grid grid-cols-2 gap-4 text-xs bg-slate-50/50">
            <div class="space-y-1">
              <p class="font-bold text-slate-400 uppercase tracking-wide text-[9px]">Employeur Fictif</p>
              <p class="font-bold text-slate-700">ENTREPRISE DE SIMULATION</p>
              <p class="text-slate-500">Taux AT : {{ tauxAt }} %</p>
            </div>
            <div class="space-y-1">
              <p class="font-bold text-slate-400 uppercase tracking-wide text-[9px]">Salarié Fictif</p>
              <p class="font-bold text-slate-700">COLLABORATEUR DÉMO</p>
              <p class="text-slate-500">Temps partiel/plein : {{ horaireStandard }} h/mois</p>
            </div>
          </div>

          <!-- Payslip Lines Table -->
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-slate-200 text-xs">
              <thead class="bg-slate-100 text-slate-600 font-bold text-[10px] uppercase tracking-wider">
                <tr>
                  <th scope="col" class="px-4 py-2.5 text-left w-1/3">Rubrique / Libellé</th>
                  <th scope="col" class="px-3 py-2.5 text-right">Base / Nombre</th>
                  <th scope="col" class="px-3 py-2.5 text-right bg-slate-50/50">Part Salariale (%)</th>
                  <th scope="col" class="px-3 py-2.5 text-right bg-slate-50/50">Montant Salarial</th>
                  <th scope="col" class="px-3 py-2.5 text-right bg-slate-100/50">Part Patronale (%)</th>
                  <th scope="col" class="px-3 py-2.5 text-right bg-slate-100/50">Montant Patronal</th>
                  <th scope="col" class="px-4 py-2.5 text-right">Gains / Retenues</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-150 font-mono text-slate-700">
                <tr v-for="line in result.lignes" :key="line.code" class="hover:bg-slate-50">
                  <td class="px-4 py-2 text-left font-sans font-medium text-slate-900">{{ line.libelle }}</td>
                  <td class="px-3 py-2 text-right text-slate-500">{{ line.base_s || line.base_p || '-' }}</td>
                  
                  <!-- Salariale -->
                  <td class="px-3 py-2 text-right bg-slate-50/20 text-slate-400">
                    {{ line.taux_s > 0 ? formatPercent(line.taux_s) : '-' }}
                  </td>
                  <td class="px-3 py-2 text-right bg-slate-50/20" :class="line.montant_cs > 0 ? 'text-slate-900 font-semibold' : 'text-slate-400'">
                    {{ line.montant_cs > 0 ? formatXOF(line.montant_cs) : '-' }}
                  </td>
                  
                  <!-- Patronale -->
                  <td class="px-3 py-2 text-right bg-slate-100/10 text-slate-400">
                    {{ line.taux_p > 0 ? formatPercent(line.taux_p) : '-' }}
                  </td>
                  <td class="px-3 py-2 text-right bg-slate-100/10" :class="line.montant_cp > 0 ? 'text-slate-900 font-semibold' : 'text-slate-400'">
                    {{ line.montant_cp > 0 ? formatXOF(line.montant_cp) : '-' }}
                  </td>

                  <!-- Primes / Retenues / Gains Bruts -->
                  <td class="px-4 py-2 text-right font-semibold text-slate-900" :class="{ 'text-red-600': line.montant_pr < 0 }">
                    {{ line.montant_pr !== 0 ? formatXOF(line.montant_pr) : '-' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Totals Breakdown & Net Pay Card -->
          <div class="p-6 bg-slate-50 space-y-4">
            
            <!-- Imposable and Brut summaries -->
            <div class="grid grid-cols-2 gap-4 text-xs text-slate-650">
              <div class="flex justify-between border-b border-slate-200 pb-1">
                <span>Total Salaire Brut :</span>
                <span class="font-bold font-mono text-slate-900">{{ formatXOF(result.salaire_brut) }}</span>
              </div>
              <div class="flex justify-between border-b border-slate-200 pb-1">
                <span>Net Imposable :</span>
                <span class="font-bold font-mono text-slate-900">{{ formatXOF(result.net_imposable) }}</span>
              </div>
              <div class="flex justify-between border-b border-slate-200 pb-1">
                <span>Total Cotisations Salariales :</span>
                <span class="font-bold font-mono text-slate-900">{{ formatXOF(result.cotisations_salariales) }}</span>
              </div>
              <div class="flex justify-between border-b border-slate-200 pb-1">
                <span>Total Cotisations Patronales :</span>
                <span class="font-bold font-mono text-slate-900">{{ formatXOF(result.cotisations_patronales) }}</span>
              </div>
            </div>

            <!-- Sleek highlight card for net pay -->
            <div class="bg-green-600 rounded-xl p-4 text-white flex justify-between items-center shadow">
              <div class="space-y-0.5">
                <p class="text-[10px] font-bold uppercase tracking-widest text-green-150">Net à Payer Fictif</p>
                <p class="text-2xl font-extrabold tracking-tight font-mono">
                  {{ formatXOF(result.net_a_payer) }}
                </p>
              </div>
              
              <div class="text-right text-[11px] text-green-100 max-w-[180px] leading-tight">
                Calculé selon le régime de la zone UEMOA.
              </div>
            </div>

            <!-- Cumul Table -->
            <div v-if="result.cumuls" class="space-y-3 pt-4 border-t border-slate-200">
              <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider">Cumuls de Paie</h4>
              <div class="overflow-x-auto rounded-lg border border-slate-200">
                <table class="min-w-full divide-y divide-slate-200 text-[10px] text-left">
                  <thead class="bg-slate-100 font-bold text-slate-650">
                    <tr>
                      <th scope="col" class="px-3 py-2">Période</th>
                      <th scope="col" class="px-3 py-2 text-right">Heures/Jours</th>
                      <th scope="col" class="px-3 py-2 text-right">Brut (FCFA)</th>
                      <th scope="col" class="px-3 py-2 text-right">Brut CNPS</th>
                      <th scope="col" class="px-3 py-2 text-right">Retraite</th>
                      <th scope="col" class="px-3 py-2 text-right">IBS</th>
                      <th scope="col" class="px-3 py-2 text-right">CMU</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-150 font-mono text-slate-700 bg-white">
                    <tr class="hover:bg-slate-50">
                      <td class="px-3 py-2 font-sans font-bold text-slate-900">Mensuel</td>
                      <td class="px-3 py-2 text-right">{{ result.cumuls.mensuel.heures_jours }}</td>
                      <td class="px-3 py-2 text-right">{{ formatXOF(result.cumuls.mensuel.salaire_brut) }}</td>
                      <td class="px-3 py-2 text-right">{{ formatXOF(result.cumuls.mensuel.brut_cnps) }}</td>
                      <td class="px-3 py-2 text-right">{{ formatXOF(result.cumuls.mensuel.cot_retraite) }}</td>
                      <td class="px-3 py-2 text-right">{{ formatXOF(result.cumuls.mensuel.ibs) }}</td>
                      <td class="px-3 py-2 text-right">{{ formatXOF(result.cumuls.mensuel.cmu) }}</td>
                    </tr>
                    <tr class="hover:bg-slate-50 bg-slate-50/30">
                      <td class="px-3 py-2 font-sans font-bold text-slate-900">Annuel</td>
                      <td class="px-3 py-2 text-right">{{ result.cumuls.annuel.heures_jours }}</td>
                      <td class="px-3 py-2 text-right">{{ formatXOF(result.cumuls.annuel.salaire_brut) }}</td>
                      <td class="px-3 py-2 text-right">{{ formatXOF(result.cumuls.annuel.brut_cnps) }}</td>
                      <td class="px-3 py-2 text-right">{{ formatXOF(result.cumuls.annuel.cot_retraite) }}</td>
                      <td class="px-3 py-2 text-right">{{ formatXOF(result.cumuls.annuel.ibs) }}</td>
                      <td class="px-3 py-2 text-right">{{ formatXOF(result.cumuls.annuel.cmu) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Vacation Tracker -->
            <div class="pt-4 border-t border-slate-200 grid grid-cols-2 gap-4 text-[10px] text-slate-650">
              <div class="bg-white border border-slate-200 rounded-lg p-3 space-y-1 shadow-sm">
                <span class="block font-bold text-slate-900 uppercase tracking-wider">Congés Payés</span>
                <div class="flex justify-between font-mono">
                  <span>Acquis :</span>
                  <span class="font-bold text-slate-900">2.50 jours / mois</span>
                </div>
                <div class="flex justify-between font-mono">
                  <span>Pris :</span>
                  <span class="font-bold text-slate-900">0.00</span>
                </div>
                <div class="flex justify-between font-mono">
                  <span>Solde :</span>
                  <span class="font-bold text-green-700">2.50</span>
                </div>
              </div>
              <div class="bg-white border border-slate-200 rounded-lg p-3 space-y-1 shadow-sm">
                <span class="block font-bold text-slate-900 uppercase tracking-wider">Logement & Congés</span>
                <div class="flex justify-between font-mono">
                  <span>Brut Congés :</span>
                  <span class="font-bold text-slate-900">{{ formatXOF(result.salaire_brut) }}</span>
                </div>
                <div class="flex justify-between font-mono">
                  <span>Réduction RICF :</span>
                  <span class="font-bold text-green-700">-11 000 FCFA</span>
                </div>
              </div>
            </div>

          </div>

        </div>

        <div v-else class="bg-white border border-slate-200 rounded-xl p-16 text-center text-slate-500 italic text-sm shadow-sm">
          Veuillez renseigner les paramètres à gauche puis cliquer sur "Lancer le calcul" pour générer la simulation du bulletin.
        </div>

      </div>

    </div>
  </div>
</template>
