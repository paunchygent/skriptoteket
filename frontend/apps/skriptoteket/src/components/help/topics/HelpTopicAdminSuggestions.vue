<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Förslag (admin)"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>
        Här hanterar du inkomna förslag. Öppna ett förslag för att läsa det i
        sin helhet och sätta ett beslut.
      </li>
      <li>
        Statusarna betyder: <strong>nytt</strong> -- oöppnat,
        <strong>under översyn</strong> -- någon tittar på det,
        <strong>godkänt</strong> -- ska byggas,
        <strong>avvisat</strong> -- byggs inte just nu.
      </li>
      <li>Skriv alltid en kort motivering vid beslutet. Det är den texten användaren ser.</li>
    </ul>
  </HelpTopicLayout>
</template>
