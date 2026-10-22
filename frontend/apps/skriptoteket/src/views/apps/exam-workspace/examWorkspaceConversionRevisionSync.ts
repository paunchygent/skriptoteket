/**
 * Exam workspace conversion revision sync.
 *
 * Domain purpose:
 *   Show a newer revision of the followed import's exam. The first one
 *   replaces the open exam; a later one is merged into the teacher's copy
 *   with the units its own response names, so a later revision another tab
 *   saved on top of the conversion's merges the same way. Awaiting an
 *   in-flight save defers the merge, and a save conflict reconciles through
 *   the same revision check.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceConversion` through the shared conversion
 *     runtime; status polling resumes through the injected `scheduleNext`
 *     hook so this module never owns the timer.
 */

import type { ExamWorkspaceConversionStatus } from "../../../api/examWorkspace";
import { mergeConversionRevision, sameDocument } from "./examWorkspaceConversionMerge";
import type { ExamWorkspaceConversionRuntime } from "./examWorkspaceConversionShared";
import {
  finishConversion,
  holdsConversionRevision,
  isSelectedConversion,
} from "./examWorkspaceConversionShared";

/** What a save conflict turned out to be, once the conversion revision was checked. */
export type ConflictSync = "merged" | "unrelated" | "unknown";

export function createConversionRevisionSync(
  runtime: ExamWorkspaceConversionRuntime,
  scheduleNext: (pollGeneration: number) => void,
) {
  const { binding } = runtime;

  /**
   * Show a newer revision of the followed import's exam. Returns true when a
   * newer revision waits for an in-flight save, so the caller polls again
   * before finishing. A fetched revision without its conversion throws like a
   * failed fetch: the copy, its lock and the shown units stay as they are.
   */
  async function applyRevision(
    status: ExamWorkspaceConversionStatus,
    pollGeneration: number,
    duringSave = false,
  ): Promise<boolean> {
    if (status.document_revision === null || holdsConversionRevision(binding.summary.value, status)) {
      return false;
    }
    if (binding.isSaving() && !duringSave) return true;
    const first = binding.summary.value?.lineage_id !== status.lineage_id;
    if (first) {
      // The converted exam is not open: open it through the coordinator's
      // entrance, which reads, installs, adopts, claims and publishes it.
      // Later revisions merge below once it is open. The import holds the
      // document like the QTI open does, so its busy clears first. A refused
      // or failed open keeps polling (the readback retries); a superseded one
      // ends following here, since the teacher's own navigation won.
      runtime.isImporting.value = false;
      runtime.isConverting.value = false;
      const outcome = await runtime.openImported(status.lineage_id);
      if (outcome === "superseded") {
        finishConversion(runtime, status);
      } else if (outcome !== "installed") {
        runtime.isImporting.value = true;
        runtime.isConverting.value = true;
      }
      return false;
    }
    const shown = runtime.shownUnits.value ?? [];
    const fence = binding.getFence();
    const token = fence.begin();
    const reconcile = binding.beginDocumentRead();
    const response = reconcile(
      await binding.store.shared.getExamWorkspaceDocument(status.lineage_id),
    );
    if (!binding.isCurrent(token)) return false;
    if (pollGeneration !== runtime.poll.generation || !binding.isCurrent(token)) return false;
    if (!isSelectedConversion(binding.summary.value, status)) return false;
    const conversion = response.conversion;
    if (conversion === null) {
      // Only the response's own conversion names the units of its head: reconcile like a failed fetch.
      throw new Error("The followed exam's revision came without its conversion.");
    }
    const local = binding.workspaceDocument.value;
    const base = binding.serverDocument.value;
    if (!local || !base || sameDocument(local, base)) {
      // Nothing edited since the base: take the head as is. An autosave
      // stores the copy without fetching, so the saved baseline can stand
      // ahead of this base; the merge still runs while the copy differs.
      binding.applyResponse(token, response);
    } else {
      const merged = mergeConversionRevision({
        base,
        baseUnits: shown,
        head: response.document,
        headUnits: conversion.units,
        local,
      });
      binding.applyResponse(token, response, merged);
    }
    return false;
  }

  /**
   * After a save conflict on the converting exam, merge the revision
   * conversion wrote meanwhile, waiting for a status request already in
   * flight first. Returns "merged" when the open copy now stands on a newer
   * revision than the failed save expected, so the caller can save again
   * without losing edits; "unrelated" when conversion wrote no revision newer
   * than the failed save's; and "unknown" when conversion did but it could not
   * be merged (the fetch failed or came without its conversion), so the caller keeps the teacher's copy and
   * the next poll merges it. Outside conversion it returns "unrelated".
   */
  async function syncAfterConflict(expectedRevision: number): Promise<ConflictSync> {
    const teacher = binding.store.teacher;
    if (!teacher) return "unrelated";
    const pollGeneration = runtime.poll.generation;
    while (runtime.poll.request) await runtime.poll.request;
    const status = runtime.conversionStatus.value;
    const isEditingConversion =
      runtime.shownUnits.value !== null &&
      binding.summary.value?.lineage_id === status?.lineage_id;
    if (pollGeneration !== runtime.poll.generation || !status || !isEditingConversion) {
      return "unrelated";
    }
    let conversionRevision = 0;
    const request = (async () => {
      const next = await teacher.getExamWorkspaceConversionStatus(status.job_id);
      if (pollGeneration !== runtime.poll.generation) return;
      runtime.conversionStatus.value = next;
      conversionRevision = next.document_revision ?? 0;
      await applyRevision(next, pollGeneration, true);
    })().finally(() => {
      runtime.poll.request = null;
    });
    runtime.poll.request = request;
    try {
      await request;
    } catch {
      return "unknown";
    }
    if (pollGeneration !== runtime.poll.generation) return "unknown";
    // The poll chain may have found this request pending and ended; resume it.
    if (runtime.isConverting.value && runtime.poll.timer === null) scheduleNext(pollGeneration);
    if ((binding.summary.value?.version ?? 0) > expectedRevision) return "merged";
    return conversionRevision > expectedRevision ? "unknown" : "unrelated";
  }

  return { applyRevision, syncAfterConflict };
}
