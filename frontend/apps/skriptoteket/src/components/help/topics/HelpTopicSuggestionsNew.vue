<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Föreslå ett nytt verktyg"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Saknar du ett verktyg? Beskriv det här så tar vi en titt.</li>
      <li>
        Var konkret om vad du vill kunna göra och i vilket sammanhang -- det gör
        det mycket lättare att bedöma och bygga.
      </li>
      <li>När du skickar in förslaget får du en bekräftelse direkt på sidan.</li>
    </ul>
  </HelpTopicLayout>
</template>
