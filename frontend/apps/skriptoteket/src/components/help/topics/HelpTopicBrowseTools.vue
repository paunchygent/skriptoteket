<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Katalog: verktyg och appar"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>
        Klicka <strong>Öppna</strong> för en app eller <strong>Kör</strong> för ett
        verktyg.
      </li>
      <li>Om inget finns ännu: prova en annan kategori.</li>
    </ul>
  </HelpTopicLayout>
</template>
