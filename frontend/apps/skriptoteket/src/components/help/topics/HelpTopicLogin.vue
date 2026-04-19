<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Logga in"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>
        Logga in med ditt skolkonto. HuleEdu sköter själva inloggningen och
        skickar dig tillbaka till Skriptoteket när du är klar.
      </li>
      <li>
        Kommer du inte vidare? Gå tillbaka till Skriptotekets startsida och välj
        <strong>Logga in</strong> igen.
      </li>
      <li>Kvarstår problemet, be skolans HuleEdu-kontakt eller support om hjälp.</li>
    </ul>
  </HelpTopicLayout>
</template>
