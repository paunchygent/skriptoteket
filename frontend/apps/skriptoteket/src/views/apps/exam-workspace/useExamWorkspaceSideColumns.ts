/**
 * Exam workspace side columns (view seam).
 *
 * Domain purpose:
 *   Own the view's presentation-only columns: the phone list,
 *   the import box, and the Förhandsgranska preview beside the editor. One
 *   side column at a time: the preview and a drawer never share the body.
 *   The preview renders the persisted working state through
 *   `useExamWorkspacePrintPreview`, refreshed after each saved edit or save.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView`; the list, import and preview flags stay
 *     plain refs so the template and the selection, save-flow and keyboard
 *     wiring keep their assignments. The drawer ref is owned by
 *     `useExamWorkspaceDrawerState` and passed in; this seam only keeps it
 *     exclusive with the preview.
 *   - Calls back with the newly opened lineage so the view shows that
 *     document and dismisses the guest sign-in prompt it interrupted.
 */

import { computed, ref, watch } from "vue";
import type { Ref } from "vue";

import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";
import { useExamWorkspacePrintPreview } from "./useExamWorkspacePrintPreview";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";

export type ExamWorkspaceSideDrawer = "open" | "export" | "details";

export function useExamWorkspaceSideColumns(deps: {
  drawer: Ref<ExamWorkspaceSideDrawer | null>;
  historyCursor: Ref<string | null>;
  historyPosition: Ref<string | null>;
  layout: Ref<ExamWorkspaceLayout>;
  lineageId: Ref<string | null>;
  savedRevision: Ref<number | null>;
  selectedItemId: Ref<string | null>;
  store: ExamWorkspaceStore;
  onLineage: (lineageId: string | null) => void;
}) {
  const isPhone = computed(() => deps.layout.value === "phone");
  const listOpen = ref(false);
  const importOpen = ref(false);

  // Förhandsgranska (W5): the persisted working state's print pages beside the editor, refreshed after each saved edit or save.
  const previewOpen = ref(false);
  const printPreview = useExamWorkspacePrintPreview({
    lineageId: deps.lineageId,
    open: previewOpen,
    savedRevision: deps.savedRevision,
    historyCursor: deps.historyCursor,
    historyPosition: deps.historyPosition,
    selectedItemId: deps.selectedItemId,
    store: deps.store,
  });
  const {
    blocked: previewBlocked,
    loading: previewLoading,
    message: previewMessage,
    pages: previewPages,
    questionPages: previewQuestionPages,
  } = printPreview;

  function togglePreview(): void {
    // The preview renders through the teacher half; guests have none.
    if (deps.store.teacher === null) return;
    previewOpen.value = !previewOpen.value;
  }

  // One side column at a time: the preview and a drawer never share the body.
  watch(previewOpen, (open) => {
    if (open) deps.drawer.value = null;
  });
  watch(deps.drawer, (name) => {
    if (name !== null) previewOpen.value = false;
  });

  watch(
    deps.lineageId,
    (lineageId, previous) => {
      deps.onLineage(lineageId);
      if (lineageId === null) {
        deps.drawer.value = "open";
      } else if (lineageId !== previous && !(deps.layout.value === "desktop" && deps.drawer.value === "open")) {
        deps.drawer.value = null;
      }
    },
  );

  watch(isPhone, (phone) => {
    if (!phone) listOpen.value = false;
  });

  return {
    importOpen,
    isPhone,
    listOpen,
    previewBlocked,
    previewLoading,
    previewMessage,
    previewOpen,
    previewPages,
    previewQuestionPages,
    togglePreview,
  };
}
