<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Åtkomst saknas"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Den här sidan kräver en roll eller behörighet som ditt konto inte har just nu.</li>
      <li>
        Det är inget fel på dig -- det kan handla om att du behöver tilldelas en
        roll eller logga in med rätt konto.
      </li>
      <li>Vet du inte vem du ska fråga? Börja med din skoladministratör.</li>
    </ul>
  </HelpTopicLayout>
</template>
