<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Mina verktyg"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Här ser du verktyg du underhåller.</li>
      <li>Klicka <strong>Redigera</strong> för att öppna skripteditorn.</li>
    </ul>
  </HelpTopicLayout>
</template>
