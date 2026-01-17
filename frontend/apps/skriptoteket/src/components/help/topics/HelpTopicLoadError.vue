<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Kunde inte ladda"
    @back="showIndex"
  >
    <p class="text-sm text-navy/70">
      Hjälpavsnittet kunde inte laddas. Försök igen eller välj ett annat ämne.
    </p>
  </HelpTopicLayout>
</template>
