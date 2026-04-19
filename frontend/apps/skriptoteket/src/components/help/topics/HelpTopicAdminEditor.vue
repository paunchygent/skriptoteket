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
      <li>Här bygger du verktyget: beskrivning, fält, filtyper och själva skriptet som körs.</li>
      <li>
        Testa alltid i <strong>Testkörning</strong> innan du publicerar. Då ser
        du exakt vad användaren kommer att se.
      </li>
      <li>
        Varje sparad version får ett eget nummer. Du kan alltid gå tillbaka till
        en tidigare version om något blir fel.
      </li>
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
