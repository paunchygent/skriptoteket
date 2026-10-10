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
import { downloadExamWorkspaceExport } from "../../../api/examWorkspace";
import type {
  ExamWorkspaceDocumentSummary,
  ExamWorkspaceExportBlocker,
  ExamWorkspaceExportBlockerReason,
  ExamWorkspaceExportTarget,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { triggerBrowserDownload } from "../exam-converter/browserDownload";

export const EXAM_WORKSPACE_EXPORT_BLOCKER_COPY: Record<ExamWorkspaceExportBlockerReason, string> =
  {
    machine_proposed_key_unreviewed: "Facitförslaget är inte godkänt.",
    missing_points: "Poäng saknas.",
    review_required: "Frågan behöver granskas.",
  };

export const EXAM_WORKSPACE_EXPORT_BLOCKED_COPY =
  "Filen kan inte skapas ännu. Åtgärda de markerade frågorna och spara.";

const EXPORT_TARGET_LABELS: Record<ExamWorkspaceExportTarget, string> = {
  docx: "Word-filen",
  pdf: "PDF-filen",
  qti: "QTI-paketet",
};

const FALLBACK_FILENAMES: Record<ExamWorkspaceExportTarget, string> = {
  docx: "prov.docx",
  pdf: "prov-examnet.pdf",
  qti: "prov-qti.zip",
};

const BLOCKER_REASONS = new Set<string>(Object.keys(EXAM_WORKSPACE_EXPORT_BLOCKER_COPY));

function parseBlockers(details: unknown): ExamWorkspaceExportBlocker[] {
  if (typeof details !== "object" || details === null) {
    return [];
  }
  const blockers = (details as { blockers?: unknown }).blockers;
  if (!Array.isArray(blockers)) {
    return [];
  }
  return blockers.filter(
    (candidate): candidate is ExamWorkspaceExportBlocker =>
      typeof candidate === "object" &&
      candidate !== null &&
      typeof (candidate as { item_id?: unknown }).item_id === "string" &&
      BLOCKER_REASONS.has(String((candidate as { reason?: unknown }).reason)),
  );
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

export function useExamWorkspaceExports(summary: Ref<ExamWorkspaceDocumentSummary | null>) {
  const toast = useToast();

  const exportingTarget = ref<ExamWorkspaceExportTarget | null>(null);
  const exportBlockersByItemId = ref<Record<string, string[]>>({});
  const exportNotice = ref<string | null>(null);

  function clearExportFeedback(): void {
    exportBlockersByItemId.value = {};
    exportNotice.value = null;
  }

  watch(
    () => [summary.value?.lineage_id, summary.value?.version],
    () => clearExportFeedback(),
  );

  async function exportDocument(target: ExamWorkspaceExportTarget): Promise<void> {
    const currentSummary = summary.value;
    if (!currentSummary || exportingTarget.value !== null) {
      return;
    }
    exportingTarget.value = target;
    try {
      const response = await downloadExamWorkspaceExport(currentSummary.lineage_id, target);
      triggerBrowserDownload(response.blob, response.filename ?? FALLBACK_FILENAMES[target]);
      clearExportFeedback();
      toast.success(`${EXPORT_TARGET_LABELS[target]} är skapad.`);
    } catch (error) {
      const blockers = isApiError(error) && error.status === 422 ? parseBlockers(error.details) : [];
      if (blockers.length > 0) {
        exportBlockersByItemId.value = groupBlockers(blockers);
        exportNotice.value = EXAM_WORKSPACE_EXPORT_BLOCKED_COPY;
        toast.warning(EXAM_WORKSPACE_EXPORT_BLOCKED_COPY);
      } else {
        exportBlockersByItemId.value = {};
        exportNotice.value = `${EXPORT_TARGET_LABELS[target]} kunde inte skapas. Försök igen.`;
        toast.failure(exportNotice.value);
      }
    } finally {
      exportingTarget.value = null;
    }
  }

  return {
    clearExportFeedback,
    exportBlockersByItemId,
    exportDocument,
    exportNotice,
    exportingTarget,
  };
}
