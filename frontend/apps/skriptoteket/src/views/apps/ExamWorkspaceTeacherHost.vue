<script setup lang="ts">
/**
 * Signed-in exam workspace host.
 *
 * Domain purpose:
 *   Mount the exam workspace on the signed-in store, which delegates every
 *   server call to the transport modules. A guest host mounts the same view on
 *   a browser store instead. A browser draft left behind by a guest is handed
 *   off to Mina filer once on mount; the view renders only after the handoff
 *   settles, opening the handed-off exam.
 *
 * Relationships:
 *   - Mounted by the `/apps/exam-workspace` route and the curated app host.
 *   - Renders `ExamWorkspaceView` with `serverExamWorkspaceStore`.
 *   - Hands a stored guest draft over through `runGuestHandoff` before the
 *     view opens the exam named by `?document=<lineage_id>`.
 */

import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import { createExamWorkspaceGuestDraftStorage } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import { createLocalStorageGuestHandoffRejectionStorage } from "./exam-workspace/examWorkspaceGuestHandoffRejection";
import { serverExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import { runGuestHandoff } from "./exam-workspace/useExamWorkspaceGuestHandoff";

const route = useRoute();
const router = useRouter();

const handoffSettled = ref(false);

onMounted(async () => {
  const outcome = await runGuestHandoff({
    rejections: createLocalStorageGuestHandoffRejectionStorage(),
    storage: createExamWorkspaceGuestDraftStorage(),
    teacher: serverExamWorkspaceStore.teacher,
  });
  if (outcome.kind === "handed_off") {
    await router.replace({ query: { ...route.query, document: outcome.lineageId } });
  }
  handoffSettled.value = true;
});
</script>

<template>
  <ExamWorkspaceView
    v-if="handoffSettled"
    :store="serverExamWorkspaceStore"
  />
</template>
