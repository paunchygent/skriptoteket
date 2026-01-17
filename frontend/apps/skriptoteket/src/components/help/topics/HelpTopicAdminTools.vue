<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Testyta (admin)"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>
        Här hanterar du verktyg: publicera, avpublicera och öppna för redigering.
      </li>
      <li>Verktyg måste ha en aktiv version för att kunna publiceras.</li>
    </ul>
  </HelpTopicLayout>
</template>
