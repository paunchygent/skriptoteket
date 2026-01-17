<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Laddar hjälp"
    @back="showIndex"
  >
    <p class="text-sm text-navy/70">
      Hämtar innehållet. Det här tar bara en liten stund.
    </p>
  </HelpTopicLayout>
</template>
