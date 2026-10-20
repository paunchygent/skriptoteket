/**
 * Exam workspace document address sync.
 *
 * Domain purpose:
 *   Keep the `?document=<lineage_id>` query and the open exam in step. On
 *   mount, a query naming a document opens it. Later query changes
 *   (back/forward or an in-app link) settle the open exam, retire its
 *   generation and open the named document under the request's token; with
 *   unsaved edits, or when the named document does not open, the open
 *   document stays and the address is pointed back at it. `showDocument`
 *   writes a newly open document into the address. Only the initiating
 *   current request clears the pending target or restores the address: a
 *   superseded completion clears and restores nothing; a failed one clears,
 *   restores and reads the retained exam fresh.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView`, which calls `showDocument` from its
 *     open-document watcher.
 *   - Opens documents through the routed open, which takes the token the
 *     settle-and-retire entry hands back.
 */

import { onMounted, ref, watch } from "vue";
import type { Ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import type { ExamWorkspaceDocumentSummary } from "../../../api/examWorkspace";
import type { FenceToken } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceRouteOpenOutcome } from "./examWorkspaceRouteRequest";

export type ExamWorkspaceAddressParams = {
  isDirty: Readonly<Ref<boolean>>;
  /** Open the named document for the request's token; reports the routed outcome. */
  openDocument: (lineageId: string, token: FenceToken) => Promise<ExamWorkspaceRouteOpenOutcome>;
  /** Settle the latest edit and retire the generation; null when the edit did not settle. */
  noteRouteRequest: () => Promise<FenceToken | null>;
  /** Read the open exam fresh when the route returns to it or its replacement fails. */
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

  /** Clear the pending target only for the request that set it. */
  function clearPendingTarget(lineageId: string): void {
    if (pendingTarget.value === lineageId) {
      pendingTarget.value = null;
    }
  }

  /** Restore the address only while the route still names this request. */
  function restoreForRequest(lineageId: string): void {
    if (routeDocumentId() === lineageId) {
      restoreDocumentAddress();
    }
  }

  /**
   * Settle and open the named document for this request. A superseded
   * request clears and restores nothing; a settled failure and an unsettled
   * request restore the address and read the retained exam fresh (a failed
   * one through the recovery, an unsettled one through the dirty guard).
   */
  async function openRequestedDocument(lineageId: string): Promise<void> {
    const token = await params.noteRouteRequest();
    if (token === null) {
      clearPendingTarget(lineageId);
      restoreForRequest(lineageId);
      return;
    }
    const outcome = await params.openDocument(lineageId, token);
    if (outcome === "superseded") {
      return;
    }
    clearPendingTarget(lineageId);
    if (outcome === "failed") {
      restoreForRequest(lineageId);
      params.reloadOpen();
    }
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
        // open exam is never read over: retire only, and keep its edits. A
        // newer request that arrived during the settle owns the route now.
        if (pendingTarget.value === null) {
          return;
        }
        pendingTarget.value = null;
        await params.noteRouteRequest();
        if (pendingTarget.value !== null) {
          return;
        }
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
      await openRequestedDocument(lineageId);
    },
  );

  onMounted(() => {
    const lineageId = routeDocumentId();
    if (lineageId) {
      pendingTarget.value = lineageId;
      void openRequestedDocument(lineageId);
    }
  });

  return { showDocument };
}
