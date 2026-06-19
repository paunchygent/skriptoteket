<script setup lang="ts">
import { computed } from "vue";

import { useAuthStore } from "../../../stores/auth";
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const auth = useAuthStore();
const { showIndex } = useHelp();

const canSeeContributor = computed(() => auth.hasAtLeastRole("contributor"));
const canSeeAdmin = computed(() => auth.hasAtLeastRole("admin"));
</script>

<template>
  <HelpTopicLayout
    title="Start"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>
        Start samlar arbetsappar, filer, katalog och de bidrags- eller
        adminvyer du har behörighet till.
      </li>
      <li>
        <strong>Katalog</strong> innehåller tillgängliga verktyg och appar.
        <strong>Mina filer</strong> samlar sparade filer och exporter.
      </li>
      <li>
        Om en genväg eller sektion saknas beror det oftast på din roll eller på
        att du inte är inloggad.
      </li>
      <li v-if="canSeeContributor">
        <strong>Bidra</strong>: syns bara om du får föreslå eller bygga verktyg.
      </li>
      <li v-if="canSeeAdmin">
        <strong>Admin</strong>: syns bara om du har en administratörsroll.
      </li>
    </ul>
  </HelpTopicLayout>
</template>
