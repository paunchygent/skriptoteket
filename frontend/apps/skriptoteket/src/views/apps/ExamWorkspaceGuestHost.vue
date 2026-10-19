<script setup lang="ts">
/**
 * Guest exam workspace host.
 *
 * Domain purpose:
 *   The public exam-converter URL mounts the same exam workspace a teacher
 *   uses, running on the browser guest store: the exam lives only in this
 *   browser, a stored draft reopens through the view's `?document=` address,
 *   and a hit guest limit surfaces the sign-in prompt. A signed-in visitor
 *   is sent to the signed-in workspace, which hands the draft off there.
 *   Every sign-in exit first departs through the guest view under its held
 *   editing lock, so signing in never abandons the working copy
 *   before its autosave; a failed departure keeps the guest view mounted with
 *   the inline failure copy.
 *
 * Relationships:
 *   - Mounted by `curatedAppHostRegistry` for the public
 *     documents.conversion_hub entry.
 *   - Renders `ExamWorkspaceView` with the guest store, like
 *     `ExamWorkspaceTeacherHost` does with the server store.
 */

import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import * as publicExamWorkspaceApi from "../../api/publicExamWorkspace";
import { useAuthStore } from "../../stores/auth";
import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import {
  GUEST_BROWSER_ONLY_NOTICE,
  GUEST_LIMIT_SIGN_IN,
} from "./exam-workspace/examWorkspaceGuestCopy";
import { createExamWorkspaceGuestDraftStorage } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import { createGuestExamWorkspaceStore } from "./exam-workspace/examWorkspaceGuestStore";
import { EXAM_WORKSPACE_DEPARTURE_FAILURE_COPY } from "./exam-workspace/examWorkspaceSignIn";
import ExamWorkspaceSignInPrompt from "./exam-workspace/ExamWorkspaceSignInPrompt.vue";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const limitReached = ref(false);
/** True once the guest view has safely settled and left for the signed-in workspace. */
const leaving = ref(false);
/** The pending edit could not be settled, so the guest view stays mounted. */
const departureFailed = ref(false);
const viewRef = ref<{
  depart: (leave: () => boolean | Promise<boolean>) => Promise<boolean>;
} | null>(null);

const guestStore = createGuestExamWorkspaceStore({
  api: publicExamWorkspaceApi,
  ids: {
    now: () => new Date().toISOString(),
    uuid: () => crypto.randomUUID(),
  },
  onLimit: () => {
    limitReached.value = true;
  },
  storage: createExamWorkspaceGuestDraftStorage(),
});

function sendSignedInVisitorToWorkspace(): void {
  void router.replace({ name: "exam-workspace" });
}

/**
 * Depart through the guest view under its held editing lock, so an in-place
 * sign-in never abandons the working copy before its autosave. With no
 * mounted view `leave` runs directly.
 */
async function departThroughView(
  leave: () => boolean | Promise<boolean>,
): Promise<boolean> {
  const view = viewRef.value;
  if (!view) {
    try {
      return await leave();
    } catch {
      return false;
    }
  }
  return view.depart(leave);
}

/** Leave for the signed-in workspace only after the working copy is stored. */
async function leaveForWorkspace(): Promise<void> {
  const left = await departThroughView(() => {
    departureFailed.value = false;
    leaving.value = true;
    sendSignedInVisitorToWorkspace();
    return true;
  });
  if (!left) {
    departureFailed.value = true;
  }
}

watch(
  () => authStore.isAuthenticated,
  (signedIn) => {
    if (signedIn) {
      void leaveForWorkspace();
    }
  },
);

onMounted(async () => {
  if (authStore.isAuthenticated) {
    await leaveForWorkspace();
    return;
  }
  const lineageId = await guestStore.currentLineageId();
  if (lineageId) {
    await router.replace({ query: { ...route.query, document: lineageId } });
  }
});
</script>

<template>
  <div
    class="guest-host"
    data-test="exam-workspace-guest-host"
  >
    <div
      class="xw-notice notice xw-notice--info"
      role="status"
      data-test="exam-workspace-guest-browser-notice"
    >
      {{ GUEST_BROWSER_ONLY_NOTICE }}
    </div>
    <ExamWorkspaceSignInPrompt
      v-if="limitReached"
      :depart="departThroughView"
      :message="GUEST_LIMIT_SIGN_IN"
    />
    <p
      v-if="departureFailed"
      class="xw-notice notice xw-notice--error"
      role="status"
      data-test="exam-workspace-guest-departure-error"
    >
      {{ EXAM_WORKSPACE_DEPARTURE_FAILURE_COPY }}
    </p>
    <ExamWorkspaceView
      v-if="!leaving"
      ref="viewRef"
      :store="guestStore.store"
    />
  </div>
</template>

<style scoped>
.guest-host { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.guest-host > .notice { flex: none; }
.notice { margin-bottom: var(--huleedu-space-3); }
</style>
