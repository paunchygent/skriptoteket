<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Skripteditorn"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Spara som utkast, testkör och granska resultatet.</li>
      <li>När du är nöjd: skicka för granskning och publicera.</li>
      <li>
        <strong>Krav för begäran</strong>: URL-namnet får inte börja med
        <span class="font-mono">draft-</span> och minst ett yrke + en kategori
        måste vara valda.
      </li>
      <li>
        Ändra URL-namn och sökord under <strong>Metadata</strong>-panelen.
      </li>
    </ul>
  </HelpTopicLayout>
</template>
