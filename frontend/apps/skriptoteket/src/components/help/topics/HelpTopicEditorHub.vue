<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Kodredigerare"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Här startar du arbetet med verktyg du bygger eller ansvarar för.</li>
      <li>Öppna ett befintligt verktyg för att fortsätta på en version.</li>
      <li>Skapa bara nya verktyg när du vet vilket lärarproblem verktyget ska lösa.</li>
    </ul>
  </HelpTopicLayout>
</template>
