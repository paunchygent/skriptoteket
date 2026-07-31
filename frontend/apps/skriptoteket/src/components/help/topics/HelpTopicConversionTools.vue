<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Konvertera material"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Välj eller ladda upp det material som verktyget ska bearbeta.</li>
      <li>Kontrollera inställningarna innan du startar konverteringen.</li>
      <li>Följ statusen och hämta resultatet när bearbetningen är klar.</li>
    </ul>
  </HelpTopicLayout>
</template>
