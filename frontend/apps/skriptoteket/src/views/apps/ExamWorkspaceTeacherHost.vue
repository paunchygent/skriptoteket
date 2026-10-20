<script setup lang="ts">
/**
 * Signed-in exam workspace host.
 *
 * Domain purpose:
 *   Mount the exam workspace on the signed-in store, which delegates every
 *   server call to the transport modules. A guest host mounts the same view
 *   on a browser store instead. A browser draft left behind by a guest is
 *   handed off to Mina filer once on mount through the handoff controller;
 *   the view renders only after the first attempt settles, and a successful
 *   first handoff points the route at the handed-off lineage before the view
 *   mounts, so the view opens the handed-off exam. A draft Mina filer
 *   refused for good leaves a file notice above the view with glyph actions
 *   (download, remove, and for a full Mina filer retry); transient failures
 *   toast and retry in the background.
 *
 * Relationships:
 *   - Mounted by the `/apps/exam-workspace` route and the curated app host.
 *   - Renders `ExamWorkspaceView` with `serverExamWorkspaceStore`.
 *   - Runs the stored guest draft through `useExamWorkspaceGuestHandoffController`
 *     before the view opens the exam named by `?document=<lineage_id>`, and
 *     renders `ExamWorkspaceFileNotice` above the view while the
 *     controller holds a rejection, mapping `permanent` to the
 *     refused-draft reason, `unreadable` to the older-format reason and
 *     `vault_full` to the full-Mina-filer reason.
 */

import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import ExamWorkspaceFileNotice from "./exam-workspace/ExamWorkspaceFileNotice.vue";
import { createExamWorkspaceGuestDraftStorage } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import { createWebGuestHandoffLock } from "./exam-workspace/examWorkspaceGuestHandoffLock";
import { createLocalStorageGuestHandoffRejectionStorage } from "./exam-workspace/examWorkspaceGuestHandoffRejection";
import { serverExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import { useExamWorkspaceGuestHandoffController } from "./exam-workspace/useExamWorkspaceGuestHandoffController";

const route = useRoute();
const router = useRouter();

const handoff = useExamWorkspaceGuestHandoffController({
  lock: createWebGuestHandoffLock(),
  rejections: createLocalStorageGuestHandoffRejectionStorage(),
  storage: createExamWorkspaceGuestDraftStorage(),
  teacher: serverExamWorkspaceStore.teacher,
});
const handoffSettled = ref(false);

/**
 * Map the controller's handoff reason to the shared file notice reason: an
 * outdated-format refusal shows the older-format sentence with the same
 * download and remove, every other permanent refusal the refused-draft
 * sentence, and a full Mina filer the vault sentence.
 */
const noticeReason = computed(() => {
  const reason = handoff.notice.value?.reason;
  if (reason === "vault_full") {
    return "guest_vault_full";
  }
  if (reason === "unreadable") {
    return "guest_unreadable";
  }
  return "guest_permanent";
});

onMounted(async () => {
  try {
    const lineageId = await handoff.start();
    if (lineageId) {
      await router.replace({ query: { ...route.query, document: lineageId } });
    }
  } finally {
    handoffSettled.value = true;
  }
});
</script>

<template>
  <div
    class="teacher-host"
    data-test="exam-workspace-teacher-host"
  >
    <ExamWorkspaceFileNotice
      v-if="handoff.notice.value"
      :reason="noticeReason"
      :busy="handoff.notice.value.busy"
      @download="handoff.download()"
      @remove="handoff.remove()"
      @retry="handoff.retry()"
    />
    <ExamWorkspaceView
      v-if="handoffSettled"
      :store="serverExamWorkspaceStore"
    />
  </div>
</template>

<style scoped>
.teacher-host { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.teacher-host > .notice { flex: none; }
.notice { margin-bottom: var(--huleedu-space-3); }
</style>
