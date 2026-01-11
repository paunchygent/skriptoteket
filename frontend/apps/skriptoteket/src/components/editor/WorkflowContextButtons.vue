<script setup lang="ts">
import { computed } from "vue";
import type { SubmitReviewTooltip } from "../../composables/editor/useEditorWorkflowActions";

import WorkflowActionsDropdown from "./WorkflowActionsDropdown.vue";

type WorkflowAction = "submit_review" | "publish" | "request_changes" | "rollback";

const props = defineProps<{
  canSubmitReview: boolean;
  submitReviewTooltip: SubmitReviewTooltip | null;
  canPublish: boolean;
  canRequestChanges: boolean;
  canRollback: boolean;
  isSubmitting: boolean;
}>();

const emit = defineEmits<{
  (e: "action", action: WorkflowAction): void;
}>();

const hasAdminContext = computed(() => props.canPublish || props.canRequestChanges);
const hasSubmitReviewTooltip = computed(() => Boolean(props.submitReviewTooltip));

const actionButtonClass =
  "btn-ghost shadow-none bg-canvas h-[28px] px-2.5 py-1 text-[10px] font-semibold tracking-[var(--huleedu-tracking-label)] w-[140px] justify-center border-navy/30 whitespace-nowrap leading-none";
const disabledButtonClass =
  "inline-flex items-center justify-center h-[28px] w-[140px] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] border border-navy/20 bg-canvas text-navy/30 cursor-not-allowed whitespace-nowrap leading-none";

function handleDropdownSelect(actionId: string): void {
  emit("action", actionId as WorkflowAction);
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <!-- Author Context -->
    <div
      class="flex items-center gap-2"
      title="Författare"
    >
      <div
        v-if="canSubmitReview"
        class="relative group"
      >
        <button
          type="button"
          :class="actionButtonClass"
          :disabled="isSubmitting"
          @click="emit('action', 'submit_review')"
        >
          Begär publicering
        </button>
        <div
          v-if="hasSubmitReviewTooltip"
          class="absolute left-0 top-full mt-2 w-[min(260px,calc(100vw-2*var(--huleedu-space-4)))] border border-navy bg-white text-navy px-3 py-2 text-xs opacity-0 pointer-events-none transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 z-[var(--huleedu-z-tooltip)]"
          role="tooltip"
        >
          <div class="text-[0.65rem] font-semibold uppercase tracking-wide text-navy/70">
            {{ submitReviewTooltip?.title }}
          </div>
          <p
            v-if="submitReviewTooltip?.description"
            class="mt-2 text-xs text-navy/70"
          >
            {{ submitReviewTooltip?.description }}
          </p>
          <ul
            v-else-if="submitReviewTooltip?.items?.length"
            class="mt-2 space-y-1 text-xs text-navy/70"
          >
            <li
              v-for="item in submitReviewTooltip?.items"
              :key="item"
              class="leading-snug"
            >
              - {{ item }}
            </li>
          </ul>
        </div>
      </div>
      <span
        v-else
        :class="disabledButtonClass"
      >
        Begär publicering
      </span>
    </div>

    <!-- Admin/Reviewer Context -->
    <div
      class="flex items-center gap-2"
      title="Granskare"
    >
      <template v-if="hasAdminContext">
        <button
          v-if="canPublish"
          type="button"
          :class="actionButtonClass"
          :disabled="isSubmitting"
          @click="emit('action', 'publish')"
        >
          Publicera
        </button>
        <button
          v-if="canRequestChanges"
          type="button"
          :class="[actionButtonClass, 'text-burgundy']"
          :disabled="isSubmitting"
          @click="emit('action', 'request_changes')"
        >
          Avslå
        </button>
      </template>
      <template v-else>
        <span :class="disabledButtonClass">
          Publicera
        </span>
        <span :class="disabledButtonClass">
          Avslå
        </span>
      </template>

      <!-- Overflow menu for rollback -->
      <WorkflowActionsDropdown
        v-if="canRollback"
        :items="[{ id: 'rollback', label: 'Återställ', tone: 'danger' }]"
        label="⋮"
        @select="handleDropdownSelect"
      />
    </div>
  </div>
</template>
