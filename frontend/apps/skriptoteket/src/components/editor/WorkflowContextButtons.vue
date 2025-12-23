<script setup lang="ts">
import { computed } from "vue";

import WorkflowActionsDropdown from "./WorkflowActionsDropdown.vue";

type WorkflowAction = "submit_review" | "publish" | "request_changes" | "rollback";

const props = defineProps<{
  canSubmitReview: boolean;
  canPublish: boolean;
  canRequestChanges: boolean;
  canRollback: boolean;
  isSubmitting: boolean;
}>();

const emit = defineEmits<{
  (e: "action", action: WorkflowAction): void;
}>();

const hasAuthorContext = computed(() => props.canSubmitReview);
const hasAdminContext = computed(() => props.canPublish || props.canRequestChanges);
const showSeparator = computed(() => hasAuthorContext.value || hasAdminContext.value);

function handleDropdownSelect(actionId: string): void {
  emit("action", actionId as WorkflowAction);
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-3">
    <!-- Author Context -->
    <div class="flex items-center gap-2">
      <span class="text-xs font-semibold uppercase tracking-wide text-navy/50">
        Författare
      </span>
      <button
        v-if="canSubmitReview"
        type="button"
        class="px-3 py-2 text-xs font-semibold uppercase tracking-wide bg-navy text-canvas border border-navy shadow-brutal-sm btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="isSubmitting"
        @click="emit('action', 'submit_review')"
      >
        Begär publicering
      </button>
      <span
        v-else
        class="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-navy/30 border border-navy/20 bg-canvas cursor-not-allowed"
      >
        Begär publicering
      </span>
    </div>

    <!-- Separator -->
    <div
      v-if="showSeparator"
      class="h-8 w-px bg-navy/20"
      aria-hidden="true"
    />

    <!-- Admin/Reviewer Context -->
    <div class="flex items-center gap-2">
      <span class="text-xs font-semibold uppercase tracking-wide text-navy/50">
        Granskare
      </span>

      <template v-if="hasAdminContext">
        <button
          v-if="canPublish"
          type="button"
          class="px-3 py-2 text-xs font-semibold uppercase tracking-wide bg-burgundy text-canvas border border-navy shadow-brutal-sm btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="isSubmitting"
          @click="emit('action', 'publish')"
        >
          Publicera
        </button>
        <button
          v-if="canRequestChanges"
          type="button"
          class="px-3 py-2 text-xs font-semibold uppercase tracking-wide bg-white text-navy border border-navy shadow-brutal-sm hover:bg-canvas btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
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
