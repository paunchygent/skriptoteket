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
import ExamWorkspaceSignInPrompt from "./exam-workspace/ExamWorkspaceSignInPrompt.vue";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const limitReached = ref(false);

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

watch(
  () => authStore.isAuthenticated,
  (signedIn) => {
    if (signedIn) {
      sendSignedInVisitorToWorkspace();
    }
  },
);

onMounted(async () => {
  if (authStore.isAuthenticated) {
    sendSignedInVisitorToWorkspace();
    return;
  }
  const lineageId = await guestStore.currentLineageId();
  if (lineageId) {
    await router.replace({ query: { ...route.query, document: lineageId } });
  }
});
</script>

<template>
  <div data-test="exam-workspace-guest-host">
    <div
      class="xw-notice notice xw-notice--info"
      role="status"
      data-test="exam-workspace-guest-browser-notice"
    >
      {{ GUEST_BROWSER_ONLY_NOTICE }}
    </div>
    <ExamWorkspaceSignInPrompt
      v-if="limitReached"
      :message="GUEST_LIMIT_SIGN_IN"
    />
    <ExamWorkspaceView
      v-if="!authStore.isAuthenticated"
      :store="guestStore.store"
    />
  </div>
</template>

<style scoped>
.notice { margin-bottom: var(--huleedu-space-3); }
</style>
