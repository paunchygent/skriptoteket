<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Förslag (admin)"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>
        Öppna ett förslag och läs igenom titel, beskrivning, yrken och kategorier.
      </li>
      <li>Fatta beslut och skriv en kort motivering.</li>
    </ul>
  </HelpTopicLayout>
</template>
