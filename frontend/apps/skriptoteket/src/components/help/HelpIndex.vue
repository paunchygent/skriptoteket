<script setup lang="ts">
import { computed } from "vue";

import { useAuthStore } from "../../stores/auth";
import { type HelpTopicId, useHelp } from "./useHelp";

type IndexItem = {
  topic: HelpTopicId;
  title: string;
  description?: string;
};

const auth = useAuthStore();
const { showTopic } = useHelp();

const isAuthenticated = computed(() => auth.isAuthenticated);
const canSeeContributor = computed(() => auth.hasAtLeastRole("contributor"));
const canSeeAdmin = computed(() => auth.hasAtLeastRole("admin"));

const starterIndexItems: IndexItem[] = [
  {
    topic: "home",
    title: "Start",
    description: "Se vad du har tillgång till.",
  },
  {
    topic: "browse_professions",
    title: "Katalog",
    description: "Hitta verktyg via yrke → kategori.",
  },
  {
    topic: "tools_run",
    title: "Kör ett verktyg",
    description: "Ladda upp fil och klicka Kör.",
  },
];

const contributorIndexItems: IndexItem[] = [
  {
    topic: "my_tools",
    title: "Mina verktyg",
    description: "Öppna verktyg du underhåller.",
  },
  {
    topic: "suggestions_new",
    title: "Föreslå skript",
    description: "Skicka in idéer och behov.",
  },
];

const adminIndexItems: IndexItem[] = [
  {
    topic: "admin_suggestions",
    title: "Förslag",
    description: "Granska och fatta beslut.",
  },
  {
    topic: "admin_tools",
    title: "Testyta",
    description: "Publicera/avpublicera och testa.",
  },
  {
    topic: "admin_editor",
    title: "Skripteditorn",
    description: "Redigera skript och versioner.",
  },
];

const loggedOutIndexItems: IndexItem[] = [
  {
    topic: "login",
    title: "Logga in",
  },
];
</script>

<template>
  <div class="space-y-6">
    <div class="space-y-3">
      <h3 class="text-lg font-semibold text-navy">Hjälpindex</h3>
      <p
        v-if="!isAuthenticated"
        class="text-sm text-navy/60"
      >
        Välj ett ämne för att komma igång.
      </p>
    </div>

    <div
      v-if="isAuthenticated"
      class="space-y-6"
    >
      <section class="space-y-3">
        <h4 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          Kom igång
        </h4>
        <ul class="border border-navy/20 bg-white shadow-brutal-sm divide-y divide-navy/20">
          <li
            v-for="item in starterIndexItems"
            :key="item.topic"
          >
            <button
              type="button"
              class="w-full text-left flex items-start justify-between gap-4 px-4 py-3 hover:bg-canvas transition-colors"
              @click="showTopic(item.topic)"
            >
              <span class="flex flex-col gap-1">
                <span class="text-sm font-semibold text-navy">{{ item.title }}</span>
                <span class="text-xs text-navy/60">{{ item.description }}</span>
              </span>
              <span class="text-navy/40">→</span>
            </button>
          </li>
        </ul>
      </section>

      <section
        v-if="canSeeContributor"
        class="space-y-3"
      >
        <h4 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          Bidra
        </h4>
        <ul class="border border-navy/20 bg-white shadow-brutal-sm divide-y divide-navy/20">
          <li
            v-for="item in contributorIndexItems"
            :key="item.topic"
          >
            <button
              type="button"
              class="w-full text-left flex items-start justify-between gap-4 px-4 py-3 hover:bg-canvas transition-colors"
              @click="showTopic(item.topic)"
            >
              <span class="flex flex-col gap-1">
                <span class="text-sm font-semibold text-navy">{{ item.title }}</span>
                <span class="text-xs text-navy/60">{{ item.description }}</span>
              </span>
              <span class="text-navy/40">→</span>
            </button>
          </li>
        </ul>
      </section>

      <section
        v-if="canSeeAdmin"
        class="space-y-3"
      >
        <h4 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          Admin
        </h4>
        <ul class="border border-navy/20 bg-white shadow-brutal-sm divide-y divide-navy/20">
          <li
            v-for="item in adminIndexItems"
            :key="item.topic"
          >
            <button
              type="button"
              class="w-full text-left flex items-start justify-between gap-4 px-4 py-3 hover:bg-canvas transition-colors"
              @click="showTopic(item.topic)"
            >
              <span class="flex flex-col gap-1">
                <span class="text-sm font-semibold text-navy">{{ item.title }}</span>
                <span class="text-xs text-navy/60">{{ item.description }}</span>
              </span>
              <span class="text-navy/40">→</span>
            </button>
          </li>
        </ul>
      </section>
    </div>

    <section
      v-else
      class="space-y-3"
    >
      <ul class="border border-navy/20 bg-white shadow-brutal-sm divide-y divide-navy/20">
        <li
          v-for="item in loggedOutIndexItems"
          :key="item.topic"
        >
          <button
            type="button"
            class="w-full text-left flex items-center justify-between gap-4 px-4 py-3 hover:bg-canvas transition-colors"
            @click="showTopic(item.topic)"
          >
            <span class="text-sm font-semibold text-navy">{{ item.title }}</span>
            <span class="text-navy/40">→</span>
          </button>
        </li>
      </ul>
    </section>
  </div>
</template>
