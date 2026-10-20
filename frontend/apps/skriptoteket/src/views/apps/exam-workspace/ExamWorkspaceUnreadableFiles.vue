<script setup lang="ts">
/**
 * Exam workspace unreadable saved exams rows.
 *
 * Domain purpose:
 *   The Öppna drawer's rows for saved exams the app cannot read: one row
 *   per exam that is not a button, with the title, the saved date and the
 *   shared file notice for downloading the stored file or moving it to the
 *   papperskorg. A row click opens nothing. The row count is reported after
 *   every load and remove so the drawer can hide its empty hint.
 *
 * Relationships:
 *   - Rendered at the end of the saved section in `ExamWorkspaceOpenDrawer`,
 *     only for a signed-in teacher; the drawer owns the empty hint.
 *   - Rows come from the shared unreadable-files state the surrounding
 *     `ExamWorkspaceDrawers` provides, so a remove from the
 *     saved-unreadable notice reloads these rows too; presentation reuses
 *     `ExamWorkspaceFileNotice` with reason `saved_unreadable` and the row
 *     labels in `examWorkspaceRows`.
 */

import { onMounted } from "vue";

import type { ExamWorkspaceUnreadableDocument } from "../../../api/examWorkspaceUnreadableFiles";
import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceFileNotice from "./ExamWorkspaceFileNotice.vue";
import { examWorkspaceDocumentLabel, examWorkspaceSavedAtLabel } from "./examWorkspaceRows";
import { useExamWorkspaceUnreadableFilesState } from "./useExamWorkspaceUnreadableFiles";

const emit = defineEmits<{
  count: [count: number];
}>();

const { busyIds, download, files, load, remove } = useExamWorkspaceUnreadableFilesState();

/** Load the rows on mount, then report the count; every remove reports it again. */
onMounted(async () => {
  await load();
  emit("count", files.value.length);
});

async function handleRemove(file: ExamWorkspaceUnreadableDocument): Promise<void> {
  await remove(file);
  emit("count", files.value.length);
}
</script>

<template>
  <div
    v-if="files.length > 0"
    class="unreadable"
  >
    <div class="files">
      <div
        v-for="file in files"
        :key="file.lineage_id"
        class="file file--unreadable"
        :data-test="`exam-workspace-unreadable-${file.lineage_id}`"
      >
        <UiGlyph
          meaning="document"
          :size="16"
        />
        <span class="file__body">
          <span class="file__title">{{ file.title || examWorkspaceDocumentLabel(file.name) }}</span>
          <span class="file__meta">
            <span>Sparad {{ examWorkspaceSavedAtLabel(file.saved_at) }}</span>
          </span>
          <ExamWorkspaceFileNotice
            reason="saved_unreadable"
            :busy="busyIds.has(file.lineage_id)"
            @download="download(file)"
            @remove="handleRemove(file)"
          />
        </span>
        <span />
      </div>
    </div>
  </div>
</template>

<style scoped>
.unreadable { margin-top: var(--huleedu-space-4); }
.files { overflow: hidden; border: 1px solid var(--huleedu-panel-border); border-radius: var(--huleedu-radius-lg); background: var(--huleedu-surface-content); }
.file {
  display: grid; grid-template-columns: 20px minmax(0, 1fr) auto; align-items: start; gap: var(--huleedu-space-3);
  padding: var(--huleedu-space-2-5) var(--huleedu-space-3); border-top: 1px solid var(--huleedu-surface-divider);
  cursor: default;
}
.file:first-child { border-top: 0; }
.file > svg { margin-top: 2px; color: var(--huleedu-navy-60); }
.file__body { min-width: 0; }
.file__title { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--huleedu-text-sm); font-weight: var(--huleedu-font-medium); }
.file__meta {
  display: flex; flex-wrap: wrap; align-items: center; gap: var(--huleedu-space-1-5); margin-top: 3px;
  font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-60);
}
</style>
