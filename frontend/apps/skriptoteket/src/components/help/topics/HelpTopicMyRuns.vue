<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Mina körningar"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>
        Här ligger alla dina körningar, den senaste först. Du ser status, vilket
        verktyg det var och när den startade.
      </li>
      <li>Klicka på en rad för att se resultat, nedladdningar och felmeddelanden.</li>
      <li>
        <strong>Pågår</strong> betyder att verktyget arbetar,
        <strong>klar</strong> att resultat finns att hämta och
        <strong>misslyckad</strong> att något gick fel.
      </li>
    </ul>
  </HelpTopicLayout>
</template>
