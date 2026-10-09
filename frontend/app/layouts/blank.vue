<template>
  <!--
    Layout « nu » : utilisé par les pages d'impression (bulletins, attestations,
    certificats, solde de tout compte). Il ne rend aucun habillage de
    navigation, afin que l'aperçu avant impression corresponde exactement au
    document imprimé.
  -->
  <div class="print-root bg-white min-h-screen">
    <slot />
  </div>
</template>

<style>
@media print {
  /* Aucune marge de page imposée par l'habillage : le document gère la sienne. */
  html, body {
    background: #ffffff !important;
    margin: 0 !important;
    padding: 0 !important;
  }
}
</style>
