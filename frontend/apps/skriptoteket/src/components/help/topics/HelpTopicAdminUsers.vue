<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Administrera användare"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Här ser du användare i Skriptoteket och vilka roller de har lokalt hos oss.</li>
      <li>Rollen bestämmer vad användaren får göra -- inte vem hen är.</li>
      <li>Identitet och inloggning sköts av HuleEdu.</li>
      <li>Ändringar slår igenom nästa gång användaren laddar om sidan.</li>
    </ul>
  </HelpTopicLayout>
</template>
