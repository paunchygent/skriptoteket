<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Sidan hittades inte"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Adressen leder inte någonstans just nu. Kanske har länken blivit gammal, eller så har något flyttats.</li>
      <li>Prova att gå till startsidan och leta dig fram därifrån, eller använd sökfältet.</li>
      <li>
        Kom du hit via en länk från någon annan? Hör av dig till den som delade
        länken -- den behöver förmodligen uppdateras.
      </li>
    </ul>
  </HelpTopicLayout>
</template>
