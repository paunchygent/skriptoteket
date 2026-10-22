/**
 * Exam workspace conversion shared runtime.
 *
 * Domain purpose:
 *   The mutable page state one DOCX/DigiExam import's progressive conversion
 *   lives in, shared by the import action, the status poll and the revision
 *   sync. The poll owns the status, the revision sync owns the merge, and the
 *   import owns the file entrance; all three read and advance this one
 *   runtime so the orchestrator keeps no logic of its own.
 *
 * Relationships:
 *   - Created by `useExamWorkspaceConversion`; used by
 *     `examWorkspaceConversionStatusPoll`,
 *     `examWorkspaceConversionRevisionSync` and
 *     `examWorkspaceConversionImportAction`.
 */

import { ref } from "vue";
import type { Ref } from "vue";

import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceConversionUnit,
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import type { ExamWorkspaceRouteOpenOutcome } from "./examWorkspaceReplacementTypes";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import type { FenceToken, SyncFence } from "./examWorkspaceSyncFence";

export const EXAM_WORKSPACE_CONVERSION_POLL_MS = 3000;
export const CONVERSION_MAX_POLL_MS = 30_000;
export const CONVERSION_CLOCK_MS = 1000;
export const IMPORT_FAILURE_COPY = "Det gick inte att läsa in provet. Försök igen.";

/** The document owner's state that conversion revisions are applied to. */
export type ExamWorkspaceConversionBinding = {
  isDirty: Readonly<Ref<boolean>>;
  /** The server document the local copy started from. */
  serverDocument: Ref<NativeExamDocument | null>;
  summary: Ref<ExamWorkspaceDocumentSummary | null>;
  workspaceDocument: Ref<NativeExamDocument | null>;
  /** Capture metadata ordering before a GET; reconcile without delaying its application. */
  beginDocumentRead: () => (response: ExamWorkspaceDocumentResponse) => ExamWorkspaceDocumentResponse;
  /** Replace the local copy with a server response; `local` keeps merged teacher edits. */
  applyResponse: (token: FenceToken, response: ExamWorkspaceDocumentResponse, local?: NativeExamDocument) => void;
  /** The sync gate's generation owner; every install carries its token. */
  getFence: () => SyncFence;
  /** True while the token's generation is still current; stale installs do nothing. */
  isCurrent: (token: FenceToken) => boolean;
  /** A save is in flight; its response replaces the copy, so merging waits. */
  isSaving: () => boolean;
  /** The store the document reads and the import lifecycle run through. */
  store: ExamWorkspaceStore;
  /** The edit-lease tab a guest QTI import writes the browser slot as. */
  tabId: () => string;
  /** An import started here names its exam, for the import-time points check (TASK-SKRIPT-40-04-23). */
  noteImportStarted: (lineageId: string) => void;
};

/** The one status request in flight and the poll chain it belongs to. */
export type ConversionPollState = {
  generation: number;
  timer: ReturnType<typeof setTimeout> | null;
  /** The one-second clock behind the phase's elapsed time; runs while a conversion is followed. */
  clock: ReturnType<typeof setInterval> | null;
  failures: number;
  request: Promise<void> | null;
};

/** Mutable page state shared by the conversion import, poll and revision sync. */
export type ExamWorkspaceConversionRuntime = {
  binding: ExamWorkspaceConversionBinding;
  /** Opens a saved document by its lineage id, as the Öppna list's open command does. */
  openImported: (lineageId: string) => Promise<ExamWorkspaceRouteOpenOutcome>;
  conversionStatus: Ref<ExamWorkspaceConversionStatus | null>;
  isConverting: Ref<boolean>;
  isImporting: Ref<boolean>;
  conversionError: Ref<string | null>;
  /** Units of `binding.serverDocument` while its conversion runs; null otherwise. */
  shownUnits: Ref<ExamWorkspaceConversionUnit[] | null>;
  poll: ConversionPollState;
  /** Browser time in ms, advanced once a second while a conversion is followed. */
  now: Ref<number>;
};

export function createConversionRuntime(
  binding: ExamWorkspaceConversionBinding,
  openImported: (lineageId: string) => Promise<ExamWorkspaceRouteOpenOutcome>,
): ExamWorkspaceConversionRuntime {
  return {
    binding,
    openImported,
    conversionStatus: ref<ExamWorkspaceConversionStatus | null>(null),
    conversionError: ref<string | null>(null),
    isConverting: ref(false),
    isImporting: ref(false),
    now: ref(Date.now()),
    poll: { clock: null, failures: 0, generation: 0, request: null, timer: null },
    shownUnits: ref<ExamWorkspaceConversionUnit[] | null>(null),
  };
}

export function isFinishedStatus(status: ExamWorkspaceConversionStatus): boolean {
  return status.state === "succeeded" || status.state === "failed";
}

/** The open copy stands on the status's revision or a later one, so it holds its results. */
export function holdsConversionRevision(
  summary: ExamWorkspaceDocumentSummary | null,
  status: ExamWorkspaceConversionStatus,
): boolean {
  const revision = status.document_revision;
  return (
    revision === null ||
    (summary?.lineage_id === status.lineage_id && summary.version >= revision)
  );
}

/**
 * The conversion result still belongs to the open exam: when another exam
 * was adopted meanwhile, even under a still-current fence token, the result
 * drops instead of seizing the newer target.
 */
export function isSelectedConversion(
  summary: ExamWorkspaceDocumentSummary | null,
  status: ExamWorkspaceConversionStatus,
): boolean {
  const openLineageId = summary?.lineage_id ?? null;
  return openLineageId === null || openLineageId === status.lineage_id;
}

function clearPollTimer(runtime: ExamWorkspaceConversionRuntime): void {
  if (runtime.poll.timer !== null) {
    clearTimeout(runtime.poll.timer);
    runtime.poll.timer = null;
  }
}

function startConversionClock(runtime: ExamWorkspaceConversionRuntime): void {
  if (runtime.poll.clock !== null) return;
  runtime.now.value = Date.now();
  runtime.poll.clock = setInterval(() => {
    runtime.now.value = Date.now();
  }, CONVERSION_CLOCK_MS);
}

/** Ends the followed conversion's poll timer and its elapsed-time clock. */
export function stopConversionPolling(runtime: ExamWorkspaceConversionRuntime): void {
  clearPollTimer(runtime);
  if (runtime.poll.clock !== null) {
    clearInterval(runtime.poll.clock);
    runtime.poll.clock = null;
  }
}

export function scheduleConversionPoll(
  runtime: ExamWorkspaceConversionRuntime,
  pollGeneration: number,
  refresh: (pollGeneration: number) => void,
): void {
  clearPollTimer(runtime);
  startConversionClock(runtime);
  const delay = Math.min(
    EXAM_WORKSPACE_CONVERSION_POLL_MS * 2 ** Math.max(0, runtime.poll.failures - 1),
    CONVERSION_MAX_POLL_MS,
  );
  runtime.poll.timer = setTimeout(() => {
    runtime.poll.timer = null;
    refresh(pollGeneration);
  }, delay);
}

/** The opened exam is the success state; toasts report failures only (user rule 2026-10-17). */
export function finishConversion(
  runtime: ExamWorkspaceConversionRuntime,
  status: ExamWorkspaceConversionStatus,
): void {
  runtime.conversionStatus.value = status;
  runtime.isConverting.value = false;
  runtime.shownUnits.value = null;
  runtime.conversionError.value = null;
  stopConversionPolling(runtime);
}
