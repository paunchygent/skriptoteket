<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Hantera verktyg"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>
        Listan visar alla verktyg i Skriptoteket. Härifrån publicerar,
        avpublicerar och redigerar du dem.
      </li>
      <li>
        <strong>Publicera</strong> gör verktyget synligt för alla användare som
        har rätt roll. <strong>Avpublicera</strong> döljer det igen -- befintliga
        körningar påverkas inte.
      </li>
      <li>Ta bort ett verktyg bara om det verkligen inte ska finnas kvar. Körhistorik följer med.</li>
    </ul>
  </HelpTopicLayout>
</template>
