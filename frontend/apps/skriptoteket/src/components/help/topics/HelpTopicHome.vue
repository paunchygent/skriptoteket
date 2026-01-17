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
        <strong>Katalog</strong>: hitta verktyg via yrke → kategori → verktyg,
        och kör dem när du behöver.
      </li>
      <li>
        <strong>Kör ett verktyg</strong>: ladda upp fil när verktyget ber om det
        och klicka Kör. Om verktyget behöver fler saker, visas de under resultatet.
      </li>
      <li v-if="canSeeContributor">
        <strong>Mina verktyg</strong>: se och öppna verktyg du underhåller.
      </li>
      <li v-if="canSeeContributor">
        <strong>Föreslå skript</strong>: skicka in idéer och behov (välj yrke/kategori).
      </li>
      <li v-if="canSeeAdmin">
        <strong>Förslag</strong>: granska inkomna förslag och fatta beslut.
      </li>
      <li v-if="canSeeAdmin">
        <strong>Testyta</strong>: publicera/avpublicera och testa verktyg.
      </li>
      <li v-if="canSeeAdmin">
        <strong>Skripteditorn</strong>: redigera skript och spara versioner.
      </li>
    </ul>
  </HelpTopicLayout>
</template>
