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

function handleDropdownSelect(actionId: string): void {
  emit("action", actionId as WorkflowAction);
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-3 w-full">
    <!-- Author Context -->
    <div class="flex items-center gap-2">
      <span class="text-xs font-semibold uppercase tracking-wide text-navy/50">
        Författare
      </span>
      <div
        v-if="canSubmitReview"
        class="relative group"
      >
        <button
          type="button"
          class="btn-primary px-3 py-2 text-xs font-semibold tracking-wide"
          :disabled="isSubmitting"
          @click="emit('action', 'submit_review')"
        >
          Begär publicering
        </button>
        <div
          v-if="hasSubmitReviewTooltip"
          class="absolute left-0 top-full mt-2 w-[min(260px,calc(100vw-2*var(--huleedu-space-4)))] border border-navy bg-white text-navy shadow-brutal-sm px-3 py-2 text-xs opacity-0 pointer-events-none transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
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
        class="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-navy/30 border border-navy/20 bg-canvas cursor-not-allowed"
      >
        Begär publicering
      </span>
    </div>

    <!-- Admin/Reviewer Context -->
    <div class="flex items-center gap-2 md:ml-auto">
      <span class="text-xs font-semibold uppercase tracking-wide text-navy/50">
        Granskare
      </span>

      <template v-if="hasAdminContext">
        <button
          v-if="canPublish"
          type="button"
          class="btn-cta px-3 py-2 text-xs font-semibold tracking-wide"
          :disabled="isSubmitting"
          @click="emit('action', 'publish')"
        >
          Publicera
        </button>
        <button
          v-if="canRequestChanges"
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          :disabled="isSubmitting"
          @click="emit('action', 'request_changes')"
        >
          Avslå
        </button>
      </template>
      <template v-else>
        <span class="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-navy/30 border border-navy/20 bg-canvas cursor-not-allowed">
          Publicera
        </span>
        <span class="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-navy/30 border border-navy/20 bg-canvas cursor-not-allowed">
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
