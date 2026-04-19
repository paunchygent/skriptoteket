<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Kontot behöver aktiveras"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Inloggningen gick bra, men ditt konto är inte fullt aktiverat i Skriptoteket ännu.</li>
      <li>Oftast löser det sig av sig själv inom några minuter. Ladda om sidan och försök igen.</li>
      <li>
        Om problemen kvarstår: kontakta din skoladministratör eller be support
        om hjälp. Ange din e-postadress när du hör av dig -- det gör det snabbare
        att ta reda på var det fastnat.
      </li>
    </ul>
  </HelpTopicLayout>
</template>
