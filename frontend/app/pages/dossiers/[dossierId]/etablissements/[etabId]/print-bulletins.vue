<script setup>
const route = useRoute()
const router = useRouter()
const { get } = useApi()

const dossierId = route.params.dossierId
const etabId = route.params.etabId

const ids = route.query.ids ? String(route.query.ids).split(',') : []

const etablissement = ref(null)
const bulletinsData = ref([])
const loading = ref(true)

const loadAllData = async () => {
  if (ids.length === 0) {
    loading.value = false
    return
  }
  try {
    etablissement.value = await get(`/etablissements/${etabId}`)
    const promises = ids.map(async (bId) => {
      try {
        const b = await get(`/bulletins/${bId}`)
        const contrat = await get(`/contrats/${b.contrat_id}`)
        const salarie = await get(`/salaries/${contrat.salarie_id}`)
        return { bulletin: b, contrat, salarie }
      } catch (e) {
        console.error(`Error loading bulletin #${bId}:`, e)
        return null
      }
    })
    const results = await Promise.all(promises)
    bulletinsData.value = results.filter(Boolean)
  } catch (e) {
    console.error("Error loading print data:", e)
  } finally {
    loading.value = false
  }
}

// Helpers
const formatXOF = (value) => {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'XOF',
    maximumFractionDigits: 0
  }).format(value).replace('XOF', 'FCFA')
}

const formatPercent = (value) => {
  if (!value) return '-'
  return `${value.toFixed(2)} %`
}

const getPeriodLabel = (mois, annee) => {
  const months = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
  ]
  return `${months[mois - 1]} ${annee}`
}

const getGrossLines = (bulletin) => {
  if (!bulletin || !bulletin.lignes) return []
  const cotisCodes = ['IBS', 'RICF', 'CNPS_RETRAITE', 'CMU_S', 'CN', 'TA', 'TFC', 'CNPS_PF', 'CNPS_AT', 'CNPS_MATERNITE', 'CMU_P']
  return bulletin.lignes.filter(l => {
    const c = l.code.toUpperCase()
    const isCotis = cotisCodes.includes(c)
    const isNet = ['TRANSPORT', 'TELEPHONE', 'ACOMPTE', 'FRAIS_PROFESSIONNELS', 'AUTRE_RETENUE'].includes(c) || c.startsWith('RET_')
    return !isCotis && !isNet
  })
}

const getCotisationsLines = (bulletin) => {
  if (!bulletin || !bulletin.lignes) return []
  return bulletin.lignes.filter(l => {
    const c = l.code.toUpperCase()
    return ['IBS', 'RICF', 'CNPS_RETRAITE', 'CMU_S', 'CN', 'TA', 'TFC', 'CNPS_PF', 'CNPS_AT', 'CNPS_MATERNITE', 'CMU_P'].includes(c)
  })
}

const getNetLines = (bulletin) => {
  if (!bulletin || !bulletin.lignes) return []
  return bulletin.lignes.filter(l => {
    const c = l.code.toUpperCase()
    return ['TRANSPORT', 'TELEPHONE', 'ACOMPTE', 'FRAIS_PROFESSIONNELS', 'AUTRE_RETENUE'].includes(c) || c.startsWith('RET_')
  })
}

const triggerPrint = () => {
  window.print()
}

onMounted(() => {
  loadAllData()
})
</script>

<template>
  <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4 no-print">
    <UIcon name="i-lucide-loader-2" class="w-8 h-8 animate-spin text-green-600" />
    <span class="text-sm text-slate-500 font-medium">Préparation de l'impression...</span>
  </div>

  <div v-else-if="bulletinsData.length === 0" class="max-w-md mx-auto py-20 text-center space-y-4 no-print bg-white p-8 border-2 border-slate-200 shadow-flat">
    <div class="w-12 h-12 bg-slate-100 text-slate-400 rounded-none flex items-center justify-center mx-auto">
      <UIcon name="i-lucide-alert-circle" class="w-6 h-6" />
    </div>
    <h3 class="font-bold text-slate-900 text-lg">Aucun bulletin sélectionné</h3>
    <p class="text-xs text-slate-500">
      Veuillez retourner sur la liste des bulletins pour en sélectionner.
    </p>
    <NuxtLink 
      :to="`/dossiers/${dossierId}/etablissements/${etabId}?tab=bulletins`"
      class="inline-block px-4 py-2 border-2 border-slate-200 text-xs font-bold uppercase tracking-wider hover:bg-slate-50 text-slate-700 transition-all rounded-none"
    >
      Retourner aux bulletins
    </NuxtLink>
  </div>

  <div v-else class="space-y-6 print-container">
    <!-- Top toolbar hidden during printing -->
    <div class="bg-white border-2 border-slate-200 p-4 shadow-flat flex flex-col sm:flex-row justify-between items-center gap-4 no-print border-t-4 border-t-green-600">
      <div class="flex items-center space-x-3">
        <NuxtLink 
          :to="`/dossiers/${dossierId}/etablissements/${etabId}?tab=bulletins`"
          class="p-2 border-2 border-slate-200 rounded-none hover:bg-slate-50 text-slate-700 transition-colors"
        >
          <UIcon name="i-lucide-arrow-left" class="w-4 h-4" />
        </NuxtLink>
        <div>
          <h1 class="text-lg font-bold text-slate-900 leading-tight uppercase">
            Impression en Masse
          </h1>
          <p class="text-xs text-slate-500 uppercase font-semibold">
            {{ bulletinsData.length }} bulletin(s) sélectionné(s) prêt(s) à être imprimé(s)
          </p>
        </div>
      </div>

      <div>
        <button 
          @click="triggerPrint"
          class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-bold rounded-none shadow-flat transition-colors flex items-center gap-1.5 uppercase tracking-wider cursor-pointer shadow-flat-hover shadow-flat-active"
        >
          <UIcon name="i-lucide-printer" class="w-4 h-4" />
          Lancer l'impression
        </button>
      </div>
    </div>

    <!-- Printable Payslips -->
    <div class="space-y-8 print:space-y-0">
      <div 
        v-for="item in bulletinsData" 
        :key="item.bulletin.id"
        class="bg-white border-2 border-slate-200 shadow-flat rounded-none p-4 mx-auto print-payslip text-slate-800 border-t-4 border-t-green-600 print-payslip-page print:border-none print:shadow-none print:p-0 max-w-[850px]"
      >
        
        <!-- Top Columns: Employer vs Employee -->
        <div class="grid grid-cols-2 gap-8 border-b-2 border-slate-200 pb-6 text-xs">
          
          <!-- Left Side: Employer Info -->
          <div class="space-y-2">
            <div class="space-y-1">
              <h2 class="text-sm font-black text-slate-900 uppercase">{{ etablissement?.raison_sociale }}</h2>
              <p class="text-slate-650 leading-relaxed font-medium">
                {{ etablissement?.adresse?.adresse_postale }}<br />
                {{ etablissement?.adresse?.adresse_postale2 || '' }}<br />
                {{ etablissement?.adresse?.code_postal }} {{ etablissement?.adresse?.ville }}<br />
                {{ etablissement?.adresse?.pays }}
              </p>
            </div>
            
            <div class="grid grid-cols-2 gap-2 border-t border-slate-200 pt-2 font-mono text-[10px] text-slate-500">
              <div>
                <span class="block text-[8px] font-bold uppercase tracking-wider text-slate-450">N° SIRET</span>
                <span class="font-bold text-slate-700">{{ etablissement?.siret || '-' }}</span>
              </div>
              <div>
                <span class="block text-[8px] font-bold uppercase tracking-wider text-slate-450">Code NAF</span>
                <span class="font-bold text-slate-700">{{ etablissement?.ape || '-' }}</span>
              </div>
              <div class="col-span-2">
                <span class="block text-[8px] font-bold uppercase tracking-wider text-slate-450">N° Cotisant</span>
                <span class="font-bold text-slate-700">{{ etablissement?.numero_cotisant || '-' }}</span>
              </div>
            </div>
          </div>

          <!-- Right Side: Employee Info -->
          <div class="space-y-3">
            <div class="bg-slate-50 border-2 border-slate-200 rounded-none p-4 space-y-2 shadow-flat">
              <div class="flex justify-between border-b border-slate-200 pb-1">
                <span class="font-bold text-slate-900 uppercase">{{ item.salarie?.civilite }} {{ item.salarie?.prenom }} {{ item.salarie?.nom?.toUpperCase() }}</span>
                <span class="font-mono text-slate-500 text-[10px] font-bold">Matricule : {{ item.salarie?.matricule }}</span>
              </div>
              
              <div class="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[10px] leading-tight">
                <div>
                  <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">Emploi / Poste</span>
                  <span class="font-bold text-slate-800 uppercase">{{ item.contrat?.emploi || 'Non spécifié' }}</span>
                </div>
                <div>
                  <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">Date d'embauche</span>
                  <span class="font-mono text-slate-800 font-semibold">{{ item.contrat?.date_debut_contrat || '-' }}</span>
                </div>
                <div class="col-span-2 border-t border-slate-200 pt-1">
                  <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">Adresse du Salarié</span>
                  <span class="text-slate-700 font-medium">
                    {{ item.salarie?.adresse || '-' }} {{ item.salarie?.adresse2 || '' }}<br />
                    {{ item.salarie?.code_postal }} {{ item.salarie?.ville }}
                  </span>
                </div>
                <div class="border-t border-slate-200 pt-1">
                  <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">N° Securité Sociale</span>
                  <span class="font-mono text-slate-800 font-semibold">{{ item.salarie?.numero_securite_sociale || '-' }}</span>
                </div>
                <div class="border-t border-slate-200 pt-1">
                  <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">Régime</span>
                  <span class="font-bold text-xs uppercase" :class="item.salarie?.expatrie ? 'text-amber-700' : 'text-slate-700'">
                    {{ item.salarie?.expatrie ? 'EXPATRIÉ (8.0% CN)' : 'LOCAL (1.5% CN)' }}
                  </span>
                </div>
                <div class="border-t border-slate-200 pt-1">
                  <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">Base Temps de Travail</span>
                  <span class="font-bold text-slate-800">
                    {{ item.contrat?.unite_temps === 'Jours' ? '30.00 jours / mois' : `${item.contrat?.horaires?.horaire_travail || '173.33'} heures / mois` }}
                  </span>
                </div>
                <div class="border-t border-slate-200 pt-1">
                  <span class="text-slate-450 block uppercase text-[8px] tracking-wide font-bold">Unité de temps</span>
                  <span class="font-bold text-slate-800 uppercase">{{ item.contrat?.unite_temps || 'Heures' }}</span>
                </div>
              </div>
            </div>
          </div>

        </div>

        <!-- Payslip Metadata / Period Bar -->
        <div class="my-4 py-3 px-4 bg-slate-50 border-2 border-slate-200 rounded-none flex justify-between items-center text-xs font-semibold shadow-flat">
          <div>
            <span>PÉRIODE : </span>
            <span class="font-bold text-slate-900 font-mono uppercase">{{ getPeriodLabel(item.bulletin.mois, item.bulletin.annee) }}</span>
          </div>
          <div>
            <span>DATE DE PAIEMENT : </span>
            <span class="font-mono text-slate-900">{{ item.bulletin.date_paiement ? new Date(item.bulletin.date_paiement).toLocaleDateString('fr-FR') : '-' }}</span>
          </div>
          <div>
            <span>MODE DE RÈGLEMENT : </span>
            <span class="text-slate-900 uppercase">VIREMENT BANCAIRE</span>
          </div>
        </div>

        <!-- Main Pay Lines Table -->
        <div class="overflow-x-auto border-2 border-slate-200 rounded-none shadow-flat">
          <table class="min-w-full divide-y divide-slate-250 text-xs">
            <thead class="bg-slate-100 text-slate-650 font-bold uppercase tracking-wider text-[9px] border-b-2 border-slate-200">
              <!-- Group Headers -->
              <tr>
                <th scope="col" rowspan="2" class="px-4 py-2.5 text-left w-1/4 border-r border-slate-200 align-middle">
                  <div class="flex items-center">
                    <div class="inline-block px-1.5 py-0.5 bg-slate-200 border border-slate-350 text-[10px] font-mono text-slate-800 font-bold uppercase mr-2" title="Nombre de jours ou d'heures travaillés (Base de calcul)">
                      {{ item.bulletin.cumuls?.mensuel?.heures_jours }} {{ item.contrat?.unite_temps === 'Jours' ? 'j' : 'h' }}
                    </div>
                    <span>Rubrique / Libellé</span>
                  </div>
                </th>
                <th scope="col" colspan="4" class="px-2 py-1 text-center bg-slate-50 border-r border-slate-200 border-b border-slate-200">Charges Employé</th>
                <th scope="col" colspan="3" class="px-2 py-1 text-center bg-slate-100 border-b border-slate-200">Charges Patronales</th>
              </tr>
              <!-- Sub Headers -->
              <tr class="bg-slate-50/50">
                <th scope="col" class="px-2 py-1.5 text-right border-r border-slate-200">Base</th>
                <th scope="col" class="px-2 py-1.5 text-right border-r border-slate-200">Taux</th>
                <th scope="col" class="px-2 py-1.5 text-right border-r border-slate-200">A déduire</th>
                <th scope="col" class="px-2 py-1.5 text-right border-r border-slate-200">A payer</th>
                <th scope="col" class="px-2 py-1.5 text-right border-r border-slate-200">Base</th>
                <th scope="col" class="px-2 py-1.5 text-right border-r border-slate-200">Taux</th>
                <th scope="col" class="px-2 py-1.5 text-right">Montant</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 font-mono text-slate-700 bg-white">
              <!-- Group 1: Gross Salary Elements -->
              <tr class="bg-slate-50/50 font-bold text-[10px] text-slate-650 uppercase tracking-wider no-print">
                <td colspan="8" class="px-4 py-1.5 text-left font-sans border-b border-slate-200">1. Éléments de Salaire Brut</td>
              </tr>
              <tr v-for="line in getGrossLines(item.bulletin)" :key="line.code" class="hover:bg-slate-50/50 transition-colors">
                <td class="px-4 py-2 text-left font-sans font-medium text-slate-900 border-r border-slate-100">{{ line.libelle }}</td>
                <!-- Emp Base -->
                <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-500">
                  {{ line.base_s ? `${line.base_s} ${line.code.startsWith('HS_') ? 'h' : (item.contrat?.unite_temps === 'Jours' ? 'j' : 'h')}` : '-' }}
                </td>
                <!-- Emp Taux -->
                <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-400">{{ line.taux_s > 0 ? formatPercent(line.taux_s) : '-' }}</td>
                <!-- Emp Deduct -->
                <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-400">-</td>
                <!-- Emp Pay -->
                <td class="px-2 py-2 text-right border-r border-slate-100 font-bold text-slate-900" :class="{ 'text-red-650': line.montant_pr < 0 }">
                  {{ line.montant_pr !== 0 ? formatXOF(line.montant_pr) : '-' }}
                </td>
                <!-- Pat Base -->
                <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-550">
                  {{ line.base_p ? `${line.base_p} ${line.code.startsWith('HS_') ? 'h' : (item.contrat?.unite_temps === 'Jours' ? 'j' : 'h')}` : '-' }}
                </td>
                <!-- Pat Taux -->
                <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-400">{{ line.taux_p > 0 ? formatPercent(line.taux_p) : '-' }}</td>
                <!-- Pat Montant -->
                <td class="px-2 py-2 text-right" :class="line.montant_cp > 0 ? 'text-slate-900 font-bold' : 'text-slate-400'">
                  {{ line.montant_cp > 0 ? formatXOF(line.montant_cp) : '-' }}
                </td>
              </tr>
              <!-- Subtotal Gross -->
              <tr class="bg-slate-100 font-extrabold border-t border-b border-slate-300">
                <td class="px-4 py-2 text-left font-sans text-slate-950 uppercase text-[10px] border-r border-slate-200">Total Salaire Brut</td>
                <td class="px-2 py-2 border-r border-slate-100"></td>
                <td class="px-2 py-2 border-r border-slate-100"></td>
                <td class="px-2 py-2 border-r border-slate-100"></td>
                <td class="px-2 py-2 text-right font-mono text-slate-950 border-r border-slate-200">{{ formatXOF(item.bulletin.salaire_brut) }}</td>
                <td class="px-2 py-2 border-r border-slate-100"></td>
                <td class="px-2 py-2 border-r border-slate-100"></td>
                <td class="px-2 py-2 text-right text-slate-450">-</td>
              </tr>

              <!-- Group 2: Cotisations & Retenues -->
              <tr class="bg-slate-50/50 font-bold text-[10px] text-slate-650 uppercase tracking-wider no-print">
                <td colspan="8" class="px-4 py-1.5 text-left font-sans border-b border-slate-200">2. Cotisations & Retenues Fiscales et Sociales</td>
              </tr>
              <tr v-for="line in getCotisationsLines(item.bulletin)" :key="line.code" class="hover:bg-slate-50/50 transition-colors">
                <td class="px-4 py-2 text-left font-sans font-medium text-slate-900 border-r border-slate-100">{{ line.libelle }}</td>
                <!-- Emp Base -->
                <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-500">{{ line.base_s || '-' }}</td>
                <!-- Emp Taux -->
                <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-400">{{ line.taux_s > 0 ? formatPercent(line.taux_s) : '-' }}</td>
                <!-- Emp Deduct -->
                <td class="px-2 py-2 text-right border-r border-slate-100 font-bold text-slate-900">{{ line.montant_cs !== 0 ? formatXOF(line.montant_cs) : '-' }}</td>
                <!-- Emp Pay -->
                <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-450">-</td>
                <!-- Pat Base -->
                <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-500">{{ line.base_p || '-' }}</td>
                <!-- Pat Taux -->
                <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-400">{{ line.taux_p > 0 ? formatPercent(line.taux_p) : '-' }}</td>
                <!-- Pat Montant -->
                <td class="px-2 py-2 text-right font-bold text-slate-900">{{ line.montant_cp > 0 ? formatXOF(line.montant_cp) : '-' }}</td>
              </tr>
              <!-- Subtotal Cotisations -->
              <tr class="bg-slate-100 font-extrabold border-t border-b border-slate-300">
                <td class="px-4 py-2 text-left font-sans text-slate-950 uppercase text-[10px] border-r border-slate-200">Total Cotisations & Retenues</td>
                <td class="px-2 py-2 border-r border-slate-100"></td>
                <td class="px-2 py-2 border-r border-slate-100"></td>
                <td class="px-2 py-2 text-right font-mono text-slate-950 border-r border-slate-200">{{ formatXOF(item.bulletin.cotisations_salariales) }}</td>
                <td class="px-2 py-2 border-r border-slate-100 text-slate-450">-</td>
                <td class="px-2 py-2 border-r border-slate-100"></td>
                <td class="px-2 py-2 border-r border-slate-100"></td>
                <td class="px-2 py-2 text-right font-mono text-slate-950">{{ formatXOF(item.bulletin.cotisations_patronales) }}</td>
              </tr>

              <!-- Group 3: Indemnités & Retenues diverses -->
              <tr class="bg-slate-50/50 font-bold text-[10px] text-slate-650 uppercase tracking-wider no-print">
                <td colspan="8" class="px-4 py-1.5 text-left font-sans border-b border-slate-200">3. Indemnités & Retenues diverses</td>
              </tr>
              <tr v-for="line in getNetLines(item.bulletin)" :key="line.code" class="hover:bg-slate-50/50 transition-colors">
                <td class="px-4 py-2 text-left font-sans font-medium text-slate-900 border-r border-slate-100">{{ line.libelle }}</td>
                <!-- Emp Base -->
                <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-500">{{ line.base_s || '-' }}</td>
                <!-- Emp Taux -->
                <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-450">-</td>
                <!-- Emp Deduct -->
                <td class="px-2 py-2 text-right border-r border-slate-100 font-bold text-slate-900" :class="{ 'text-red-650': line.montant_cs > 0 }">
                  {{ line.montant_cs > 0 ? formatXOF(line.montant_cs) : '-' }}
                </td>
                <!-- Emp Pay -->
                <td class="px-2 py-2 text-right border-r border-slate-100 font-bold text-slate-900" :class="{ 'text-red-650': line.montant_pr < 0 }">
                  {{ line.montant_pr > 0 ? formatXOF(line.montant_pr) : '-' }}
                </td>
                <!-- Pat Base -->
                <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-450">-</td>
                <!-- Pat Taux -->
                <td class="px-2 py-2 text-right border-r border-slate-100 text-slate-450">-</td>
                <!-- Pat Montant -->
                <td class="px-2 py-2 text-right text-slate-400">-</td>
              </tr>

              <!-- Net à Payer Highlight Row -->
              <tr class="bg-green-600 font-extrabold text-white">
                <td class="px-4 py-3 text-left font-sans uppercase tracking-wider text-[11px] text-white border-r border-green-700">Net à payer</td>
                <td class="px-2 py-3 border-r border-green-500"></td>
                <td class="px-2 py-3 border-r border-green-500"></td>
                <td class="px-2 py-3 border-r border-green-500"></td>
                <td class="px-2 py-3 text-right font-mono text-white text-base border-r border-green-700">{{ formatXOF(item.bulletin.net_a_payer) }}</td>
                <td class="px-2 py-3 border-r border-green-500"></td>
                <td class="px-2 py-3 border-r border-green-500"></td>
                <td class="px-2 py-3 text-right text-white font-mono">-</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Bottom Tables: Monthly/Annual Cumulates & Vacation Tracker -->
        <div v-if="item.bulletin.cumuls" class="mt-8 border-t-2 border-slate-200 pt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- Cumuls Table (cols-span 2) -->
          <div class="md:col-span-2 space-y-2">
            <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider">Cumuls Période et Annuel</h4>
            <div class="overflow-x-auto rounded-none border-2 border-slate-200 shadow-flat">
              <table class="min-w-full divide-y divide-slate-200 text-[10px] text-left">
                <thead class="bg-slate-100 font-bold text-slate-650 border-b border-slate-200">
                  <tr>
                    <th scope="col" class="px-2 py-1.5">Période</th>
                    <th scope="col" class="px-2 py-1.5 text-right">Heures/Jours</th>
                    <th scope="col" class="px-2 py-1.5 text-right">Brut (FCFA)</th>
                    <th scope="col" class="px-2 py-1.5 text-right">Brut CNPS</th>
                    <th scope="col" class="px-2 py-1.5 text-right">Retraite</th>
                    <th scope="col" class="px-2 py-1.5 text-right">IBS</th>
                    <th scope="col" class="px-2 py-1.5 text-right">CMU</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-150 font-mono text-slate-700 bg-white">
                  <tr class="hover:bg-slate-50/50">
                    <td class="px-2 py-1.5 font-sans font-bold text-slate-900">Mensuel</td>
                    <td class="px-2 py-1.5 text-right font-semibold">{{ item.bulletin.cumuls.mensuel.heures_jours }} {{ item.contrat?.unite_temps === 'Jours' ? 'j' : 'h' }}</td>
                    <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(item.bulletin.cumuls.mensuel.salaire_brut) }}</td>
                    <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(item.bulletin.cumuls.mensuel.brut_cnps) }}</td>
                    <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(item.bulletin.cumuls.mensuel.cot_retraite) }}</td>
                    <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(item.bulletin.cumuls.mensuel.ibs) }}</td>
                    <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(item.bulletin.cumuls.mensuel.cmu) }}</td>
                  </tr>
                  <tr class="hover:bg-slate-50/50 bg-slate-50/30">
                    <td class="px-2 py-1.5 font-sans font-bold text-slate-900">Annuel</td>
                    <td class="px-2 py-1.5 text-right font-semibold">{{ item.bulletin.cumuls.annuel.heures_jours }} {{ item.contrat?.unite_temps === 'Jours' ? 'j' : 'h' }}</td>
                    <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(item.bulletin.cumuls.annuel.salaire_brut) }}</td>
                    <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(item.bulletin.cumuls.annuel.brut_cnps) }}</td>
                    <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(item.bulletin.cumuls.annuel.cot_retraite) }}</td>
                    <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(item.bulletin.cumuls.annuel.ibs) }}</td>
                    <td class="px-2 py-1.5 text-right font-semibold">{{ formatXOF(item.bulletin.cumuls.annuel.cmu) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Congés Payés Card -->
          <div class="space-y-2">
            <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider">Congés Payés</h4>
            <div class="bg-white border-2 border-slate-200 rounded-none p-3 space-y-1.5 shadow-flat text-[10px] text-slate-650">
              <div class="flex justify-between font-mono font-semibold">
                <span>Droits acquis (Cumul) :</span>
                <span class="font-bold text-slate-900">{{ item.bulletin.cumuls?.annuel?.conges_acquis?.toFixed(2) }} j</span>
              </div>
              <div class="flex justify-between font-mono font-semibold">
                <span>Pris ce mois :</span>
                <span class="font-bold text-slate-900">{{ item.bulletin.cumuls?.mensuel?.conges_pris?.toFixed(2) }} j</span>
              </div>
              <div class="flex justify-between font-mono border-t border-slate-200 pt-1.5 font-semibold">
                <span>Solde disponible :</span>
                <span class="font-bold text-green-700 text-sm">{{ item.bulletin.cumuls?.mensuel?.conges_solde?.toFixed(2) }} jours</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
@media print {
  .no-print {
    display: none !important;
  }
  body, .print-container {
    background-color: transparent !important;
    color: black !important;
  }
  .print-payslip-page {
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    box-shadow: none !important;
    page-break-after: always;
    break-after: page;
  }
  .print-payslip-page:last-child {
    page-break-after: avoid;
    break-after: avoid;
  }
}
</style>
