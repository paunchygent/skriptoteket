<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Katalog: välj yrke"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>
        Här hittar du verktyg och appar sorterade efter yrke. Välj det som
        ligger närmast ditt uppdrag -- du kan alltid gå tillbaka.
      </li>
      <li>Varje yrke leder vidare till de kategorier som är relevanta för just det arbetet.</li>
      <li>Letar du efter något särskilt? Använd sökfältet i toppen.</li>
    </ul>
  </HelpTopicLayout>
</template>
