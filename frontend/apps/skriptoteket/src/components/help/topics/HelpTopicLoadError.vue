<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import SystemMessage from "../../ui/shared/components/SystemMessage.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Kunde inte ladda"
    @back="showIndex"
  >
    <SystemMessage tone="failure">
      Hjälpavsnittet kunde inte laddas. Försök igen eller välj ett annat ämne.
    </SystemMessage>
  </HelpTopicLayout>
</template>
