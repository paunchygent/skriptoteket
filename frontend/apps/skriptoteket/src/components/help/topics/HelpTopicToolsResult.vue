<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Resultat"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Här ser du utdata och eventuella filer från körningen.</li>
      <li>Om du får fel: prova igen eller kontrollera att filen är rätt.</li>
    </ul>
  </HelpTopicLayout>
</template>
