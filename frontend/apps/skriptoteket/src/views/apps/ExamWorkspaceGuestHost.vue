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
 *   A stored draft the app cannot read shows the shared file notice with
 *   download or remove instead of the editor; only the explicit remove
 *   deletes it. Every sign-in exit first departs through the guest view
 *   under its held editing lock, so signing in never abandons the working
 *   copy before its autosave; a failed departure keeps the guest view
 *   mounted with the inline failure copy.
 *
 * Relationships:
 *   - Mounted by `curatedAppHostRegistry` for the public
 *     documents.conversion_hub entry.
 *   - Renders `ExamWorkspaceView` with the guest store, like
 *     `ExamWorkspaceTeacherHost` does with the server store.
 */

import { onMounted, ref, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import * as publicExamWorkspaceApi from "../../api/publicExamWorkspace";
import { useToast } from "../../composables/useToast";
import { useAuthStore } from "../../stores/auth";
import { triggerBrowserDownload } from "../../utils/browserDownload";
import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import ExamWorkspaceFileNotice from "./exam-workspace/ExamWorkspaceFileNotice.vue";
import {
  GUEST_BROWSER_ONLY_NOTICE,
  GUEST_LIMIT_SIGN_IN,
} from "./exam-workspace/examWorkspaceGuestCopy";
import { buildGuestDraftArchive } from "./exam-workspace/examWorkspaceGuestDraftArchive";
import { isGuestDraftReadable } from "./exam-workspace/examWorkspaceGuestDraftReadability";
import {
  createExamWorkspaceGuestDraftStorage,
  type StoredGuestDraft,
} from "./exam-workspace/examWorkspaceGuestDraftStorage";
import { createGuestExamWorkspaceStore } from "./exam-workspace/examWorkspaceGuestStore";
import { EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY } from "./exam-workspace/examWorkspaceFileNoticeCopy";
import { EXAM_WORKSPACE_DEPARTURE_FAILURE_COPY } from "./exam-workspace/examWorkspaceSignIn";
import ExamWorkspaceSignInPrompt from "./exam-workspace/ExamWorkspaceSignInPrompt.vue";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const toast = useToast();

const limitReached = ref(false);
/** The stored draft the app cannot open, held for download or explicit removal. */
const unreadableStored = shallowRef<StoredGuestDraft | null>(null);
/** True while the unreadable draft's zip is built or its record is removed. */
const recoveryBusy = ref(false);
const guestStorage = createExamWorkspaceGuestDraftStorage();

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
    const stored = await guestStorage.load();
    if (stored && stored.draft.lineage_id === lineageId && !isGuestDraftReadable(stored.draft)) {
      unreadableStored.value = stored;
    }
  }
});

/**
 * Save the unreadable draft as the same zip the signed-in guest download
 * saves. The stored record stays untouched; nothing is retried.
 */
async function downloadUnreadableDraft(): Promise<void> {
  const held = unreadableStored.value;
  if (held === null || recoveryBusy.value) {
    return;
  }
  recoveryBusy.value = true;
  try {
    const current = await guestStorage.load();
    if (current?.draft.cursor !== held.draft.cursor) {
      toast.failure(EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY);
      return;
    }
    const archive = await buildGuestDraftArchive(current);
    triggerBrowserDownload(archive.blob, archive.filename);
  } catch {
    toast.failure(EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY);
  } finally {
    recoveryBusy.value = false;
  }
}

/**
 * Delete the unreadable draft and its pictures from IndexedDB on the
 * explicit click, then show the normal empty guest start: the notice
 * clears, the document address clears, and the view mounts with no draft.
 */
async function removeUnreadableDraft(): Promise<void> {
  const held = unreadableStored.value;
  if (held === null || recoveryBusy.value) {
    return;
  }
  recoveryBusy.value = true;
  try {
    await guestStorage.clearIf(held.draft.cursor);
  } catch {
    recoveryBusy.value = false;
    return;
  }
  recoveryBusy.value = false;
  unreadableStored.value = null;
  await router.replace({ query: { ...route.query, document: undefined } });
}
</script>

<template>
  <div
    class="guest-host"
    data-test="exam-workspace-guest-host"
  >
    <div
      v-if="unreadableStored === null"
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
    <ExamWorkspaceFileNotice
      v-if="unreadableStored !== null"
      reason="guest_unreadable"
      :busy="recoveryBusy"
      @download="downloadUnreadableDraft()"
      @remove="removeUnreadableDraft()"
    />
    <ExamWorkspaceView
      v-if="!leaving && unreadableStored === null"
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
