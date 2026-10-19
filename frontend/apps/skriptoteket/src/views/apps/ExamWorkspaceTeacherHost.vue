<script setup lang="ts">
/**
 * Signed-in exam workspace host.
 *
 * Domain purpose:
 *   Mount the exam workspace on the signed-in store, which delegates every
 *   server call to the transport modules. A guest host mounts the same view on
 *   a browser store instead. A browser draft left behind by a guest is handed
 *   off to Mina filer once on mount through the handoff controller; the view
 *   renders only after the first attempt settles, opening the handed-off
 *   exam. A draft Mina filer refused for good leaves a notice above the view
 *   with glyph actions (download, remove, and for a full Mina filer retry);
 *   transient failures toast and retry in the background.
 *
 * Relationships:
 *   - Mounted by the `/apps/exam-workspace` route and the curated app host.
 *   - Renders `ExamWorkspaceView` with `serverExamWorkspaceStore`.
 *   - Runs the stored guest draft through `useExamWorkspaceGuestHandoffController`
 *     before the view opens the exam named by `?document=<lineage_id>`, and
 *     renders `ExamWorkspaceGuestHandoffNotice` above the view while the
 *     controller holds a rejection.
 */

import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import ExamWorkspaceGuestHandoffNotice from "./exam-workspace/ExamWorkspaceGuestHandoffNotice.vue";
import { createExamWorkspaceGuestDraftStorage } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import { createLocalStorageGuestHandoffRejectionStorage } from "./exam-workspace/examWorkspaceGuestHandoffRejection";
import { serverExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import { useExamWorkspaceGuestHandoffController } from "./exam-workspace/useExamWorkspaceGuestHandoffController";

const route = useRoute();
const router = useRouter();

const handoff = useExamWorkspaceGuestHandoffController({
  rejections: createLocalStorageGuestHandoffRejectionStorage(),
  storage: createExamWorkspaceGuestDraftStorage(),
  teacher: serverExamWorkspaceStore.teacher,
});
const handoffSettled = ref(false);

onMounted(async () => {
  const lineageId = await handoff.start();
  if (lineageId) {
    await router.replace({ query: { ...route.query, document: lineageId } });
  }
  handoffSettled.value = true;
});
</script>

<template>
  <div
    class="teacher-host"
    data-test="exam-workspace-teacher-host"
  >
    <ExamWorkspaceGuestHandoffNotice
      v-if="handoff.notice.value"
      :reason="handoff.notice.value.reason"
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
