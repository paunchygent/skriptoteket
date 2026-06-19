<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Resultat"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>
        Här ser du vad verktyget gjorde och det som blev resultatet. Filer kan
        laddas ner direkt eller sparas i Mina filer.
      </li>
      <li>Gick något fel visar vi ett begripligt meddelande om vad som hände och vad du kan prova.</li>
      <li>Behöver du köra om med samma inställningar klickar du <strong>Kör igen</strong>.</li>
    </ul>
  </HelpTopicLayout>
</template>
