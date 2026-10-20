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

import { onMounted, ref, watch } from "vue";
import type { Ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import type { ExamWorkspaceDocumentSummary } from "../../../api/examWorkspace";

export type ExamWorkspaceAddressParams = {
  isDirty: Readonly<Ref<boolean>>;
  openDocument: (lineageId: string) => Promise<boolean>;
  /** Retire the superseded open when the route returns to the open exam. */
  noteRouteRequest: () => void;
  /** Read the open exam fresh when the route returns to it. */
  reloadOpen: () => void;
  summary: Ref<ExamWorkspaceDocumentSummary | null>;
};

export function useExamWorkspaceAddress(params: ExamWorkspaceAddressParams) {
  const route = useRoute();
  const router = useRouter();
  /** The lineage the route last asked for while another exam is still open. */
  const pendingTarget = ref<string | null>(null);

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
      if (!lineageId) {
        return;
      }
      if (lineageId === openLineageId) {
        // The route is back at the open exam while another open was pending:
        // retire the superseded open and read the open exam fresh. A dirty
        // open exam is never read over: retire only, and keep its edits.
        if (pendingTarget.value === null) {
          return;
        }
        pendingTarget.value = null;
        params.noteRouteRequest();
        if (!params.isDirty.value) {
          params.reloadOpen();
        }
        return;
      }
      if (params.isDirty.value && openLineageId) {
        restoreDocumentAddress();
        return;
      }
      pendingTarget.value = lineageId;
      const opened = await params.openDocument(lineageId);
      if (pendingTarget.value === lineageId) {
        pendingTarget.value = null;
      }
      if (!opened && routeDocumentId() === lineageId) {
        restoreDocumentAddress();
      }
    },
  );

  onMounted(() => {
    const lineageId = routeDocumentId();
    if (lineageId) {
      pendingTarget.value = lineageId;
      void params.openDocument(lineageId).then(() => {
        if (pendingTarget.value === lineageId) {
          pendingTarget.value = null;
        }
      });
    }
  });

  return { showDocument };
}
