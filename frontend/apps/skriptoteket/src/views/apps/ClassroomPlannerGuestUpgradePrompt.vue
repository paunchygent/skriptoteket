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

const props = defineProps<{
  summary: ClassroomPlannerGuestSnapshotSummary | null;
  previewReceipt: ClassroomPlannerGuestUpgradeReceipt | null;
  errorMessage: string | null;
}>();

defineEmits<{
  import: [];
  postpone: [];
  discard: [];
}>();

function formatCount(count: number, singular: string, plural: string): string | null {
  if (count <= 0) {
    return null;
  }
  return `${count} ${count === 1 ? singular : plural}`;
}

function joinHumanList(parts: string[]): string {
  if (parts.length === 0) {
    return "";
  }
  if (parts.length === 1) {
    return parts[0];
  }
  if (parts.length === 2) {
    return `${parts[0]} och ${parts[1]}`;
  }
  return `${parts.slice(0, -1).join(", ")} och ${parts.at(-1)}`;
}

function buildSummaryLine(summary: ClassroomPlannerGuestSnapshotSummary | null): string {
  if (!summary) {
    return "Tidigare arbete finns att föra över till ditt konto.";
  }

  const parts = [
    formatCount(summary.roster_count, "klass", "klasser"),
    formatCount(summary.template_count, "klassrum", "klassrum"),
    summary.smart_rule_set_count > 0 ? "regler" : null,
    formatCount(
      Number(summary.has_grouping_draft) + Number(summary.has_seating_draft),
      "utkast",
      "utkast",
    ),
  ].filter((part): part is string => part !== null);

  if (parts.length === 0) {
    return "Tidigare arbete finns att föra över till ditt konto.";
  }

  return `${joinHumanList(parts)} finns att föra över till ditt konto.`;
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-navy/35 p-4 backdrop-blur-[1px]"
    role="dialog"
    aria-modal="true"
    aria-labelledby="guest-upgrade-title"
    data-test="guest-upgrade-modal"
  >
    <section class="w-full max-w-[34rem] border border-navy bg-modal p-6 shadow-brutal-md md:p-7">
      <div class="space-y-3">
        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-terracotta">
          Arbete från gästläge hittat
        </p>
        <div class="space-y-2">
          <h1
            id="guest-upgrade-title"
            class="font-serif text-3xl text-navy"
          >
            Vill du importera det?
          </h1>
          <p
            data-test="guest-upgrade-summary-line"
            class="text-base leading-7 text-navy/78"
          >
            {{ buildSummaryLine(props.summary) }}
          </p>
        </div>
      </div>

      <p
        v-if="errorMessage"
        data-test="guest-upgrade-error-message"
        class="mt-4 text-sm leading-6 text-critical"
      >
        {{ errorMessage }}
      </p>

      <div class="mt-8 flex flex-wrap items-center gap-3">
        <button
          type="button"
          class="btn-primary"
          data-test="guest-upgrade-import-button"
          @click="$emit('import')"
        >
          Importera
        </button>
        <button
          type="button"
          class="btn-ghost"
          data-test="guest-upgrade-postpone-button"
          @click="$emit('postpone')"
        >
          Inte nu
        </button>
        <button
          type="button"
          class="btn-ghost text-critical"
          data-test="guest-upgrade-discard-button"
          @click="$emit('discard')"
        >
          Kasta
        </button>
      </div>
    </section>
  </div>
</template>
