<script setup lang="ts">
/**
 * Exam workspace guest sign-in bar.
 *
 * Domain purpose:
 *   The one row a guest sees above the workspace when a signed-in action
 *   needs an account: the sign-in prompt with its "Logga in" link plus the
 *   "Stäng" dismiss button. Dismissing only hides the row.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` while its guest sign-in prompt is set;
 *     the prompt state lives in `useExamWorkspaceGuestSignIn`.
 */

import ExamWorkspaceSignInPrompt from "./ExamWorkspaceSignInPrompt.vue";

const props = defineProps<{
  /** Settle the pending edit into browser storage; true when it is safe to leave. */
  depart: () => Promise<boolean>;
  /** The guest sign-in message the prompt renders. */
  message: string;
}>();

const emit = defineEmits<{
  /** The guest dismissed the prompt without signing in. */
  dismiss: [];
}>();
</script>

<template>
  <div
    class="ws__bar ws__signin"
  >
    <ExamWorkspaceSignInPrompt
      :depart="props.depart"
      :message="props.message"
    />
    <button
      type="button"
      class="xw-btn xw-btn--compact"
      data-test="exam-workspace-sign-in-prompt-dismiss"
      @click="emit('dismiss')"
    >
      Stäng
    </button>
  </div>
</template>
