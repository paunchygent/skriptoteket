<script setup lang="ts">
import { computed } from "vue";
import { UiDenseActionButton } from "../ui";
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
        <UiDenseActionButton
          label="Begär publicering"
          :disabled="isSubmitting"
          @click="emit('action', 'submit_review')"
        />
        <div
          v-if="hasSubmitReviewTooltip"
          class="absolute left-0 top-full mt-2 w-[min(260px,calc(100vw-2*var(--huleedu-space-4)))] border border-navy/20 bg-modal shadow-md text-navy px-3 py-2 text-xs opacity-0 pointer-events-none transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 z-[var(--huleedu-z-tooltip)]"
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
      <UiDenseActionButton
        v-else
        label="Begär publicering"
        disabled
      />
    </div>

    <!-- Admin/Reviewer Context -->
    <div
      class="flex items-center gap-2"
      title="Granskare"
    >
      <template v-if="hasAdminContext">
        <UiDenseActionButton
          v-if="canPublish"
          label="Publicera"
          :disabled="isSubmitting"
          @click="emit('action', 'publish')"
        />
        <UiDenseActionButton
          v-if="canRequestChanges"
          label="Avslå"
          tone="danger"
          :disabled="isSubmitting"
          @click="emit('action', 'request_changes')"
        />
      </template>
      <template v-else>
        <UiDenseActionButton
          label="Publicera"
          disabled
        />
        <UiDenseActionButton
          label="Avslå"
          tone="danger"
          disabled
        />
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
