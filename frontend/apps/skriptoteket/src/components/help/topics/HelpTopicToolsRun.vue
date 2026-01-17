<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Kör ett verktyg"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Ladda upp en fil och klicka <strong>Kör</strong>.</li>
      <li>Resultatet visas under formuläret när körningen är klar.</li>
    </ul>
  </HelpTopicLayout>
</template>
