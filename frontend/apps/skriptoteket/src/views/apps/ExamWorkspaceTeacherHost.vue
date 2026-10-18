<script setup lang="ts">
/**
 * Signed-in exam workspace host.
 *
 * Domain purpose:
 *   Mount the exam workspace on the signed-in store, which delegates every
 *   server call to the transport modules. A guest host mounts the same view on
 *   a browser store instead.
 *
 * Relationships:
 *   - Mounted by the `/apps/exam-workspace` route and the curated app host.
 *   - Renders `ExamWorkspaceView` with `serverExamWorkspaceStore`.
 */

import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import { serverExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
</script>

<template>
  <ExamWorkspaceView :store="serverExamWorkspaceStore" />
</template>
