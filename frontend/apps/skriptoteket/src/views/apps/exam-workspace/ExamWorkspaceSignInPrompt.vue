<script setup lang="ts">
/**
 * Exam workspace guest sign-in prompt.
 *
 * Domain purpose:
 *   The inline notice a guest sees where a signed-in teacher's action needs
 *   an account: the sentence plus a "Logga in" link into the shared auth
 *   ceremony, returning to the signed-in exam workspace. Inline only, never
 *   a toast.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceGuestHost` for a hit guest limit; the next
 *     unit renders it for import and AI gating too.
 *   - Builds the login link with `sharedAuthCeremonyUrl` exactly like the
 *     classroom planner guest view does.
 */

import { computed } from "vue";

import { sharedAuthCeremonyUrl } from "../../../api/sharedAuth";
import { UiGlyph } from "../../../components/ui";

const props = defineProps<{ message: string }>();

const loginUrl = computed(() =>
  sharedAuthCeremonyUrl({
    nextPath: "/apps/exam-workspace",
    origin: window.location.origin,
  }),
);
</script>

<template>
  <div
    class="xw-notice notice xw-notice--info"
    role="status"
    data-test="exam-workspace-sign-in-prompt"
  >
    <UiGlyph
      :meaning="'info'"
      :size="16"
    />
    <span class="xw-grow">{{ props.message }}</span>
    <a
      :href="loginUrl"
      class="font-semibold underline"
      data-test="exam-workspace-sign-in-prompt-login"
    >
      Logga in
    </a>
  </div>
</template>

<style scoped>
.notice { margin-bottom: var(--huleedu-space-3); }
</style>
