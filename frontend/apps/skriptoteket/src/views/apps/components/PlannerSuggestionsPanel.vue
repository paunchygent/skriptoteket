<script setup lang="ts">
/**
 * Planner controls, findings, and suggestion panel.
 *
 * This component collects the authoritative backend-driven planning actions:
 * validate, generate suggestions, randomize, and finalize. It also shows
 * autosave/conflict state and snapshot history so teachers can trust what is
 * currently persisted before committing a final arrangement.
 */

import { onMounted, ref } from "vue";

import { planningProfileLabels } from "../classroomPlannerTypes";
import { useClassroomState } from "../useClassroomState";

const state = useClassroomState();

const isValidating = ref(false);
const isLoadingSuggestions = ref(false);
const isRandomizing = ref(false);
const isFinalizing = ref(false);
const actionMessage = ref<string | null>(null);

onMounted(() => {
  void state.loadSnapshots().catch(() => undefined);
});

async function runValidate(): Promise<void> {
  isValidating.value = true;
  actionMessage.value = null;
  try {
    await state.validateDraft();
  } finally {
    isValidating.value = false;
  }
}

async function runSuggestions(): Promise<void> {
  isLoadingSuggestions.value = true;
  actionMessage.value = null;
  try {
    await state.loadSuggestions();
  } finally {
    isLoadingSuggestions.value = false;
  }
}

async function runRandomize(): Promise<void> {
  isRandomizing.value = true;
  actionMessage.value = null;
  try {
    await state.randomizeDraft();
    actionMessage.value = "Slumpa placerade om eleverna och uppdaterade utkastet.";
  } finally {
    isRandomizing.value = false;
  }
}

async function runFinalize(): Promise<void> {
  isFinalizing.value = true;
  actionMessage.value = null;
  try {
    const snapshot = await state.finalizeDraft();
    actionMessage.value = `Planeringen fastställdes i snapshot ${snapshot.id.slice(0, 8)}.`;
  } finally {
    isFinalizing.value = false;
  }
}
</script>

<template>
  <div class="space-y-4">
    <section class="border border-navy bg-white p-4 shadow-brutal-sm">
      <div class="flex flex-col gap-3 border-b border-navy/20 pb-3">
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Motor och status
          </p>
          <h3 class="font-serif text-xl text-navy">
            Assisterad planering
          </h3>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="btn-primary"
            :disabled="isValidating"
            @click="runValidate"
          >
            {{ isValidating ? "Validerar..." : "Validera" }}
          </button>
          <button
            type="button"
            class="btn-primary"
            :disabled="isLoadingSuggestions"
            @click="runSuggestions"
          >
            {{ isLoadingSuggestions ? "Beräknar..." : "Hämta förslag" }}
          </button>
          <button
            type="button"
            class="btn-ghost border-navy/30 bg-canvas shadow-none"
            :disabled="isRandomizing"
            @click="runRandomize"
          >
            {{ isRandomizing ? "Slumpar..." : "Slumpa" }}
          </button>
          <button
            type="button"
            class="btn-cta"
            :disabled="isFinalizing"
            @click="runFinalize"
          >
            {{ isFinalizing ? "Fastställer..." : "Fastställ snapshot" }}
          </button>
        </div>
      </div>

      <div class="mt-4 space-y-3">
        <div class="border border-navy/20 bg-canvas px-3 py-2 text-sm text-navy">
          <span class="font-semibold">Sparstatus:</span>
          {{ state.saveStatus }}
          <span v-if="state.saveMessage"> · {{ state.saveMessage }}</span>
        </div>
        <div
          v-if="state.draft?.engine_metadata"
          class="border border-navy/20 bg-white px-3 py-2 text-sm text-navy/80"
        >
          <span class="font-semibold">Senast tillämpat förslag:</span>
          {{ state.draft.engine_metadata.suggestion_id }}
          <span class="text-navy/60">
            ({{ planningProfileLabels[state.draft.engine_metadata.profile_kind] }})
          </span>
        </div>
        <div
          v-if="actionMessage"
          class="system-message system-message-success"
        >
          <div class="system-message-content">
            {{ actionMessage }}
          </div>
        </div>
      </div>
    </section>

    <section class="border border-navy bg-white p-4 shadow-brutal-sm">
      <div class="flex items-end justify-between gap-3 border-b border-navy/20 pb-3">
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Validering
          </p>
          <h3 class="font-serif text-xl text-navy">
            Fynd
          </h3>
        </div>
        <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          {{ state.validationFindings.length }} totalt
        </span>
      </div>

      <div class="mt-4 space-y-2">
        <div
          v-if="state.validationFindings.length === 0"
          class="border border-dashed border-navy/30 bg-canvas px-3 py-4 text-sm text-navy/60"
        >
          Kör validering för att se hårda blockerare och mjuka varningar.
        </div>
        <div
          v-for="finding in state.validationFindings"
          :key="`${finding.code}-${finding.subject_ref ?? 'none'}`"
          class="border px-3 py-3"
          :class="finding.severity === 'hard' ? 'border-burgundy bg-burgundy/10 text-burgundy' : 'border-warning bg-warning/10 text-navy'"
        >
          <div class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)]">
            {{ finding.severity }} · {{ finding.code }}
          </div>
          <div class="mt-1 text-sm font-semibold">
            {{ finding.message }}
          </div>
          <div class="mt-1 text-sm leading-relaxed opacity-80">
            {{ finding.explanation }}
          </div>
        </div>
      </div>
    </section>

    <section class="border border-navy bg-white p-4 shadow-brutal-sm">
      <div class="flex items-end justify-between gap-3 border-b border-navy/20 pb-3">
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Förslag
          </p>
          <h3 class="font-serif text-xl text-navy">
            Fördelningar
          </h3>
        </div>
        <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          {{ state.suggestions.length }} profiler
        </span>
      </div>

      <div class="mt-4 space-y-3">
        <div
          v-if="state.suggestions.length === 0"
          class="border border-dashed border-navy/30 bg-canvas px-3 py-4 text-sm text-navy/60"
        >
          Hämta förslag för att jämföra fokus-, balans- och rotationsprofiler.
        </div>

        <article
          v-for="suggestion in state.suggestions"
          :key="suggestion.suggestion_id"
          class="space-y-3 border border-navy/20 bg-canvas p-3"
        >
          <div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
            <div>
              <h4 class="text-base font-semibold text-navy">
                {{ suggestion.label }}
              </h4>
              <p class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                {{ planningProfileLabels[suggestion.profile_kind] }}
              </p>
            </div>
            <button
              type="button"
              class="btn-primary"
              @click="state.applySuggestion(suggestion.suggestion_id)"
            >
              Tillämpa
            </button>
          </div>

          <div class="grid gap-2 md:grid-cols-2">
            <div
              v-for="(score, key) in suggestion.score_breakdown"
              :key="key"
              class="border border-navy/20 bg-white px-3 py-2 text-sm text-navy"
            >
              <span class="font-semibold">{{ key }}:</span> {{ score.toFixed(2) }}
            </div>
          </div>

          <ul class="space-y-1 text-sm leading-relaxed text-navy/80">
            <li
              v-for="bullet in suggestion.explanation_bullets"
              :key="bullet"
            >
              {{ bullet }}
            </li>
          </ul>
        </article>
      </div>
    </section>

    <section class="border border-navy bg-white p-4 shadow-brutal-sm">
      <div class="flex items-end justify-between gap-3 border-b border-navy/20 pb-3">
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Historik
          </p>
          <h3 class="font-serif text-xl text-navy">
            Snapshots
          </h3>
        </div>
        <button
          type="button"
          class="btn-ghost border-navy/30 bg-canvas shadow-none"
          @click="state.loadSnapshots()"
        >
          Uppdatera
        </button>
      </div>

      <div class="mt-4 space-y-2">
        <div
          v-if="state.snapshots.length === 0"
          class="border border-dashed border-navy/30 bg-canvas px-3 py-4 text-sm text-navy/60"
        >
          Inga snapshots ännu.
        </div>
        <div
          v-for="snapshot in state.snapshots"
          :key="snapshot.id"
          class="border border-navy/20 bg-canvas px-3 py-3 text-sm text-navy"
        >
          <div class="font-semibold">
            Snapshot {{ snapshot.id.slice(0, 8) }}
          </div>
          <div class="mt-1 text-navy/60">
            {{ snapshot.lesson_mode_id }} · {{ new Date(snapshot.created_at).toLocaleString('sv-SE') }}
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
