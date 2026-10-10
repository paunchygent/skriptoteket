<script setup lang="ts">
/**
 * Exam workspace item details drawer.
 *
 * Domain purpose:
 *   Hold the selected question's metadata outside the editor: what stops
 *   its export or save, why it needs review, the open answer-key proposal,
 *   and how the question was read from the source file. The teacher opens
 *   it from the editor's "Detaljer" toggle; the view also opens it when a
 *   proposal waits.
 *
 * Presentation by layout:
 *   - desktop: a column beside the editor; focus stays where it was.
 *   - tablet: a panel laid over the editor's right edge; focus moves into
 *     it, Escape from inside it closes it, and focus returns on close.
 *   - phone: a full-screen modal dialog; focus moves into it, Tab stays
 *     inside it, Escape closes it, and focus returns on close.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` with the current layout.
 *   - Keyboard and focus handling comes from `useExamWorkspaceDialogFocus`.
 *   - Embeds `ExamWorkspaceProposalPanel` and re-emits its intents.
 */

import { computed, ref, useId } from "vue";

import { IconX } from "../../../components/icons";
import type { NativeExamItem, NativeExamParseOrigin } from "../../../api/examWorkspace";
import ExamWorkspaceProposalPanel from "./ExamWorkspaceProposalPanel.vue";
import { examWorkspaceReviewReasonLabel } from "./examWorkspaceRows";
import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";
import { useExamWorkspaceDialogFocus } from "./useExamWorkspaceDialogFocus";

const PARSE_ORIGIN_LABELS: Record<NativeExamParseOrigin, string> = {
  deterministic: "Läst direkt ur provfilen.",
  llm_parsed: "Tolkad med AI ur provfilen.",
  teacher_created: "Skapad i provredigeringen.",
};

const props = defineProps<{
  disabled: boolean;
  item: NativeExamItem;
  layout: ExamWorkspaceLayout;
  proposedItem: NativeExamItem | null;
  readiness: string[];
  serverBlockers: string[];
}>();

const emit = defineEmits<{
  approve: [itemId: string];
  close: [];
  dismiss: [itemId: string];
  edit: [itemId: string];
}>();

const FRAME_CLASS: Record<ExamWorkspaceLayout, string> = {
  desktop: "min-h-0 w-[22rem] shrink-0 overflow-y-auto border-l border-navy/20",
  phone: "fixed inset-0 z-50 overflow-y-auto bg-panel outline-none",
  tablet:
    "absolute inset-y-0 right-0 z-10 w-[min(22rem,90%)] overflow-y-auto border-l border-navy bg-panel shadow-brutal-sm outline-none",
};

const frame = ref<HTMLElement | null>(null);
const titleId = useId();
const isModal = computed(() => props.layout === "phone");

useExamWorkspaceDialogFocus(frame, {
  modal: () => isModal.value,
  onClose: () => emit("close"),
  takesFocus: () => props.layout !== "desktop",
});
</script>

<template>
  <div
    ref="frame"
    :class="FRAME_CLASS[layout]"
    :role="isModal ? 'dialog' : undefined"
    :aria-modal="isModal ? 'true' : undefined"
    :aria-labelledby="isModal ? titleId : undefined"
    :tabindex="layout === 'desktop' ? undefined : -1"
    data-test="exam-workspace-item-drawer-frame"
  >
    <aside
      class="grid content-start gap-5 bg-panel p-4 text-navy"
      :aria-labelledby="titleId"
      data-test="exam-workspace-item-drawer"
    >
      <header class="flex items-center justify-between gap-3">
        <h3
          :id="titleId"
          class="text-sm font-semibold leading-tight"
        >
          Detaljer – fråga {{ item.sequence }}
        </h3>
        <button
          type="button"
          class="inline-flex h-9 w-9 items-center justify-center border border-navy/35 bg-panel hover:bg-canvas"
          aria-label="Stäng detaljer"
          data-test="exam-workspace-item-drawer-close"
          @click="emit('close')"
        >
          <IconX
            :size="16"
            class="h-4 w-4"
            aria-hidden="true"
          />
        </button>
      </header>

      <ExamWorkspaceProposalPanel
        v-if="proposedItem"
        :disabled="disabled"
        :item="item"
        :proposed-item="proposedItem"
        @approve="emit('approve', $event)"
        @dismiss="emit('dismiss', $event)"
        @edit="emit('edit', $event)"
      />

      <section class="grid gap-2">
        <h4 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          Före export
        </h4>
        <ul
          v-if="readiness.length > 0 || serverBlockers.length > 0"
          class="grid gap-1 text-sm leading-snug"
          data-test="exam-workspace-item-readiness"
        >
          <li
            v-for="reason in [...new Set([...serverBlockers, ...readiness])]"
            :key="reason"
            class="border-l-4 border-warning pl-2"
          >
            {{ reason }}
          </li>
        </ul>
        <p
          v-else
          class="border-l-4 border-success pl-2 text-sm leading-snug"
          data-test="exam-workspace-item-ready"
        >
          Frågan är klar för export.
        </p>
      </section>

      <section
        v-if="item.review.reasons.length > 0"
        class="grid gap-2"
      >
        <h4 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          Att granska
        </h4>
        <ul
          class="grid gap-1 text-sm leading-snug text-navy/80"
          data-test="exam-workspace-review-reasons"
        >
          <li
            v-for="reason in item.review.reasons"
            :key="reason"
          >
            {{ examWorkspaceReviewReasonLabel(reason) }}
          </li>
        </ul>
      </section>

      <section class="grid gap-1">
        <h4 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          Källa
        </h4>
        <p class="text-sm leading-snug text-navy/80">
          {{ PARSE_ORIGIN_LABELS[item.review.parse_origin] }}
        </p>
      </section>
    </aside>
  </div>
</template>
