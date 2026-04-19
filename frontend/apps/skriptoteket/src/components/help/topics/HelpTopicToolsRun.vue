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
      <li>Fyll i fälten, ladda upp filer om det behövs och klicka <strong>Kör</strong>.</li>
      <li>
        Medan verktyget arbetar kan du lämna sidan -- körningen fortsätter i
        bakgrunden. Du hittar den igen under <strong>Mina körningar</strong>.
      </li>
      <li>När körningen är klar får du ett resultat du kan ladda ner eller spara i Kassaskåpet.</li>
    </ul>
  </HelpTopicLayout>
</template>
