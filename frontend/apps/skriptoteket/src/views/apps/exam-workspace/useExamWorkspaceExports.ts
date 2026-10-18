/**
 * Exam workspace on-demand exports.
 *
 * Domain purpose:
 *   Download QTI, PDF, and DOCX files generated from the saved head revision,
 *   or keep one in Mina filer as the exam's one file of that format, which
 *   the next save of that format replaces (TASK-SKRIPT-39-04-08). An export
 *   saves the exam first, so one click exports what the teacher sees; a
 *   failed save stops it (user rule 2026-10-17). The server owns the export
 *   gate; when it refuses with per-item blockers, keep their reasons per
 *   question, and a refused title, for the export menu's blocker rows. The
 *   file name is the server's: the Content-Disposition name is used as sent. When a save elsewhere moved
 *   the saved exam, the latest version is read in for the next export.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView` next to `useExamWorkspaceDocument`.
 *   - Delegates transport to `api/examWorkspace.ts` and downloads through the
 *     shared browser download helper.
 */

import { computed, ref, watch } from "vue";
import type { Ref } from "vue";

import { isApiError } from "../../../api/client";
import {
  downloadExamWorkspaceExport,
  getExamWorkspaceExportChecklist,
  saveExamWorkspaceExport,
} from "../../../api/examWorkspace";
import type {
  ExamWorkspaceDocumentSummary,
  ExamWorkspaceExportBlocker,
  ExamWorkspaceExportBlockerReason,
  ExamWorkspaceExportChecklistEntry,
  ExamWorkspaceExportTarget,
  ExamWorkspaceItemExportBlockerReason,
  NativeExamDocument,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { triggerBrowserDownload } from "../../../utils/browserDownload";
import { examWorkspaceSavedAt } from "./examWorkspaceFormat";
import type { ExamWorkspaceTitleVerdict } from "./useExamWorkspaceTitleVerdict";

/** A save from elsewhere moved the head; the workspace reads the latest version in. */
const EXPORT_STALE_COPY =
  "Provet hade sparats någon annanstans. Den senaste versionen är inläst. Exportera igen.";

export const EXAM_WORKSPACE_EXPORT_BLOCKER_COPY: Record<ExamWorkspaceExportBlockerReason, string> =
  {
    machine_proposed_key_unreviewed: "Facitförslaget är inte godkänt.",
    missing_answer_key: "Frågan saknar facit. Fyll i facit eller låt AI föreslå ett.",
    missing_points: "Poäng saknas.",
    empty_choice: "Ett svarsalternativ saknar text.",
    empty_gap_option: "Ett alternativ i en lucka saknar text.",
    empty_match_entry: "En del i matchningen saknar text.",
    ordering_too_few_steps: "Ordningsfrågan behöver minst två steg.",
    empty_ordering_step: "Ett steg i ordningsfrågan saknar text.",
    inline_choice_option_heading: "Rubrikformat är inte tillåtet i rullistealternativ.",
    title_without_text: "Ge provet en titel med bokstäver eller siffror.",
    too_few_gap_options: "En rullista i en lucka har färre än två alternativ.",
    unbuilt_question:
      "Frågan kunde inte konverteras och visas som i källan. Kontrollera den och markera den som granskad.",
  };

/** The refusal names what blocks: the title, the questions, or both. */
export function examWorkspaceExportBlockedCopy(blockers: readonly ExamWorkspaceExportBlocker[]): string {
  const titleBlocked = blockers.some((blocker) => blocker.item_id === null);
  const questionsBlocked = blockers.some((blocker) => blocker.item_id !== null);
  if (titleBlocked && questionsBlocked) {
    return "Filen kan inte skapas ännu. Åtgärda titeln och frågorna i listan och exportera igen.";
  }
  if (titleBlocked) {
    return "Filen kan inte skapas ännu. Ge provet en titel med bokstäver eller siffror och exportera igen.";
  }
  return "Filen kan inte skapas ännu. Åtgärda frågorna i listan och exportera igen.";
}

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

/** The format's name in the Mina filer messages. */
export const EXPORT_FORMAT_NAMES: Record<ExamWorkspaceExportTarget, string> = {
  docx: "DOCX",
  pdf: "PDF",
  qti: "QTI",
};

type ExportDestination = "download" | "files";

const BLOCKER_REASONS = new Set<string>(Object.keys(EXAM_WORKSPACE_EXPORT_BLOCKER_COPY));

function isExportBlocker(candidate: unknown): candidate is ExamWorkspaceExportBlocker {
  return (
    typeof candidate === "object" &&
    candidate !== null &&
    "item_id" in candidate &&
    (typeof candidate.item_id === "string" || candidate.item_id === null) &&
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

/** The server's reasons for one question, and the question as it was refused. */
type RefusedItem = { item: NativeExamItem | undefined; reasons: ExamWorkspaceItemExportBlockerReason[] };

function groupBlockers(
  blockers: ExamWorkspaceExportBlocker[],
  items: NativeExamItem[],
): Record<string, RefusedItem> {
  const grouped: Record<string, RefusedItem> = {};
  for (const blocker of blockers) {
    if (blocker.item_id === null || blocker.reason === "title_without_text") {
      continue;
    }
    const existing = grouped[blocker.item_id] ?? {
      item: items.find((item) => item.item_id === blocker.item_id),
      reasons: [],
    };
    if (!existing.reasons.includes(blocker.reason)) {
      existing.reasons.push(blocker.reason);
    }
    grouped[blocker.item_id] = existing;
  }
  return grouped;
}

export type ExamWorkspaceExportSteps = {
  /** Spara before the export; false when the save failed and has reported why. */
  saveFirst: () => Promise<boolean>;
  /** Read in the latest saved version after a save elsewhere moved it. */
  readLatest: () => Promise<void>;
  /** The export gate's refusal of the title just saved, for the title blocker. */
  noteBlockers: ExamWorkspaceTitleVerdict;
};

export function useExamWorkspaceExports(
  summary: Ref<ExamWorkspaceDocumentSummary | null>,
  workspaceDocument: Ref<NativeExamDocument | null>,
  steps: ExamWorkspaceExportSteps,
) {
  const toast = useToast();

  const exportingTarget = ref<ExamWorkspaceExportTarget | null>(null);
  const refusedItems = ref<Record<string, RefusedItem>>({});
  /**
   * The reasons the server gave when it last refused an export, per question,
   * until the teacher changes that question: items change by replacement, so
   * a changed question is a new object and its old refusal no longer holds.
   */
  const exportBlockersByItemId = computed<Record<string, ExamWorkspaceItemExportBlockerReason[]>>(() => {
    const current = new Map((workspaceDocument.value?.items ?? []).map((item) => [item.item_id, item]));
    return Object.fromEntries(
      Object.entries(refusedItems.value)
        .filter(([itemId, refused]) => refused.item !== undefined && current.get(itemId) === refused.item)
        .map(([itemId, refused]) => [itemId, refused.reasons]),
    );
  });
  const exportNotice = ref<string | null>(null);
  /** What the last export made, shown in Exportera; toasts report failures only (user rule 2026-10-17). */
  const exportResult = ref<string | null>(null);
  const exportChecklist = ref<ExamWorkspaceExportChecklistEntry[]>([]);
  /** Export format -> when the exam's file of that format was saved in Mina filer this session. */
  const savedExports = ref<Partial<Record<ExamWorkspaceExportTarget, string>>>({});
  /** Bumped by every clear, so an in-flight checklist response can be dropped. */
  let checklistRequestId = 0;

  function clearExportFeedback(): void {
    refusedItems.value = {};
    exportNotice.value = null;
    exportResult.value = null;
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
    () => summary.value?.lineage_id,
    () => {
      savedExports.value = {};
    },
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

  /** Show why the server refused an export of the saved version. */
  async function reportExportFailure(target: ExamWorkspaceExportTarget, error: unknown): Promise<void> {
    const blockers = isApiError(error) && error.status === 422 ? parseBlockers(error.details) : [];
    if (blockers.length > 0) {
      refusedItems.value = groupBlockers(blockers, workspaceDocument.value?.items ?? []);
      steps.noteBlockers(workspaceDocument.value?.title ?? "", blockers);
      exportNotice.value = examWorkspaceExportBlockedCopy(blockers);
      toast.warning(exportNotice.value);
    } else if (isApiError(error) && error.status === 409) {
      refusedItems.value = {};
        await steps.readLatest();
      exportNotice.value = EXPORT_STALE_COPY;
      toast.warning(EXPORT_STALE_COPY);
    } else {
      refusedItems.value = {};
        exportNotice.value = `${EXPORT_TARGET_LABELS[target]} kunde inte skapas. Försök igen.`;
      toast.failure(exportNotice.value);
    }
  }

  /**
   * Create one export of the saved version: download it, or keep it in Mina
   * filer as the exam's one file of that format, replacing the earlier one.
   * True when the file was made.
   */
  async function createExport(
    target: ExamWorkspaceExportTarget,
    destination: ExportDestination,
    savedSummary: ExamWorkspaceDocumentSummary,
  ): Promise<boolean> {
    try {
      if (destination === "files") {
        const replaced = savedExports.value[target] ?? null;
        const saved = await saveExamWorkspaceExport(savedSummary.lineage_id, target, savedSummary.version);
        if (summary.value?.lineage_id === savedSummary.lineage_id) {
          savedExports.value = { ...savedExports.value, [target]: saved.created_at };
        }
        clearExportFeedback();
        exportResult.value = replaced
          ? `${EXPORT_FORMAT_NAMES[target]} sparad i Mina filer och ersatte filen från ${examWorkspaceSavedAt(replaced)}.`
          : `${EXPORT_FORMAT_NAMES[target]} sparad i Mina filer.`;
      } else {
        const response = await downloadExamWorkspaceExport(savedSummary.lineage_id, target, savedSummary.version);
        triggerBrowserDownload(response.blob, response.filename);
        clearExportFeedback();
        exportResult.value = EXPORT_CREATED_MESSAGES[target];
      }
      return true;
    } catch (error) {
      await reportExportFailure(target, error);
      return false;
    }
  }

  /**
   * Spara, then export the version just saved, in one click. The format shows
   * the export running from the save on; a failed save exports nothing.
   */
  async function runExport(target: ExamWorkspaceExportTarget, destination: ExportDestination): Promise<void> {
    if (!summary.value || exportingTarget.value !== null) {
      return;
    }
    exportingTarget.value = target;
    let savedSummary: ExamWorkspaceDocumentSummary | null = null;
    let created = false;
    let requestId = checklistRequestId;
    try {
      if (!(await steps.saveFirst()) || !summary.value) {
        return;
      }
      savedSummary = summary.value;
      clearExportChecklist();
      requestId = checklistRequestId;
      created = await createExport(target, destination, savedSummary);
    } finally {
      exportingTarget.value = null;
    }
    if (created && target === "qti") {
      await loadExportChecklist(savedSummary.lineage_id, savedSummary.version, requestId);
    }
  }

  async function exportDocument(target: ExamWorkspaceExportTarget): Promise<void> {
    await runExport(target, "download");
  }

  async function saveExportToFiles(target: ExamWorkspaceExportTarget): Promise<void> {
    await runExport(target, "files");
  }

  return {
    clearExportFeedback,
    exportBlockersByItemId,
    exportChecklist,
    exportDocument,
    exportNotice,
    exportResult,
    exportingTarget,
    saveExportToFiles,
    savedExports,
  };
}
