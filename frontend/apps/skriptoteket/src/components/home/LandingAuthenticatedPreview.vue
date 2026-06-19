<script setup lang="ts">
/**
 * Signed-out landing preview of authenticated Skriptoteket app lanes.
 *
 * This section replaces the retired generic value ledger and repeated
 * Klassrumskartan showcase with the approved three-panel workflow preview
 * while reusing the authenticated-home app symbols and keeping shared HuleEdu
 * auth continuation links for login and registration.
 */

import { computed } from "vue";
import { useRoute } from "vue-router";

import { sharedAuthCeremonyUrl } from "../../api/sharedAuth";
import { resolveLandingAuthContinuation } from "../../composables/auth/authEntryNavigation";
import { HOME_PRIMARY_WORK_APPS } from "./homeWorkApps";

const route = useRoute();

const loginUrl = computed(() => {
  const continuation = resolveLandingAuthContinuation(route);
  return sharedAuthCeremonyUrl({
    nextPath: continuation.nextPath,
    origin: window.location.origin,
  });
});
const registerUrl = computed(() => {
  const continuation = resolveLandingAuthContinuation(route);
  return sharedAuthCeremonyUrl({
    kind: "register",
    nextPath: continuation.nextPath,
    origin: window.location.origin,
  });
});
function getWorkAppSymbol(appId: string): string {
  const app = HOME_PRIMARY_WORK_APPS.find((candidate) => candidate.id === appId);

  if (!app) {
    throw new Error(`Missing work-app symbol for landing preview: ${appId}`);
  }

  return app.imageSrc;
}

const panels = [
  {
    title: "Transkribera tal till text",
    imageSrc: getWorkAppSymbol("audio-transcription"),
  },
  {
    title: "Skapa PDF:er med hjälp av HTML och CSS",
    imageSrc: getWorkAppSymbol("document-converter"),
  },
  {
    title: "Skapa, redigera och konvertera prov",
    imageSrc: getWorkAppSymbol("exam-converter"),
  },
] as const;
</script>

<template>
  <section
    aria-labelledby="landing-authenticated-preview-heading"
    class="py-16 md:py-20"
  >
    <div class="max-w-[42ch]">
      <h2
        id="landing-authenticated-preview-heading"
        class="font-serif text-3xl font-semibold tracking-[-0.02em] text-navy md:text-4xl"
      >
        När du loggar in
      </h2>
      <div
        class="mt-6 h-[2px] w-16 bg-navy"
        aria-hidden="true"
      />
    </div>

    <div class="mt-10 grid divide-y-2 divide-navy border-2 border-navy bg-panel lg:grid-cols-3 lg:divide-x-2 lg:divide-y-0">
      <article
        v-for="panel in panels"
        :key="panel.title"
        class="min-h-[15rem] p-6"
      >
        <div
          aria-hidden="true"
          class="flex min-h-[8.25rem] items-center justify-center border border-navy/40 bg-canvas p-4"
        >
          <img
            :src="panel.imageSrc"
            alt=""
            class="h-auto w-full max-w-[7.25rem] object-contain"
            loading="eager"
            decoding="sync"
            fetchpriority="high"
          >
        </div>
        <h3 class="mt-5 text-base font-semibold leading-[1.35] text-navy">
          {{ panel.title }}
        </h3>
      </article>
    </div>

    <p class="mt-8 text-sm leading-6 text-navy/70">
      <a
        :href="loginUrl"
        class="font-medium text-navy underline decoration-1 underline-offset-3 transition-colors hover:text-action focus-visible:outline focus-visible:outline-2 focus-visible:outline-action/40 focus-visible:outline-offset-2"
      >
        Logga in
      </a>
      ·
      <a
        :href="registerUrl"
        class="font-medium text-navy underline decoration-1 underline-offset-3 transition-colors hover:text-action focus-visible:outline focus-visible:outline-2 focus-visible:outline-action/40 focus-visible:outline-offset-2"
      >
        Skapa konto
      </a>
    </p>
  </section>
</template>
