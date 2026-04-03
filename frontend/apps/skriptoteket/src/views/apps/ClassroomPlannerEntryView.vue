<script setup lang="ts">
/**
 * Klassrumskartan entry shell.
 *
 * This wrapper lets the authenticated and public curated-app host routes share
 * one app-specific shell contract while the public browser-workspace behavior
 * is implemented in later EPIC-32 slices.
 */

import { computed } from "vue";
import { RouterLink } from "vue-router";

import { useLoginModal } from "../../composables/useLoginModal";
import { CLASSROOM_PLANNER_APP_ID } from "./classroomPlannerNavigation";
import ClassroomPlannerView from "./ClassroomPlannerView.vue";

const props = withDefaults(
  defineProps<{
    hostMode?: "authenticated" | "public";
  }>(),
  {
    hostMode: "authenticated",
  },
);

const authenticatedRoute = computed(() => `/apps/${encodeURIComponent(CLASSROOM_PLANNER_APP_ID)}`);
const loginModal = useLoginModal();

function openLoginModal(): void {
  loginModal.open(authenticatedRoute.value);
}
</script>

<template>
  <ClassroomPlannerView v-if="props.hostMode === 'authenticated'" />

  <section
    v-else
    class="mx-auto flex max-w-4xl flex-col gap-6 border border-navy bg-white p-6 shadow-brutal-md md:p-8"
  >
    <div class="space-y-3">
      <p class="text-xs font-semibold uppercase tracking-[0.22em] text-burgundy">
        Publik apphost
      </p>
      <div class="space-y-2">
        <h1 class="font-serif text-3xl text-navy md:text-4xl">
          Klassrumskartan
        </h1>
        <p class="max-w-2xl text-sm leading-6 text-navy/80 md:text-base">
          Den separata publika värdytan är nu på plats. I den här första bounded slice landar den
          godkända host- och bootstrap-gränsen, medan browser-ägd gästarbetsyta, publik import,
          export och inloggad uppgradering följer i senare EPIC-32-steg.
        </p>
      </div>
    </div>

    <div class="grid gap-4 md:grid-cols-2">
      <article class="border border-navy/20 bg-canvas p-4 shadow-brutal-sm">
        <h2 class="font-serif text-xl text-navy">
          Det här är klart nu
        </h2>
        <p class="mt-2 text-sm leading-6 text-navy/80">
          Klassrumskartan kan nu ha en dedikerad publik route och publik bootstrap utan att
          försvaga den befintliga autentiserade hosten eller de ägarstyrda API-sömmarna.
        </p>
      </article>

      <article class="border border-navy/20 bg-canvas p-4 shadow-brutal-sm">
        <h2 class="font-serif text-xl text-navy">
          Nästa steg i demo-paketet
        </h2>
        <p class="mt-2 text-sm leading-6 text-navy/80">
          Gästläge för roster, mallar, smarta regler, lokala snapshots och senare inloggad import
          är medvetet utanför just den här implementeringsslicen.
        </p>
      </article>
    </div>

    <div class="flex flex-wrap gap-3">
      <button
        type="button"
        class="btn-primary"
        @click="openLoginModal"
      >
        Logga in till full version
      </button>
      <RouterLink
        to="/register"
        class="btn-ghost"
      >
        Skapa konto
      </RouterLink>
    </div>
  </section>
</template>
