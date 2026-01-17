<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="App"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Klicka <strong>Starta</strong> för att köra appen.</li>
      <li>Resultat och nästa steg visas under.</li>
    </ul>
  </HelpTopicLayout>
</template>
