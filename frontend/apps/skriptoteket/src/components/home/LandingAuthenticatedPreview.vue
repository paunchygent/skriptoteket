<script setup lang="ts">
/**
 * Authenticated-only value preview ledger.
 *
 * Quiet bordered list placed below the featured public-app showcase. Each row
 * carries an explicit "Kräver konto" / "Kräver ansökan" tag so visitors do not
 * mistake an authenticated capability for another public route. The trailing
 * "Logga in" action routes through the shared `/auth/login` handoff.
 */

import { useRoute, useRouter } from "vue-router";

import { buildLandingAuthEntryLocation } from "../../composables/auth/authEntryNavigation";

const route = useRoute();
const router = useRouter();

const rows = [
  {
    index: "01",
    term: "Spara dina inställningar och filer",
    description:
      "Behåll dina val och dokument mellan besök, så att du hittar tillbaka till dem.",
    tag: "Kräver konto",
  },
  {
    index: "02",
    term: "Bygg egna verktyg i kodredigeraren",
    description:
      "Skriv egna små appar i Skriptoteket. Åtkomsten ansöker du om efter registreringen.",
    tag: "Kräver ansökan",
  },
] as const;

async function goToAuthEntry(): Promise<void> {
  await router.push(buildLandingAuthEntryLocation(route));
}
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
        Logga in om du vill spara dina inställningar och filer. Du kan också ansöka om att bygga
        egna verktyg i kodredigeraren.
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
      <button
        type="button"
        class="font-medium text-navy underline decoration-1 underline-offset-3 transition-colors hover:text-burgundy focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2"
        @click="void goToAuthEntry()"
      >
        Logga in
      </button>
      ·
      <RouterLink
        to="/register"
        class="font-medium text-navy underline decoration-1 underline-offset-3 transition-colors hover:text-burgundy focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2"
      >
        Skapa konto
      </RouterLink>
    </p>
  </section>
</template>
