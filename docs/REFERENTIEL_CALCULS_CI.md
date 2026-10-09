# Référentiel des calculs réglementaires — Côte d'Ivoire

Ce document décrit les règles implémentées dans `backend/app/services/` et les
textes sur lesquels elles s'appuient. Il sert de référence pour vérifier un
calcul et pour préparer une mise à jour réglementaire.

> Toutes les valeurs paramétrables sont regroupées en tête de chaque module
> afin d'être ajustées sans toucher à la logique. Les montants doivent être
> validés par un professionnel avant usage en production.

---

## 1. Indemnité de licenciement et de départ à la retraite

**Textes** : décret n° 2017-210 du 30 mars 2017 (abrogeant le décret n° 96-201
du 7 mars 1996), articles 2, 4 et 5.

| Élément | Règle |
|---|---|
| Conditions (art. 2) | Au moins **1 an de service effectif** et **absence de faute lourde** |
| Salaire de référence (art. 4) | **Salaire global mensuel moyen des 12 derniers mois** |
| Barème (art. 4) | **30 %** de la 1re à la 5e année · **35 %** de la 6e à la 10e · **40 %** au-delà |
| Fractions d'année | Retenues en **mois complets**, arrondies au mois inférieur |
| Départ à la retraite (art. 5) | Calculé dans les **mêmes conditions** que le licenciement |

Formule : `indemnité = Σ (mois de la tranche / 12) × taux × salaire mensuel moyen`

**Exemple** — 104 mois d'ancienneté, 12 salaires de 300 000 F :
`60/12 × 30 % × 300 000 = 450 000` + `44/12 × 35 % × 300 000 ≈ 385 000` = **835 000 F**

Module : `app/services/indemnites_rupture.py`
Fonctions : `calculer_indemnite_rupture()`, `anciennete_en_mois()`

---

## 2. Indemnité de décès et frais funéraires

**Texte** : décret n° 2017-210 (droits des ayants droit).

| Élément | Règle |
|---|---|
| Indemnité | **Équivalente à l'indemnité de licenciement** (barème 30/35/40 %) |
| Éligibilité | **≥ 12 mois d'ancienneté** *ou* conditions de départ à la retraite remplies |
| Frais funéraires | **3 ×** le SMHC mensuel jusqu'à 5 ans · **4 ×** de 6 à 10 ans · **6 ×** au-delà |

Les frais funéraires sont dus **même lorsque l'indemnité ne l'est pas**.

**Exemple** — 72 mois, salaire moyen 350 000 F, SMHC 125 000 F :
indemnité `5 × 30 % × 350 000 + 1 × 35 % × 350 000 = 647 500` ; frais `4 × 125 000 = 500 000` → **1 147 500 F**

Module : `app/services/indemnites_rupture.py`
Fonctions : `calculer_indemnite_deces()`, `multiplicateur_frais_funeraire()`

---

## 3. Indemnité de fin de CDD

**Texte** : article 15.8 du Code du travail (loi n° 2015-532).

| Élément | Règle |
|---|---|
| Montant | **3 %** du total des rémunérations brutes perçues pendant le contrat |
| Versement | Lors du règlement du dernier salaire |

### Cas d'exclusion retenus

- refus d'un CDI pour le même emploi ou un emploi similaire à rémunération au moins équivalente ;
- rupture anticipée à l'initiative du salarié ;
- rupture consécutive à une faute lourde ;
- conclusion effective d'un CDI à l'issue du CDD.

Tout autre motif est marqué **« à vérifier »** : aucun montant n'est attribué
automatiquement.

Module : `app/services/indemnites_rupture.py`
Fonctions : `calculer_indemnite_fin_cdd()`

---

## 4. Gratification annuelle (prime de fin d'année)

**Texte** : article 53 de la Convention collective interprofessionnelle.

| Élément | Règle |
|---|---|
| Base | **Salaire minimum conventionnel mensuel de la catégorie** (SMHC), et non le salaire réellement versé |
| Minimum | **75 %** du SMHC sur une année pleine |
| Prorata | **Année de 360 jours** (12 × 30), bornes incluses |
| Règles d'entreprise | Un taux supérieur ou un montant fixe peut être paramétré ; **le montant le plus favorable est retenu** |

Formule : `gratification = max(SMHC × 75 % × prorata ; SMHC × taux entreprise × prorata ; montant fixe × prorata)`

**Exemple** — SMHC 125 000 F, 270 jours de service :
`125 000 × 75 % = 93 750` → `93 750 × (270/360) =` **70 312,50 F**

Module : `app/services/conges_gratification.py`
Fonctions : `calculer_gratification()`, `jours_service_annuels()`, `jours_service_360()`

---

## 5. Congés payés

**Textes** : Code du travail art. 25.1 et 25.2 ; Convention collective art. 71
et 72 ; décret n° 98-39 du 28 janvier 1998, art. 12, 14 et 16.

| Élément | Règle |
|---|---|
| Acquisition | **2,2 jours ouvrables** par mois de service effectif |
| Majorations d'ancienneté | < 5 ans : 0 · 5 à < 10 : 1 j · 10 à < 15 : 2 j · 15 à < 20 : 3 j · 20 à < 25 : 5 j · 25 à < 30 : 7 j · ≥ 30 : **8 j** |
| Salaire journalier | Salaire mensuel moyen **/ 30** (art. 71) |
| Conversion ouvrables → calendaires | Coefficient **1,25** (24 j ouvrables = 30 j calendaires) |

### Deux méthodes de valorisation

1. **Conventionnelle** (art. 71-72) : `salaire journalier × jours calendaires`
2. **Décret n° 98-39** (art. 12) : allocation principale = `rémunération totale × 1/12`, puis `(allocation principale / jours principaux acquis) × solde`

Les deux montants sont calculés et comparés ; la méthode retenue est
paramétrable. Un montant validé par le gestionnaire peut être saisi directement.

**Exemple** — 12 mois à 350 000 F, 12 mois de service, 15 jours pris :
droits `12 × 2,2 = 26,4 j` ; solde `11,4 j ouvrables = 14,25 j calendaires` ;
conventionnelle `11 666,67 × 14,25 =` **166 250 F** ; décret `(350 000/26,4) × 11,4 ≈ 151 136 F`.

Module : `app/services/conges_gratification.py`
Fonctions : `calculer_conges_payes()`, `droits_conges_acquis()`, `majoration_anciennete()`

---

## 6. Avantages en nature

**Source** : note de service DGI du 08/07/2024 (n° 0053/0001).

### Barème logement (montants mensuels en F CFA)

| Pièces | Logement | Mobilier | Électricité | Eau |
|---:|---:|---:|---:|---:|
| 1 | 60 000 | 10 000 | 10 000 | 10 000 |
| 2 | 80 000 | 20 000 | 20 000 | 15 000 |
| 3 | 160 000 | 40 000 | 30 000 | 20 000 |
| 4 | 300 000 | 60 000 | 40 000 | 30 000 |
| 5 | 480 000 | 80 000 | 50 000 | 40 000 |
| 6 | 600 000 | 100 000 | 60 000 | 50 000 |
| 7 et + | 800 000 | 150 000 | 70 000 | 60 000 |

### Autres composantes

| Élément | Montant |
|---|---|
| Climatiseur / pièce climatisée | 20 000 par unité |
| Piscine | 30 000 forfait mensuel |
| Gardien / jardinier | 50 000 par personne |
| Employé de maison | 60 000 par personne |
| Cuisinier | 90 000 par personne |
| Repas | Coût réel − **30 000** d'exonération si applicable |
| Autres avantages | Coût réel supporté par l'employeur |

### Véhicule

| Mise à disposition | Traitement fiscal |
|---|---|
| Véhicule de fonction ou de service | **Non imposable** (note DGI du 08/07/2024) |
| Transport collectif — coûts réels | Coût total / nombre de bénéficiaires, **− 30 000** d'exonération, − participation |
| Transport collectif — forfait par salarié | Forfait **− 30 000**, − participation |
| Autre véhicule taxable | Valeur réelle mensuelle |

### Articulation des assiettes

```
Avantage imposable      = Σ composantes − participation du salarié
Salaire brut imposable  = salaire et primes imposables + avantage imposable
Assiette CNPS           = salaire hors avantage + valeur réelle saisie
```

Le **fisc** retient une évaluation forfaitaire, la **CNPS** la valeur réelle :
les deux assiettes sont donc saisies séparément et suivies distinctement.

**Exemple** — salaire 1 000 000 F, logement 3 pièces avec charges, 2 climatiseurs :
`160 000 + 40 000 + 30 000 + 20 000 + 40 000 = 290 000` → brut imposable **1 290 000 F**

Module : `app/services/avantages_nature.py`
Fonctions : `calculer_avantages_nature()`, `calculer_avantage_vehicule()`, `bareme_logement()`

---

## Points de vigilance

1. **Le SMHC est indispensable** à la gratification et aux frais funéraires. Il
   est lu sur le contrat (`contrats.smhc_mensuel`) ou, à défaut, sur la grille du
   poste de salaire rattaché. S'il est absent, un avertissement est remis plutôt
   qu'un montant erroné.
2. **Les barèmes sont forfaitaires** : une convention collective ou un accord
   d'entreprise plus favorable doit primer.
3. **Le salaire de référence** (12 derniers mois) est repris des bulletins
   existants ; il peut être transmis explicitement lorsqu'un mois doit être
   écarté (prime exceptionnelle, rappel).
4. **Les indemnités de rupture sont exonérées d'ITS** dans les limites légales :
   elles sont intégrées au solde de tout compte, pas au brut du bulletin.
