<script setup lang="ts">
/**
 * Klassrumskartan authenticated guest-upgrade prompt.
 *
 * This component presents the authenticated import decision when a local guest
 * snapshot exists, keeping the entry shell focused on route gating while the
 * prompt owns its own teacher-facing summary and action surface.
 */

import type { ClassroomPlannerGuestUpgradeReceipt } from "./classroomPlannerGuestUpgradeApi";
import type { ClassroomPlannerGuestSnapshotSummary } from "./classroomPlannerGuestSnapshot";

defineProps<{
  summary: ClassroomPlannerGuestSnapshotSummary | null;
  previewReceipt: ClassroomPlannerGuestUpgradeReceipt | null;
  errorMessage: string | null;
}>();

defineEmits<{
  import: [];
  postpone: [];
  discard: [];
}>();
</script>

<template>
  <section class="mx-auto flex max-w-4xl flex-col gap-6 border border-navy bg-white p-6 shadow-brutal-md md:p-8">
    <div class="space-y-3">
      <p class="text-xs font-semibold uppercase tracking-[0.22em] text-burgundy">
        Lokal gästarbetsyta hittad
      </p>
      <div class="space-y-2">
        <h1 class="font-serif text-3xl text-navy md:text-4xl">
          Importera till ditt konto?
        </h1>
        <p class="max-w-2xl text-sm leading-6 text-navy/80 md:text-base">
          Den här webbläsaren har sparad Klassrumskartan-data från gästläget. Du kan
          importera den nu, vänta till senare eller rensa den lokala gästarbetsytan.
        </p>
      </div>
    </div>

    <div
      v-if="errorMessage"
      class="border border-error/30 bg-white px-4 py-3 text-sm text-error"
    >
      {{ errorMessage }}
    </div>

    <dl
      v-if="summary"
      class="grid gap-3 border border-navy/15 bg-canvas p-4 text-sm text-navy/80 md:grid-cols-2"
    >
      <div>
        <dt class="font-semibold text-navy">
          Snapshot-id
        </dt>
        <dd class="break-all font-mono text-xs">
          {{ summary.snapshot_id }}
        </dd>
      </div>
      <div>
        <dt class="font-semibold text-navy">
          Går ut
        </dt>
        <dd>{{ summary.expires_at }}</dd>
      </div>
      <div>
        <dt class="font-semibold text-navy">
          Roster / mallar
        </dt>
        <dd>{{ summary.roster_count }} / {{ summary.template_count }}</dd>
      </div>
      <div>
        <dt class="font-semibold text-navy">
          Regler / checkpoints
        </dt>
        <dd>{{ summary.smart_rule_set_count }} / {{ summary.checkpoint_count }}</dd>
      </div>
      <div>
        <dt class="font-semibold text-navy">
          Grupputkast
        </dt>
        <dd>{{ summary.has_grouping_draft ? "Ja" : "Nej" }}</dd>
      </div>
      <div>
        <dt class="font-semibold text-navy">
          Sittutkast
        </dt>
        <dd>{{ summary.has_seating_draft ? "Ja" : "Nej" }}</dd>
      </div>
    </dl>

    <div
      v-if="previewReceipt"
      class="grid gap-4 md:grid-cols-4"
    >
      <article class="border border-success/30 bg-canvas p-4 shadow-brutal-sm">
        <h2 class="font-serif text-lg text-navy">
          Skapas
        </h2>
        <p class="mt-2 text-2xl text-navy">
          {{ previewReceipt.created.length }}
        </p>
      </article>
      <article class="border border-navy/20 bg-canvas p-4 shadow-brutal-sm">
        <h2 class="font-serif text-lg text-navy">
          Återanvänds
        </h2>
        <p class="mt-2 text-2xl text-navy">
          {{ previewReceipt.reused.length }}
        </p>
      </article>
      <article class="border border-burgundy/20 bg-canvas p-4 shadow-brutal-sm">
        <h2 class="font-serif text-lg text-navy">
          Hoppar över
        </h2>
        <p class="mt-2 text-2xl text-navy">
          {{ previewReceipt.skipped.length }}
        </p>
      </article>
      <article class="border border-error/20 bg-canvas p-4 shadow-brutal-sm">
        <h2 class="font-serif text-lg text-navy">
          Konflikter
        </h2>
        <p class="mt-2 text-2xl text-navy">
          {{ previewReceipt.conflicted.length }}
        </p>
      </article>
    </div>

    <div class="flex flex-wrap gap-3">
      <button
        type="button"
        class="btn-primary"
        @click="$emit('import')"
      >
        Importera nu
      </button>
      <button
        type="button"
        class="btn-ghost"
        @click="$emit('postpone')"
      >
        Inte nu
      </button>
      <button
        type="button"
        class="btn-ghost"
        @click="$emit('discard')"
      >
        Rensa lokal gästarbetsyta
      </button>
    </div>
  </section>
</template>
