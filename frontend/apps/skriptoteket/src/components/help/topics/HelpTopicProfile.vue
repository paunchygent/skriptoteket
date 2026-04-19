<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Min profil"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Här ser du vilket konto du är inloggad med och vilka roller du har i Skriptoteket.</li>
      <li>Namn och e-post kommer från HuleEdu och ändras där -- inte här.</li>
      <li>Inställningar som språk och aviseringar styr du på den här sidan.</li>
    </ul>
  </HelpTopicLayout>
</template>
