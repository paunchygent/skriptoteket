/**
 * Exam workspace document installs (TASK-SKRIPT-40-04-14, F2).
 *
 * Domain purpose:
 *   The fenced installs into the open copy: a fresh server response, the
 *   saved baseline after a confirmed store or move, and a server command
 *   response. Every install carries the queue token it runs under and returns
 *   without effect when the token is retired, so an obsolete answer never
 *   replaces newer typing or clears current recovery state.
 */

import type { Ref, ShallowRef } from "vue";

import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import type { FenceToken } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";
import type { ExamWorkspaceTitleVerdict } from "./useExamWorkspaceTitleVerdict";

export type ExamWorkspaceDocumentInstallsDeps = {
  openExam: ShallowRef<ExamWorkspaceOpening | null>;
  workspaceDocument: Ref<NativeExamDocument | null>;
  serverDocument: Ref<NativeExamDocument | null>;
  savedDocument: Ref<NativeExamDocument | null>;
  summary: Ref<ExamWorkspaceDocumentSummary | null>;
  historyCursor: Ref<string | null>;
  notes: Ref<string[]>;
  selectedItemId: Ref<string | null>;
  noteExportBlockers: ExamWorkspaceTitleVerdict;
  recordSummary: (summary: ExamWorkspaceDocumentSummary) => void;
  adoptConversion: (response: ExamWorkspaceDocumentResponse) => void;
  replayHeld: () => void;
  isCurrent: (token: FenceToken) => boolean;
};

export function createDocumentInstalls(deps: ExamWorkspaceDocumentInstallsDeps) {
  function applyResponse(
    token: FenceToken,
    response: ExamWorkspaceDocumentResponse,
    local: NativeExamDocument = response.document,
  ): void {
    if (!deps.isCurrent(token)) {
      return;
    }
    if (deps.openExam.value?.lineageId !== response.summary.lineage_id) {
      deps.openExam.value = { lineageId: response.summary.lineage_id };
    }
    deps.workspaceDocument.value = local;
    deps.noteExportBlockers(response.document.title, response.export_blockers);
    deps.serverDocument.value = response.document;
    deps.savedDocument.value = response.saved_document;
    deps.summary.value = response.summary;
    deps.historyCursor.value = response.history_cursor;
    deps.recordSummary(response.summary);
    deps.notes.value = response.notes;
    deps.adoptConversion(response);
    const items = local.items;
    deps.selectedItemId.value = items.some((item) => item.item_id === deps.selectedItemId.value)
      ? deps.selectedItemId.value
      : (items[0]?.item_id ?? null);
  }

  /**
   * A store or a position move confirmed this document; the exam file holds
   * it now. A stale token changes nothing. A confirmed title save also
   * carries the saved title onto the open summary and its Prov list entry at
   * once (TASK-SKRIPT-40-04-21, W3): the step store answers with the document
   * but no summary, so the entry would otherwise keep the old title until a
   * reload. The renamed file name arrives with the next list load.
   */
  function noteStored(token: FenceToken, document: NativeExamDocument): void {
    if (!deps.isCurrent(token)) {
      return;
    }
    deps.savedDocument.value = document;
    const current = deps.workspaceDocument.value;
    if (current !== null && current.revision !== document.revision) {
      deps.workspaceDocument.value = { ...current, revision: document.revision };
    }
    const currentSummary = deps.summary.value;
    if (currentSummary !== null && currentSummary.title !== document.title) {
      const updated = { ...currentSummary, title: document.title };
      deps.summary.value = updated;
      deps.recordSummary(updated);
    }
  }

  /** A server command stored a new step; show its document. A stale token changes nothing. */
  function applyCommandResponse(token: FenceToken, response: ExamWorkspaceDocumentResponse): void {
    if (!deps.isCurrent(token)) {
      return;
    }
    applyResponse(token, response);
    deps.replayHeld();
  }

  return { applyCommandResponse, applyResponse, noteStored };
}
