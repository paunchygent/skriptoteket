<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Logga in"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Logga in för att komma till startsidan.</li>
      <li>Använd din skol-/arbets-e-post.</li>
      <li>Om det inte går: kontrollera stavning och Caps Lock.</li>
      <li>Glömt lösenord? Använd länken i inloggningen för att begära en återställningslänk.</li>
      <li>Har du inte verifierat kontot än kan du begära ett nytt verifieringsmejl.</li>
    </ul>
  </HelpTopicLayout>
</template>
