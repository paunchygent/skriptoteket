<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Skapa konto, glömt lösenord och bekräfta e-post"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>
        Kontohanteringen sker hos HuleEdu. Det är där du skapar konto, byter
        lösenord och bekräftar din e-postadress.
      </li>
      <li>När du är klar skickas du tillbaka till Skriptoteket och kan logga in som vanligt.</li>
      <li>
        Får du inget mejl inom några minuter? Titta i skräpposten och
        kontrollera att du skrev rätt adress.
      </li>
    </ul>
  </HelpTopicLayout>
</template>
