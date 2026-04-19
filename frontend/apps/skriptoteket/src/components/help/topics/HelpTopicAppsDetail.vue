<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import { useAuthStore } from "../../../stores/auth";
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
const route = useRoute();
const auth = useAuthStore();

const isPublicAppRoute = computed(() => route.name === "public-app-detail");
const isAuthenticated = computed(() => auth.isAuthenticated);
</script>

<template>
  <HelpTopicLayout
    title="App"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>
        Appar är större arbetsytor, som Klassrumskartan, där du jobbar i flera
        steg inuti själva appen.
      </li>

      <template v-if="isPublicAppRoute">
        <li>
          Detta är en fullständig förhandsvisning av vad Klassrumskartan gör. Du
          kan prova arbetsytan direkt i webbläsaren.
        </li>
        <li v-if="isAuthenticated">
          Den publika versionen används utan konto. Öppna den inloggade appen om
          du vill spara och fortsätta arbetet mellan besök.
        </li>
        <li v-else>
          Logga in för att spara ditt arbete och kunna fortsätta där du slutade
          nästa gång.
        </li>
        <li>
          Om appen säger att du ska logga in beror det på att den här webbläsaren
          redan har använt Klassrumskartan med konto.
        </li>
      </template>

      <template v-else>
        <li>Klicka på appen för att öppna arbetsytan.</li>
        <li>
          När du är inloggad sparas arbetet i appen, så att du kan fortsätta där
          du slutade nästa gång.
        </li>
      </template>
    </ul>
  </HelpTopicLayout>
</template>
