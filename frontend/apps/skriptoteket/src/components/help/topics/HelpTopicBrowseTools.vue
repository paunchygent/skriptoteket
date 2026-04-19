<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Katalog: verktyg och appar"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>
        Här syns både <strong>verktyg</strong> och <strong>appar</strong>.
        Verktyg är små, fokuserade funktioner du kör med några inställningar.
        Appar är större arbetsytor -- som Klassrumskartan -- med egen vy och flera steg.
      </li>
      <li>Klicka på ett kort för att se mer och komma igång.</li>
      <li>Använd filtren för att begränsa till ditt yrke, en kategori eller en viss typ.</li>
    </ul>
  </HelpTopicLayout>
</template>
