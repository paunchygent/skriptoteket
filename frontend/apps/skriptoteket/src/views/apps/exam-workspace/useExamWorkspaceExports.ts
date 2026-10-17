/**
 * Exam workspace on-demand exports.
 *
 * Domain purpose:
 *   Download QTI, PDF, and DOCX files generated from the saved head revision.
 *   The server owns the export gate; when it refuses with per-item blockers,
 *   map them to Swedish per-item copy for the item table.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView` next to `useExamWorkspaceDocument`.
 *   - Delegates transport to `api/examWorkspace.ts` and downloads through the
 *     shared browser download helper.
 */

import { ref, watch } from "vue";
import type { Ref } from "vue";

import { isApiError } from "../../../api/client";
import {
  downloadExamWorkspaceExport,
  getExamWorkspaceExportChecklist,
} from "../../../api/examWorkspace";
import type {
  ExamWorkspaceDocumentSummary,
  ExamWorkspaceExportBlocker,
  ExamWorkspaceExportBlockerReason,
  ExamWorkspaceExportChecklistEntry,
  ExamWorkspaceExportTarget,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { triggerBrowserDownload } from "../exam-converter/browserDownload";

/** A save from elsewhere moved the head; exporting again fails until the teacher reloads it. */
const EXPORT_STALE_COPY = "Provet har sparats någon annanstans. Läs in på nytt och exportera igen.";

export const EXAM_WORKSPACE_EXPORT_BLOCKER_COPY: Record<ExamWorkspaceExportBlockerReason, string> =
  {
    machine_proposed_key_unreviewed: "Facitförslaget är inte godkänt.",
    missing_answer_key: "Frågan saknar facit. Fyll i facit eller låt AI föreslå ett.",
    missing_points: "Poäng saknas.",
    empty_choice: "Ett svarsalternativ saknar text.",
    empty_gap_option: "Ett alternativ i en lucka saknar text.",
    empty_match_entry: "En del i matchningen saknar text.",
    inline_choice_option_heading: "Rubrikformat är inte tillåtet i rullistealternativ.",
    unbuilt_question:
      "Frågan kunde inte konverteras och visas som i källan. Kontrollera den och markera den som granskad.",
  };

export const EXAM_WORKSPACE_EXPORT_BLOCKED_COPY =
  "Filen kan inte skapas ännu. Åtgärda de markerade frågorna och spara.";

const EXPORT_TARGET_LABELS: Record<ExamWorkspaceExportTarget, string> = {
  docx: "Word-filen",
  pdf: "PDF-filen",
  qti: "QTI-paketet",
};

const EXPORT_CREATED_MESSAGES: Record<ExamWorkspaceExportTarget, string> = {
  docx: "Word-filen är skapad.",
  pdf: "PDF-filen är skapad.",
  qti: "QTI-paketet är skapat.",
};

const FALLBACK_FILENAMES: Record<ExamWorkspaceExportTarget, string> = {
  docx: "prov.docx",
  pdf: "prov-examnet.pdf",
  qti: "prov-qti.zip",
};

const BLOCKER_REASONS = new Set<string>(Object.keys(EXAM_WORKSPACE_EXPORT_BLOCKER_COPY));

function isExportBlocker(candidate: unknown): candidate is ExamWorkspaceExportBlocker {
  return (
    typeof candidate === "object" &&
    candidate !== null &&
    "item_id" in candidate &&
    typeof candidate.item_id === "string" &&
    "reason" in candidate &&
    BLOCKER_REASONS.has(String(candidate.reason))
  );
}

function parseBlockers(details: unknown): ExamWorkspaceExportBlocker[] {
  if (typeof details !== "object" || details === null || !("blockers" in details)) {
    return [];
  }
  const { blockers } = details;
  return Array.isArray(blockers) ? blockers.filter(isExportBlocker) : [];
}

function groupBlockers(blockers: ExamWorkspaceExportBlocker[]): Record<string, string[]> {
  const grouped: Record<string, string[]> = {};
  for (const blocker of blockers) {
    const copy = EXAM_WORKSPACE_EXPORT_BLOCKER_COPY[blocker.reason];
    const existing = grouped[blocker.item_id] ?? [];
    if (!existing.includes(copy)) {
      grouped[blocker.item_id] = [...existing, copy];
    }
  }
  return grouped;
}

export function useExamWorkspaceExports(
  summary: Ref<ExamWorkspaceDocumentSummary | null>,
  workspaceDocument: Ref<NativeExamDocument | null>,
) {
  const toast = useToast();

  const exportingTarget = ref<ExamWorkspaceExportTarget | null>(null);
  const exportBlockersByItemId = ref<Record<string, string[]>>({});
  const exportNotice = ref<string | null>(null);
  const exportChecklist = ref<ExamWorkspaceExportChecklistEntry[]>([]);
  /** Bumped by every clear, so an in-flight checklist response can be dropped. */
  let checklistRequestId = 0;

  function clearExportFeedback(): void {
    exportBlockersByItemId.value = {};
    exportNotice.value = null;
  }

  function clearExportChecklist(): void {
    checklistRequestId += 1;
    exportChecklist.value = [];
  }

  watch(
    () => [summary.value?.lineage_id, summary.value?.version],
    () => clearExportFeedback(),
  );

  watch(
    () => [summary.value?.lineage_id, summary.value?.version, workspaceDocument.value],
    () => clearExportChecklist(),
  );

  /** Whether a checklist this request reserved is still the one the document wants. */
  function isCurrentChecklistRequest(requestId: number, lineageId: string): boolean {
    return requestId === checklistRequestId && summary.value?.lineage_id === lineageId;
  }

  /**
   * Show the losses of the revision just exported. The reserved request id
   * drops the response once any clear or export start has moved past it, so
   * a slow response cannot reappear over a changed document.
   */
  async function loadExportChecklist(
    lineageId: string,
    expectedRevision: number,
    requestId: number,
  ): Promise<void> {
    try {
      const response = await getExamWorkspaceExportChecklist(lineageId, expectedRevision);
      if (!isCurrentChecklistRequest(requestId, lineageId)) {
        return;
      }
      exportChecklist.value = response.entries;
    } catch (error) {
      if (!isCurrentChecklistRequest(requestId, lineageId)) {
        return;
      }
      toast.warning(
        isApiError(error) && error.status === 409
          ? EXPORT_STALE_COPY
          : "QTI-paketet är skapat. Listan över vad Exam.net tappar kunde inte hämtas.",
      );
    }
  }

  async function exportDocument(target: ExamWorkspaceExportTarget): Promise<void> {
    const currentSummary = summary.value;
    if (!currentSummary || exportingTarget.value !== null) {
      return;
    }
    exportingTarget.value = target;
    clearExportChecklist();
    const requestId = checklistRequestId;
    try {
      const response = await downloadExamWorkspaceExport(
        currentSummary.lineage_id,
        target,
        currentSummary.version,
      );
      triggerBrowserDownload(response.blob, response.filename ?? FALLBACK_FILENAMES[target]);
      clearExportFeedback();
      toast.success(EXPORT_CREATED_MESSAGES[target]);
    } catch (error) {
      const blockers = isApiError(error) && error.status === 422 ? parseBlockers(error.details) : [];
      if (blockers.length > 0) {
        exportBlockersByItemId.value = groupBlockers(blockers);
        exportNotice.value = EXAM_WORKSPACE_EXPORT_BLOCKED_COPY;
        toast.warning(EXAM_WORKSPACE_EXPORT_BLOCKED_COPY);
      } else if (isApiError(error) && error.status === 409) {
        exportBlockersByItemId.value = {};
        exportNotice.value = EXPORT_STALE_COPY;
        toast.warning(EXPORT_STALE_COPY);
      } else {
        exportBlockersByItemId.value = {};
        exportNotice.value = `${EXPORT_TARGET_LABELS[target]} kunde inte skapas. Försök igen.`;
        toast.failure(exportNotice.value);
      }
      return;
    } finally {
      exportingTarget.value = null;
    }
    if (target === "qti") {
      await loadExportChecklist(currentSummary.lineage_id, currentSummary.version, requestId);
    }
  }

  return {
    clearExportFeedback,
    exportBlockersByItemId,
    exportChecklist,
    exportDocument,
    exportNotice,
    exportingTarget,
  };
}
