/**
 * Exam workspace Förhandsgranska panel state.
 *
 * Domain purpose:
 *   Keep the rendered student print copy beside the editor (W5). The panel
 *   renders the persisted working state the editor stands on and refreshes
 *   after the last saved edit or save: it waits `PREVIEW_DEBOUNCE_MS` after the
 *   last history-cursor change, so a burst of edits renders once, and it keeps
 *   the last ready pages while a new render runs or the exam cannot be
 *   rendered. A moved revision or cursor answers 409 and is dropped for the
 *   next change; any other failure keeps the pages and reports once through
 *   the workspace's failure toast. Editing never waits on a render.
 *
 * Relationships:
 *   - Transport to `api/examWorkspaceExports.ts`.
 *   - Consumed by `ExamWorkspaceView` and rendered by
 *     `ExamWorkspacePrintPreviewPanel`.
 */

import { ref, watch } from "vue";
import type { Ref } from "vue";

import { isApiError } from "../../../api/client";
import { fetchExamWorkspacePrintPreview } from "../../../api/examWorkspaceExports";
import type { ExamWorkspacePrintPreview } from "../../../api/examWorkspaceExports";
import { useToast } from "../../../composables/useToast";

/** Wait after the last saved-revision or history-cursor change before rendering, so a burst of edits renders once. */
export const PREVIEW_DEBOUNCE_MS = 1200;

const REFRESH_FAILED_COPY = "Förhandsgranskningen kunde inte uppdateras.";

export interface ExamWorkspacePrintPreviewDeps {
  lineageId: Ref<string | null>;
  /** The saved version the open copy stands on; a number triggers a render. */
  savedRevision: Ref<number | null>;
  /** The server's newest undo step: the persisted working state the editor stands on after each saved edit. */
  historyCursor: Ref<string | null>;
  open: Ref<boolean>;
  /** The question the panel scrolls to; the panel owns that scroll. */
  selectedItemId: Ref<string | null>;
}

export function useExamWorkspacePrintPreview({
  historyCursor,
  lineageId,
  savedRevision,
  open,
}: ExamWorkspacePrintPreviewDeps) {
  const toast = useToast();

  /** The pages of the last ready render, kept while a new render runs or the exam is blocked. */
  const pages = ref<string[]>([]);
  const questionPages = ref<Record<string, number>>({});
  const loading = ref(false);
  /** The status of the latest answer: true when the saved exam cannot be rendered at all. */
  const blocked = ref(false);
  const message = ref<string | null>(null);

  /** The newest scheduled request; a response from an older one is dropped. */
  let requestSeq = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;

  function cancelScheduled(): void {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function apply(response: ExamWorkspacePrintPreview): void {
    if (response.status === "ready") {
      pages.value = response.pages;
      questionPages.value = response.question_pages;
      blocked.value = false;
    } else {
      // A blocked exam keeps the last pages so the teacher still sees them.
      blocked.value = true;
    }
    message.value = response.message;
  }

  async function load(
    requestId: number,
    lineage: string,
    expectedRevision: number,
    expectedCursor: string,
  ): Promise<void> {
    try {
      const response = await fetchExamWorkspacePrintPreview(lineage, expectedRevision, expectedCursor);
      if (requestId !== requestSeq) return;
      apply(response);
      loading.value = false;
    } catch (error) {
      if (requestId !== requestSeq) return;
      loading.value = false;
      // 409: the persisted state moved on; the next change fetches again.
      if (isApiError(error) && error.status === 409) return;
      toast.failure(REFRESH_FAILED_COPY);
    }
  }

  watch(
    () => [open.value, lineageId.value, savedRevision.value, historyCursor.value] as const,
    () => {
      cancelScheduled();
      const lineage = lineageId.value;
      const revision = savedRevision.value;
      const cursor = historyCursor.value;
      if (!open.value || lineage === null || typeof revision !== "number" || cursor === null) {
        // A closed panel or an unsaved exam drops every in-flight response.
        requestSeq += 1;
        loading.value = false;
        return;
      }
      const requestId = ++requestSeq;
      loading.value = true;
      timer = setTimeout(() => {
        void load(requestId, lineage, revision, cursor);
      }, PREVIEW_DEBOUNCE_MS);
    },
    { immediate: true },
  );

  // Another exam starts from no pages rather than from the previous exam's.
  watch(lineageId, () => {
    pages.value = [];
    questionPages.value = {};
    blocked.value = false;
    message.value = null;
  });

  return { blocked, loading, message, pages, questionPages };
}
