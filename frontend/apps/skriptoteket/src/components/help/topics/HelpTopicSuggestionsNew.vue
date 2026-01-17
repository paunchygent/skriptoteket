<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Föreslå skript"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Skriv en tydlig titel och en kort beskrivning av vad skriptet ska göra.</li>
      <li>Välj relevanta yrken och kategorier så att andra hittar det.</li>
      <li>Klicka <strong>Skicka förslag</strong> när du är klar.</li>
    </ul>
  </HelpTopicLayout>
</template>
