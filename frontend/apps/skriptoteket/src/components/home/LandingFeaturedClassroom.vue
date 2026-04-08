<script setup lang="ts">
/**
 * Featured public-app showcase for Klassrumskartan.
 *
 * Asymmetric two-column band placed below the signed-out hero. Left column
 * carries copy and a quiet text-link CTA; right column carries one
 * outer-bordered three-step strip with internally divided columns (not three
 * separate cards) so the showcase reads as a single product surface.
 */

const publicClassroomPlannerPath = "/public/apps/classroom.group-seating-studio";

const steps = [
  { index: "01", title: "Skapa salen" },
  { index: "02", title: "Placera eleverna" },
  { index: "03", title: "Exportera" },
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
          Skapa salen, placera eleverna, spara som PDF. Allt i webbläsaren.
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
            <svg
              v-if="step.index === '01'"
              viewBox="0 0 100 60"
              class="w-full max-w-[10rem]"
            >
              <rect
                x="2"
                y="2"
                width="96"
                height="56"
                fill="none"
                stroke="#1c2e4a"
                stroke-width="2"
              />
              <rect
                x="14"
                y="10"
                width="22"
                height="8"
                fill="rgba(28,46,74,0.10)"
                stroke="#1c2e4a"
                stroke-width="1.5"
              />
              <rect
                x="64"
                y="10"
                width="22"
                height="8"
                fill="rgba(28,46,74,0.10)"
                stroke="#1c2e4a"
                stroke-width="1.5"
              />
            </svg>
            <svg
              v-else-if="step.index === '02'"
              viewBox="0 0 100 60"
              class="w-full max-w-[10rem]"
            >
              <rect
                x="2"
                y="2"
                width="96"
                height="56"
                fill="none"
                stroke="#1c2e4a"
                stroke-width="2"
              />
              <rect
                x="12"
                y="22"
                width="14"
                height="10"
                fill="#fafaf6"
                stroke="#1c2e4a"
                stroke-width="1.5"
              />
              <rect
                x="30"
                y="22"
                width="14"
                height="10"
                fill="#fafaf6"
                stroke="#1c2e4a"
                stroke-width="1.5"
              />
              <rect
                x="48"
                y="22"
                width="14"
                height="10"
                fill="#fafaf6"
                stroke="#1c2e4a"
                stroke-width="1.5"
              />
              <rect
                x="66"
                y="22"
                width="14"
                height="10"
                fill="#fafaf6"
                stroke="#1c2e4a"
                stroke-width="1.5"
              />
              <rect
                x="12"
                y="40"
                width="14"
                height="10"
                fill="#fafaf6"
                stroke="#1c2e4a"
                stroke-width="1.5"
              />
              <rect
                x="30"
                y="40"
                width="14"
                height="10"
                fill="#fafaf6"
                stroke="#1c2e4a"
                stroke-width="1.5"
              />
              <rect
                x="48"
                y="40"
                width="14"
                height="10"
                fill="#fafaf6"
                stroke="#1c2e4a"
                stroke-width="1.5"
              />
              <rect
                x="66"
                y="40"
                width="14"
                height="10"
                fill="#fafaf6"
                stroke="#1c2e4a"
                stroke-width="1.5"
              />
            </svg>
            <svg
              v-else
              viewBox="0 0 100 60"
              class="w-full max-w-[10rem]"
            >
              <rect
                x="20"
                y="8"
                width="40"
                height="44"
                fill="#fafaf6"
                stroke="#1c2e4a"
                stroke-width="2"
              />
              <line
                x1="26"
                y1="20"
                x2="54"
                y2="20"
                stroke="#1c2e4a"
                stroke-width="1.5"
              />
              <line
                x1="26"
                y1="28"
                x2="54"
                y2="28"
                stroke="#1c2e4a"
                stroke-width="1.5"
              />
              <line
                x1="26"
                y1="36"
                x2="48"
                y2="36"
                stroke="#1c2e4a"
                stroke-width="1.5"
              />
              <text
                x="78"
                y="38"
                font-family="IBM Plex Mono, monospace"
                font-size="11"
                font-weight="700"
                fill="#1c2e4a"
              >PDF</text>
            </svg>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
