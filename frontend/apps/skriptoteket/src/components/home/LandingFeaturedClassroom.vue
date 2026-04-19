<script setup lang="ts">
/**
 * Featured public-app showcase for Klassrumskartan.
 *
 * Asymmetric two-column band placed below the signed-out hero. Left column
 * carries copy and a quiet text-link CTA; right column carries one
 * outer-bordered three-step strip with internally divided columns (not three
 * separate cards) so the showcase reads as a single product surface.
 */

import stepCreateRoomUrl from "../../assets/home/klassrumskartan/landing/redesign-v5/step-01-skapa-salen.svg?no-inline";
import stepPlaceStudentsUrl from "../../assets/home/klassrumskartan/landing/redesign-v5/step-02-placera-eleverna.svg?no-inline";
import stepExportUrl from "../../assets/home/klassrumskartan/landing/redesign-v5/step-03-exportera.svg?no-inline";

const publicClassroomPlannerPath = "/public/apps/classroom.group-seating-studio";

const steps = [
  { index: "I", title: "Skapa salen", imageSrc: stepCreateRoomUrl },
  { index: "II", title: "Placera eleverna", imageSrc: stepPlaceStudentsUrl },
  { index: "III", title: "Exportera", imageSrc: stepExportUrl },
] as const;
</script>

<template>
  <section class="border-b border-navy py-16 md:py-20">
    <div class="grid grid-cols-1 items-start gap-12 lg:grid-cols-[5fr_7fr] lg:gap-16">
      <div class="max-w-[42ch]">
        <h2 class="font-serif text-3xl font-semibold tracking-[-0.02em] text-navy md:text-4xl">
          Klassrumskartan
        </h2>
        <div
          class="mt-6 h-[2px] w-16 bg-navy"
          aria-hidden="true"
        />
        <p class="mt-6 text-base leading-7 text-navy">
          Skapa salen, placera eleverna, spara som PDF eller för Excel. Som inloggad är alla dina
          klasser, grupperingar och klassrumsplaceringar sparade.
        </p>
        <RouterLink
          :to="publicClassroomPlannerPath"
          class="mt-6 inline-flex items-center gap-2 font-medium text-navy underline decoration-1 underline-offset-3 transition-colors hover:text-burgundy focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2"
        >
          Öppna appen
          <span aria-hidden="true">→</span>
        </RouterLink>
      </div>

      <div
        class="grid grid-cols-1 divide-y-2 divide-navy border-2 border-navy md:grid-cols-3 md:divide-x-2 md:divide-y-0"
        aria-label="Tre steg i Klassrumskartan"
      >
        <article
          v-for="step in steps"
          :key="step.index"
          class="flex min-h-[14rem] flex-col gap-4 p-6"
        >
          <p class="font-mono text-xs font-semibold tracking-wider text-navy/60">
            {{ step.index }}
          </p>
          <h3 class="text-base font-semibold text-navy">{{ step.title }}</h3>
          <div
            class="mt-2 flex flex-1 items-center justify-center border border-navy/40 bg-canvas p-3"
            aria-hidden="true"
          >
            <img
              :src="step.imageSrc"
              alt=""
              width="100"
              height="60"
              class="w-full max-w-[10rem]"
            >
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
