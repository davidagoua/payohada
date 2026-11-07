/**
 * Tests de la logique de navigation par rôle.
 *
 * Aucune dépendance de test n'est ajoutée : le module TS est transpilé à la
 * volée avec esbuild (déjà présent) puis exécuté par Node.
 *
 *     node scripts/test-auth-navigation.mjs
 */
import { buildSync } from 'esbuild'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

const dossier = mkdtempSync(join(tmpdir(), 'authnav-'))
const sortie = join(dossier, 'authNavigation.mjs')

buildSync({
  entryPoints: ['app/utils/authNavigation.ts'],
  outfile: sortie,
  bundle: true,
  format: 'esm',
  platform: 'neutral',
  logLevel: 'silent'
})

const { deciderRedirection, destinationParDefaut } = await import(pathToFileURL(sortie).href)

const CABINET = { role: 'cabinet', is_admin: false }
const ADMIN = { role: 'cabinet', is_admin: true }
const CLIENT = { role: 'client', dossier_id: 1, is_admin: false }
const SALARIE = { role: 'salarie', salarie_id: 7, is_admin: false }
const GESTIONNAIRE = { role: 'gestionnaire_paie', is_admin: false }

let echecs = 0
let total = 0

function verifier(intitule, obtenu, attendu) {
  total += 1
  const ok = JSON.stringify(obtenu) === JSON.stringify(attendu)
  if (!ok) {
    echecs += 1
    console.error(`  ✗ ${intitule}`)
    console.error(`      attendu : ${JSON.stringify(attendu)}`)
    console.error(`      obtenu  : ${JSON.stringify(obtenu)}`)
  } else {
    console.log(`  ✓ ${intitule}`)
  }
}

const laisser = { action: 'laisser' }
const vers = (destination) => ({ action: 'rediriger', destination })

console.log('Régression : la boucle de redirection')
// LE cas qui bloquait la machine : jeton valide mais profil absent.
verifier('/login avec jeton SANS profil ne redirige pas',
  deciderRedirection({ chemin: '/login', aJeton: true, utilisateur: null }), laisser)
verifier('/login avec jeton et profil cabinet va vers /dossiers',
  deciderRedirection({ chemin: '/login', aJeton: true, utilisateur: CABINET }), vers('/dossiers'))
verifier('/login avec jeton et profil salarié va vers /salaries/bulletins',
  deciderRedirection({ chemin: '/login', aJeton: true, utilisateur: SALARIE }), vers('/salaries/bulletins'))
verifier('/login avec profil gestionnaire de paie va vers /dossiers',
  deciderRedirection({ chemin: '/login', aJeton: true, utilisateur: GESTIONNAIRE }), vers('/dossiers'))
verifier('/login sans jeton reste sur /login',
  deciderRedirection({ chemin: '/login', aJeton: false, utilisateur: null }), laisser)
verifier('/ reste accessible sans session',
  deciderRedirection({ chemin: '/', aJeton: false, utilisateur: null }), laisser)

console.log('\nParcours « mot de passe oublié » (accessible sans session)')
verifier('/forgot-password accessible sans jeton',
  deciderRedirection({ chemin: '/forgot-password', aJeton: false, utilisateur: null }), laisser)
verifier('/reset-password accessible sans jeton (lien reçu par email)',
  deciderRedirection({ chemin: '/reset-password', aJeton: false, utilisateur: null }), laisser)
verifier('/forgot-password redirige un utilisateur connecté vers son espace',
  deciderRedirection({ chemin: '/forgot-password', aJeton: true, utilisateur: CABINET }), laisser)
verifier('/reset-password reste accessible même avec un jeton en cache',
  deciderRedirection({ chemin: '/reset-password', aJeton: true, utilisateur: null }), laisser)

console.log('\nProtection des routes')
verifier('route protégée sans jeton renvoie vers /login avec redirect',
  deciderRedirection({ chemin: '/dossiers', aJeton: false, utilisateur: null }),
  vers('/login?redirect=%2Fdossiers'))
verifier('route protégée avec jeton sans profil laisse passer (l\'API tranche)',
  deciderRedirection({ chemin: '/dossiers', aJeton: true, utilisateur: null }), laisser)

console.log('\nCloisonnement par rôle')
verifier('cabinet accède à /dossiers',
  deciderRedirection({ chemin: '/dossiers', aJeton: true, utilisateur: CABINET }), laisser)
verifier('gestionnaire de paie accède à /dossiers',
  deciderRedirection({ chemin: '/dossiers/12', aJeton: true, utilisateur: GESTIONNAIRE }), laisser)
verifier('gestionnaire de paie est renvoyé de /client vers /dossiers',
  deciderRedirection({ chemin: '/client', aJeton: true, utilisateur: GESTIONNAIRE }), vers('/dossiers'))
verifier('gestionnaire de paie accède aux bulletins',
  deciderRedirection({ chemin: '/bulletins', aJeton: true, utilisateur: GESTIONNAIRE }), laisser)
verifier('client est renvoyé de /dossiers vers /client',
  deciderRedirection({ chemin: '/dossiers/12', aJeton: true, utilisateur: CLIENT }), vers('/client'))
verifier('salarié est renvoyé de /dossiers vers /salaries/bulletins',
  deciderRedirection({ chemin: '/dossiers', aJeton: true, utilisateur: SALARIE }), vers('/salaries/bulletins'))
verifier('client accède à /client',
  deciderRedirection({ chemin: '/client/variables', aJeton: true, utilisateur: CLIENT }), laisser)
verifier('salarié accède à /salaries/bulletins',
  deciderRedirection({ chemin: '/salaries/bulletins', aJeton: true, utilisateur: SALARIE }), laisser)
verifier('cabinet est renvoyé de /client vers /dossiers',
  deciderRedirection({ chemin: '/client', aJeton: true, utilisateur: CABINET }), vers('/dossiers'))
verifier('cabinet accède à l\'administration du cabinet',
  deciderRedirection({ chemin: '/admin', aJeton: true, utilisateur: CABINET }), laisser)
verifier('cabinet accède aux utilisateurs du cabinet',
  deciderRedirection({ chemin: '/admin/utilisateurs', aJeton: true, utilisateur: CABINET }), laisser)
verifier('cabinet consulte les constantes (lecture seule)',
  deciderRedirection({ chemin: '/admin/constantes', aJeton: true, utilisateur: CABINET }), laisser)
verifier('cabinet consulte le plan de paie (lecture seule)',
  deciderRedirection({ chemin: '/admin/plan-paie', aJeton: true, utilisateur: CABINET }), laisser)
verifier('gestionnaire de paie accède aux réclamations',
  deciderRedirection({ chemin: '/admin/reclamations', aJeton: true, utilisateur: GESTIONNAIRE }), laisser)
verifier('gestionnaire de paie est renvoyé des utilisateurs du cabinet',
  deciderRedirection({ chemin: '/admin/utilisateurs', aJeton: true, utilisateur: GESTIONNAIRE }), vers('/dossiers'))
verifier('client est renvoyé de /admin vers /client',
  deciderRedirection({ chemin: '/admin', aJeton: true, utilisateur: CLIENT }), vers('/client'))
verifier('admin accède à /admin',
  deciderRedirection({ chemin: '/admin', aJeton: true, utilisateur: ADMIN }), laisser)
verifier('admin accède aux référentiels globaux',
  deciderRedirection({ chemin: '/admin/constantes', aJeton: true, utilisateur: ADMIN }), laisser)
verifier('admin accède au plan de paie',
  deciderRedirection({ chemin: '/admin/plan-paie', aJeton: true, utilisateur: ADMIN }), laisser)
verifier('admin accède à la gestion des cabinets',
  deciderRedirection({ chemin: '/admin/cabinets', aJeton: true, utilisateur: ADMIN }), laisser)
verifier('admin plateforme est renvoyé des dossiers vers son tableau de bord',
  deciderRedirection({ chemin: '/dossiers', aJeton: true, utilisateur: ADMIN }), vers('/admin'))
verifier('admin plateforme n\'ouvre pas une société',
  deciderRedirection({ chemin: '/dossiers/12/etablissements/3', aJeton: true, utilisateur: ADMIN }), vers('/admin'))
verifier('admin plateforme n\'ouvre pas la gestion des bulletins',
  deciderRedirection({ chemin: '/bulletins', aJeton: true, utilisateur: ADMIN }), vers('/admin'))
verifier('admin plateforme n\'administre pas les membres d\'un cabinet',
  deciderRedirection({ chemin: '/admin/utilisateurs', aJeton: true, utilisateur: ADMIN }), vers('/admin'))
verifier('admin plateforme ne voit pas les réclamations des salariés',
  deciderRedirection({ chemin: '/admin/reclamations', aJeton: true, utilisateur: ADMIN }), vers('/admin'))
verifier('admin plateforme garde le simulateur',
  deciderRedirection({ chemin: '/simulation', aJeton: true, utilisateur: ADMIN }), laisser)
verifier('cabinet n\'ouvre pas la gestion des cabinets',
  deciderRedirection({ chemin: '/admin/cabinets', aJeton: true, utilisateur: CABINET }), vers('/dossiers'))
verifier('admin connecté quittant /login va sur son tableau de bord',
  deciderRedirection({ chemin: '/login', aJeton: true, utilisateur: ADMIN }), vers('/admin'))
verifier('client est renvoyé de /bulletins vers /client',
  deciderRedirection({ chemin: '/bulletins', aJeton: true, utilisateur: CLIENT }), vers('/client'))
verifier('route inconnue laissée en l\'état',
  deciderRedirection({ chemin: '/une/route/libre', aJeton: true, utilisateur: CABINET }), laisser)

console.log('\nInvariant anti-boucle')
// Aucune combinaison ne doit proposer de rediriger vers la route courante.
const chemins = ['/', '/login', '/forgot-password', '/reset-password', '/dossiers', '/client', '/salaries/bulletins', '/admin', '/admin/utilisateurs', '/admin/constantes', '/admin/cabinets', '/admin/reclamations', '/bulletins', '/simulation']
const profils = [null, CABINET, ADMIN, CLIENT, SALARIE]
let boucles = 0
for (const chemin of chemins) {
  for (const utilisateur of profils) {
    for (const aJeton of [true, false]) {
      const d = deciderRedirection({ chemin, aJeton, utilisateur })
      if (d.action === 'rediriger' && d.destination === chemin) boucles += 1
    }
  }
}
verifier(`${chemins.length * profils.length * 2} combinaisons testées, aucune boucle`, boucles, 0)

console.log('\nEspace d\'accueil par défaut')
verifier('destinationParDefaut(cabinet)', destinationParDefaut(CABINET), '/dossiers')
verifier('destinationParDefaut(client)', destinationParDefaut(CLIENT), '/client')
verifier('destinationParDefaut(salarié)', destinationParDefaut(SALARIE), '/salaries/bulletins')
verifier('destinationParDefaut(admin plateforme)', destinationParDefaut(ADMIN), '/admin')

rmSync(dossier, { recursive: true, force: true })

console.log(`\n${total - echecs}/${total} vérifications réussies`)
if (echecs > 0) {
  console.error(`❌ ${echecs} échec(s)`)
  process.exit(1)
}
console.log('✅ Toutes les vérifications passent')
