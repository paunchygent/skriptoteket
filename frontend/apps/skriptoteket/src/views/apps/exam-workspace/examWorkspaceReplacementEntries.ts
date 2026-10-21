/**
 * Exam workspace replacement entries (TASK-SKRIPT-40-04-21, F1).
 *
 * Domain purpose:
 *   The deferred-entry vocabulary behind the gate-owned replacement
 *   coordinator: one typed deferred entry per intent kind, the
 *   duplicate-submit match per kind, and the per-kind resolution of a
 *   replaced or terminated entry. Replacing the slot resolves its former
 *   caller at once; callers never wait in a queue. Spara som and Nytt prov
 *   know no superseded outcome: an obsolete copy never runs, so a replaced
 *   or terminated copy resolves "failed".
 *
 * Relationships:
 *   - Owned by `examWorkspaceReplacementCoordinator`, which stays the only
 *     replacement owner and keeps the desired/selected state; the entry
 *     types still come from `examWorkspaceReplacementTypes`.
 */

import type {
  ExamWorkspaceNewExamOutcome,
  ExamWorkspaceReplacementDesired,
  ExamWorkspaceReplacementNewExamEntry,
  ExamWorkspaceReplacementRouteEntry,
  ExamWorkspaceReplacementSaveAsEntry,
  ExamWorkspaceRouteOpenOutcome,
  ExamWorkspaceSaveAsOutcome,
} from "./examWorkspaceReplacementTypes";

function defer<Outcome>(): {
  promise: Promise<Outcome>;
  resolve: (outcome: Outcome) => void;
} {
  let resolve: (outcome: Outcome) => void = () => undefined;
  const promise = new Promise<Outcome>((run) => {
    resolve = run;
  });
  return { promise, resolve };
}

/** One immutable route request with its deferred outcome. */
export function createRouteEntry(lineage: string): ExamWorkspaceReplacementRouteEntry {
  const deferred = defer<ExamWorkspaceRouteOpenOutcome>();
  return {
    intent: { kind: "route", lineage },
    kind: "route",
    promise: deferred.promise,
    resolve: deferred.resolve,
  };
}

/** One immutable Spara som request with its deferred outcome. */
export function createSaveAsEntry(source: string, name: string): ExamWorkspaceReplacementSaveAsEntry {
  const deferred = defer<ExamWorkspaceSaveAsOutcome>();
  return {
    intent: { kind: "saveAs", name, source },
    kind: "saveAs",
    promise: deferred.promise,
    resolve: deferred.resolve,
  };
}

/** One immutable Nytt prov request with its deferred outcome. */
export function createNewExamEntry(
  source: string | null,
  expectedCursor: string | null,
): ExamWorkspaceReplacementNewExamEntry {
  const deferred = defer<ExamWorkspaceNewExamOutcome>();
  return {
    intent: { expectedCursor, kind: "newExam", source },
    kind: "newExam",
    promise: deferred.promise,
    resolve: deferred.resolve,
  };
}

/** A duplicate submit while the same route entry is desired returns its promise. */
export function isDuplicateRoute(
  current: ExamWorkspaceReplacementDesired | null,
  lineage: string,
): current is ExamWorkspaceReplacementRouteEntry {
  return current !== null && current.kind === "route" && current.intent.lineage === lineage;
}

/** A duplicate submit while the same Spara som entry is desired returns its promise. */
export function isDuplicateSaveAs(
  current: ExamWorkspaceReplacementDesired | null,
  source: string,
  name: string,
): current is ExamWorkspaceReplacementSaveAsEntry {
  return (
    current !== null &&
    current.kind === "saveAs" &&
    current.intent.source === source &&
    current.intent.name === name
  );
}

/** A duplicate submit while the same Nytt prov entry is desired returns its promise. */
export function isDuplicateNewExam(
  current: ExamWorkspaceReplacementDesired | null,
  source: string | null,
  expectedCursor: string | null,
): current is ExamWorkspaceReplacementNewExamEntry {
  return (
    current !== null &&
    current.kind === "newExam" &&
    current.intent.source === source &&
    current.intent.expectedCursor === expectedCursor
  );
}

/**
 * Replace the slot: its former caller resolves at once and never waits. A
 * route knows the superseded outcome; a copy never runs once obsolete.
 */
export function resolveReplaced(entry: ExamWorkspaceReplacementDesired): void {
  switch (entry.kind) {
    case "route":
      entry.resolve("superseded");
      break;
    case "saveAs":
      entry.resolve("failed");
      break;
    case "newExam":
      entry.resolve("failed");
      break;
    case "recover":
      break;
  }
}

/**
 * Terminate the currently desired departure: keep the source and its work.
 * Every intent but recovery reports the failure to its caller.
 */
export function resolveTerminated(entry: ExamWorkspaceReplacementDesired): void {
  switch (entry.kind) {
    case "route":
      entry.resolve("failed");
      break;
    case "saveAs":
      entry.resolve("failed");
      break;
    case "newExam":
      entry.resolve("failed");
      break;
    case "recover":
      break;
  }
}

/** True while the entry holds the copy busy: Spara som and Nytt prov. */
export function holdsCopyBusy(entry: { kind: string }): boolean {
  return entry.kind === "saveAs" || entry.kind === "newExam";
}
