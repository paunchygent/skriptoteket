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

const hasAdminContext = computed(() => props.canPublish || props.canRequestChanges);

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
      <button
        v-if="canSubmitReview"
        type="button"
        class="btn-primary px-3 py-2 text-xs font-semibold tracking-wide"
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
