<script setup lang="ts">
/**
 * Authenticated-only value preview section (ST-32-08, Alternative B).
 *
 * Placed below the featured public-app showcase. Leads with access to more
 * apps and work tools as the primary signed-in value, surfaces that teacher
 * suggestions can become new apps, and keeps saved work (classes, files,
 * settings, classroom placements) as the persistence guarantee. The trailing
 * "Logga in" / "Skapa konto" actions open shared HuleEdu ceremonies directly.
 */

import { computed } from "vue";
import { useRoute } from "vue-router";

import { sharedAuthCeremonyUrl } from "../../api/sharedAuth";
import { resolveLandingAuthContinuation } from "../../composables/auth/authEntryNavigation";

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

const rows = [
  {
    index: "I",
    term: "Fler färdiga lärarverktyg",
    description:
      "Använd alla Skriptotekets appar och verktyg som finns tillgängliga.",
    tag: "Kräver konto",
  },
  {
    index: "II",
    term: "Dina förslag kan bli nya appar",
    description: "Berätta vilka arbetsmoment du vill slippa göra för hand.",
    tag: "Kräver konto",
  },
  {
    index: "III",
    term: "Spara arbetet över tid",
    description:
      "Kom tillbaka till klasser, filer, inställningar och placeringar.",
    tag: "Kräver konto",
  },
] as const;
</script>

<template>
  <section class="py-16 md:py-20">
    <div class="max-w-[42ch]">
      <h2 class="font-serif text-3xl font-semibold tracking-[-0.02em] text-navy md:text-4xl">
        Mer när du loggar in
      </h2>
      <div
        class="mt-6 h-[2px] w-16 bg-navy"
        aria-hidden="true"
      />
      <p class="mt-6 text-base leading-7 text-navy">
        Få tillgång till fler appar och arbetsverktyg. Du kan också ge förslag på nya appar som du
        anser skulle underlätta ditt arbete.
      </p>
    </div>

    <ul class="mt-10 divide-y divide-navy/20 border-y-2 border-navy">
      <li
        v-for="row in rows"
        :key="row.index"
        class="grid grid-cols-[3rem_1fr_auto] items-start gap-6 py-6 md:grid-cols-[4rem_1fr_12rem] md:gap-8"
      >
        <span class="font-mono text-xs font-semibold tracking-wider text-navy/60">
          {{ row.index }}
        </span>
        <div>
          <h3 class="text-base font-semibold text-navy">{{ row.term }}</h3>
          <p class="mt-2 text-sm leading-6 text-navy/70">{{ row.description }}</p>
        </div>
        <span
          class="justify-self-end border border-navy px-3 py-1 font-mono text-[11px] tracking-wider text-navy uppercase"
        >
          {{ row.tag }}
        </span>
      </li>
    </ul>

    <p class="mt-8 text-sm leading-6 text-navy/70">
      <a
        :href="loginUrl"
        class="font-medium text-navy underline decoration-1 underline-offset-3 transition-colors hover:text-burgundy focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2"
      >
        Logga in
      </a>
      ·
      <a
        :href="registerUrl"
        class="font-medium text-navy underline decoration-1 underline-offset-3 transition-colors hover:text-burgundy focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2"
      >
        Skapa konto
      </a>
    </p>
  </section>
</template>
