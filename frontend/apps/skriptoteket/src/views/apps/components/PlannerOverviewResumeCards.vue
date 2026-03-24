<script setup lang="ts">
/**
 * Overview resumable draft cards.
 *
 * This component renders the compact overview-owned continue/dismiss cards for
 * grouping and seating. It stays presentation-focused so the parent overview
 * shell owns draft visibility and modal orchestration.
 */

import { computed } from "vue";

import { IconSettings, IconX } from "../../../components/icons";
import type { PlanDraftSummary, RoomTemplate } from "../classroomPlannerTypes";

const props = defineProps<{
  visibleGroupingDraft: PlanDraftSummary | null;
  visibleSeatingDraft: PlanDraftSummary | null;
  visibleSeatingDraftTemplate: RoomTemplate | null;
}>();

const emit = defineEmits<{
  (e: "open-grouping"): void;
  (e: "open-seating", templateId: string | null): void;
  (e: "edit-roster"): void;
  (e: "edit-current-template", template: RoomTemplate): void;
  (e: "dismiss-grouping-draft"): void;
  (e: "dismiss-seating-draft"): void;
}>();

const hasVisibleDrafts = computed(() => {
  return props.visibleGroupingDraft !== null || props.visibleSeatingDraft !== null;
});

function describeGroupingDraft(draft: PlanDraftSummary): string {
  if (draft.template_name) {
    return `${draft.template_name} · Revision ${draft.revision}`;
  }
  return `Utan klassrum · Revision ${draft.revision}`;
}

function describeSeatingDraft(draft: PlanDraftSummary): string {
  if (draft.template_name) {
    return `${draft.template_name} · Revision ${draft.revision}`;
  }
  return `Välj klassrum för att fortsätta · Revision ${draft.revision}`;
}
</script>

<template>
  <section
    v-if="hasVisibleDrafts"
    class="grid gap-3 xl:grid-cols-2"
    data-test="overview-resumable-surface"
  >
    <article
      v-if="visibleGroupingDraft"
      class="relative space-y-3 border border-navy/20 bg-white p-4 shadow-brutal-sm"
      data-test="overview-grouping-resume-card"
    >
      <button
        type="button"
        class="absolute right-3 top-3 text-navy/45 transition-colors hover:text-navy"
        aria-label="Stäng fortsätt grupper"
        data-test="dismiss-grouping-resume"
        @click="emit('dismiss-grouping-draft')"
      >
        <IconX :size="16" />
      </button>

      <div class="space-y-1 pr-8">
        <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          Grupper
        </p>
        <h3 class="font-serif text-xl text-navy">
          Fortsätt grupper
        </h3>
        <p class="text-sm text-navy/70">
          {{ describeGroupingDraft(visibleGroupingDraft) }}
        </p>
      </div>

      <div class="flex items-center gap-2">
        <button
          type="button"
          class="btn-primary justify-center"
          data-test="continue-grouping-draft"
          @click="emit('open-grouping')"
        >
          Fortsätt grupper
        </button>
        <button
          type="button"
          class="inline-flex h-10 items-center justify-center rounded-none border border-navy/20 bg-white px-3 text-navy transition-colors hover:border-navy/35 hover:bg-canvas"
          aria-label="Inställningar för grupper"
          data-test="grouping-draft-settings"
          @click="emit('edit-roster')"
        >
          <IconSettings :size="16" />
        </button>
      </div>
    </article>

    <article
      v-if="visibleSeatingDraft"
      class="relative space-y-3 border border-navy/20 bg-white p-4 shadow-brutal-sm"
      data-test="overview-seating-resume-card"
    >
      <button
        type="button"
        class="absolute right-3 top-3 text-navy/45 transition-colors hover:text-navy"
        aria-label="Stäng fortsätt sittschema"
        data-test="dismiss-seating-resume"
        @click="emit('dismiss-seating-draft')"
      >
        <IconX :size="16" />
      </button>

      <div class="space-y-1 pr-8">
        <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          Sittplatser
        </p>
        <h3 class="font-serif text-xl text-navy">
          Fortsätt sittschema
        </h3>
        <p class="text-sm text-navy/70">
          {{ describeSeatingDraft(visibleSeatingDraft) }}
        </p>
      </div>

      <div class="flex items-center gap-2">
        <button
          type="button"
          class="btn-primary justify-center"
          data-test="continue-seating-draft"
          @click="emit('open-seating', visibleSeatingDraft.template_id ?? null)"
        >
          Fortsätt sittschema
        </button>
        <button
          type="button"
          class="inline-flex h-10 items-center justify-center rounded-none border border-navy/20 bg-white px-3 text-navy transition-colors hover:border-navy/35 hover:bg-canvas"
          aria-label="Inställningar för sittplatser"
          data-test="seating-draft-settings"
          :disabled="!visibleSeatingDraftTemplate"
          @click="visibleSeatingDraftTemplate ? emit('edit-current-template', visibleSeatingDraftTemplate) : undefined"
        >
          <IconSettings :size="16" />
        </button>
      </div>
    </article>
  </section>
</template>
