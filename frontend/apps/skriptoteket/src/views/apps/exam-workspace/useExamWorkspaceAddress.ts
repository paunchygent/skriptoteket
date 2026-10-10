/**
 * Exam workspace document address sync.
 *
 * Domain purpose:
 *   Keep the `?document=<lineage_id>` query and the open exam in step. On
 *   mount, a query naming a document opens it. Later query changes
 *   (back/forward or an in-app link) open the named document; with unsaved
 *   edits, or when the named document does not open, the open document
 *   stays and the address is pointed back at it. `showDocument` writes a
 *   newly open document into the address.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView`, which calls `showDocument` from its
 *     open-document watcher.
 *   - Opens documents through `useExamWorkspaceDocument.openDocument`.
 */

import { onMounted, watch } from "vue";
import type { Ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import type { ExamWorkspaceDocumentSummary } from "../../../api/examWorkspace";

export type ExamWorkspaceAddressParams = {
  isDirty: Ref<boolean>;
  openDocument: (lineageId: string) => Promise<boolean>;
  summary: Ref<ExamWorkspaceDocumentSummary | null>;
};

export function useExamWorkspaceAddress(params: ExamWorkspaceAddressParams) {
  const route = useRoute();
  const router = useRouter();

  function routeDocumentId(): string | null {
    const value = route.query.document;
    return typeof value === "string" && value.length > 0 ? value : null;
  }

  /** Write a newly open document into the address; the route watcher treats it as a no-op. */
  function showDocument(lineageId: string | null): void {
    if (lineageId && routeDocumentId() !== lineageId) {
      void router.replace({ query: { ...route.query, document: lineageId } });
    }
  }

  // Point the address back at the open document, or drop `document` when
  // nothing is open. Both outcomes are no-ops for the route watcher below.
  function restoreDocumentAddress(): void {
    const openLineageId = params.summary.value?.lineage_id ?? null;
    const { document: _document, ...rest } = route.query;
    void router.replace({ query: openLineageId ? { ...rest, document: openLineageId } : rest });
  }

  watch(
    () => routeDocumentId(),
    async (lineageId) => {
      const openLineageId = params.summary.value?.lineage_id ?? null;
      if (!lineageId || lineageId === openLineageId) {
        return;
      }
      if (params.isDirty.value && openLineageId) {
        restoreDocumentAddress();
        return;
      }
      const opened = await params.openDocument(lineageId);
      if (!opened && routeDocumentId() === lineageId) {
        restoreDocumentAddress();
      }
    },
  );

  onMounted(() => {
    const lineageId = routeDocumentId();
    if (lineageId) {
      void params.openDocument(lineageId);
    }
  });

  return { showDocument };
}
