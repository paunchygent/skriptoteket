<script setup lang="ts">
/**
 * Exam workspace guest sign-in prompt.
 *
 * Domain purpose:
 *   The inline notice a guest sees where a signed-in teacher's action needs
 *   an account: the sentence plus a "Logga in" link into the shared auth
 *   ceremony, returning to the signed-in exam workspace. Inline only, never
 *   a toast. Following the link first settles the pending edit into browser
 *   storage through the `depart` prop, so signing in never abandons the
 *   working copy before its autosave; a failed settle stays and shows the
 *   inline failure copy instead of navigating.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceGuestHost` for a hit guest limit; the next
 *     unit renders it for import and AI gating too.
 *   - Builds the login link with `sharedAuthCeremonyUrl` exactly like the
 *     classroom planner guest view does.
 */

import { computed, ref } from "vue";

import { sharedAuthCeremonyUrl } from "../../../api/sharedAuth";
import { redirectToSharedAuthCeremony } from "../../../composables/auth/sharedAuthRedirect";
import { UiGlyph } from "../../../components/ui";
import { EXAM_WORKSPACE_DEPARTURE_FAILURE_COPY } from "./examWorkspaceSignIn";

const props = defineProps<{
  /** Settle the pending edit into browser storage; true when it is safe to leave. */
  depart: () => Promise<boolean>;
  message: string;
}>();

const loginUrl = computed(() =>
  sharedAuthCeremonyUrl({
    nextPath: "/apps/exam-workspace",
    origin: window.location.origin,
  }),
);

/** Leaving the working copy behind can abandon it before its autosave. */
const settleFailed = ref(false);

async function followLogin(event: Event): Promise<void> {
  event.preventDefault();
  settleFailed.value = false;
  const settled = await props.depart();
  if (settled) {
    redirectToSharedAuthCeremony(loginUrl.value);
  } else {
    settleFailed.value = true;
  }
}
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
      @click="followLogin"
    >
      Logga in
    </a>
    <p
      v-if="settleFailed"
      class="xw-grow"
      data-test="exam-workspace-sign-in-prompt-error"
    >
      {{ EXAM_WORKSPACE_DEPARTURE_FAILURE_COPY }}
    </p>
  </div>
</template>

<style scoped>
.notice { margin-bottom: var(--huleedu-space-3); }
</style>
