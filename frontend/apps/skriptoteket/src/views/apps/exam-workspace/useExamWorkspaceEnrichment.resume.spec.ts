/**
 * A suggestion job this page lost is found again when an exam opens
 * (TASK-SKRIPT-39-04-09 P1, P2, P7).
 *
 * Expected behavior:
 *   Every new opening asks for the newest job requested on its saved
 *   version. A queued or running job is polled, a finished job's suggestions
 *   are written through the same arrival path as any job of this opening.
 *   The answer is admitted only if, when it lands, the opening is still open,
 *   its copy still stands on the asked-for saved version, and the teacher has
 *   not started a job of their own there. Same-exam replacements keep the
 *   opening and ask nothing. A failed lookup is shown with a retry that asks
 *   again, only while the opening that asked is still open.
 *
 * Rows follow the case tables (C1-C16) in the retained design note
 * `evidence/implementation/TASK-SKRIPT-39-04-09/design.md` and, for the
 * failed lookup that replaces C12, (F2-a to F2-i) in `repair1/design.md`.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import type {
  ExamWorkspaceAnswerKeySuggestionsStatus,
  ExamWorkspaceDocumentResponse,
  NativeAnswerKeySuggestion,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { useAuthStore } from "../../../stores/auth";
import { useToastStore } from "../../../stores/toast";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { buildResponse, currentItem, deferred } from "./useExamWorkspaceDocument.specSupport";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";
import {
  EXAM_WORKSPACE_ENRICHMENT_MAX_POLL_MS,
  EXAM_WORKSPACE_ENRICHMENT_POLL_MS,
  useExamWorkspaceEnrichment,
} from "./useExamWorkspaceEnrichment";

const apiMocks = vi.hoisted(() => ({
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  requestExamWorkspaceAnswerKeySuggestions: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const SUGGESTION: NativeAnswerKeySuggestion = {
  correct_choice_ids: [],
  fingerprint: "a".repeat(64),
  gap_accepted_values: [],
  match_pairs: [
    { left_id: "left_001", right_id: "right_001" },
    { left_id: "left_002", right_id: "right_002" },
    { left_id: "left_003", right_id: "right_003" },
  ],
  model: "model",
  prompt_template_version: "v1",
  provider_profile_id: "profile",
};

function keylessItem(): NativeExamItem {
  return buildMatchingItem({
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
  });
}

function examResponse(lineageId: string, revision = 1): ExamWorkspaceDocumentResponse {
  const base = buildResponse(keylessItem());
  const document = { ...base.document, document_id: lineageId, revision };
  return {
    ...base,
    document,
    saved_document: document,
    summary: { ...base.summary, lineage_id: lineageId, version: revision },
  };
}

function jobStatus(
  state: ExamWorkspaceAnswerKeySuggestionsStatus["state"],
  { jobId = "job-a", withSuggestion = false, message = null as string | null } = {},
): ExamWorkspaceAnswerKeySuggestionsStatus {
  return {
    job_id: jobId,
    lineage_id: "lineage-a",
    message,
    state,
    suggestions: withSuggestion ? [{ item_id: "item_001", suggestion: SUGGESTION }] : [],
  };
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  setActivePinia(createPinia());
  useAuthStore().user = {
    id: "teacher-a", email: "teacher-a@example.test", role: "admin", auth_provider: "local",
  };
  for (const mock of [...Object.values(apiMocks), ...Object.values(exportApiMocks)]) {
    mock.mockReset();
  }
  apiMocks.findExamWorkspaceAnswerKeySuggestions.mockResolvedValue(null);
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
});

function composeWorkspace() {
  const scope = effectScope();
  const composed = scope.run(() => {
    const document = useExamWorkspaceDocument({ store: serverExamWorkspaceStore });
    const enrichment = useExamWorkspaceEnrichment({
      applySuggestions: document.applyArrivingSuggestions,
      document: document.workspaceDocument,
      isOpen: document.isOpen,
      openExam: document.openExam,
      savedRevision: document.savedRevision,
      teacher: serverExamWorkspaceStore.teacher,
    });
    return { document, enrichment };
  });
  if (!composed) {
    throw new Error("expected the composed workspace state");
  }
  return { ...composed, scope };
}

async function open(
  state: ReturnType<typeof useExamWorkspaceDocument>,
  lineageId: string,
): Promise<void> {
  apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(examResponse(lineageId));
  await state.openDocument(lineageId);
}

/** Open exam A while its lookup is held; returns the held lookup. */
async function openAWithLookupHeld() {
  const composed = composeWorkspace();
  const lookup = deferred<ExamWorkspaceAnswerKeySuggestionsStatus | null>();
  apiMocks.findExamWorkspaceAnswerKeySuggestions.mockReturnValueOnce(lookup.promise);
  await open(composed.document, "lineage-a");
  await flushPromises();
  return { ...composed, lookup };
}

function expectUntouched(state: ReturnType<typeof useExamWorkspaceDocument>): void {
  expect(currentItem(state).ai_suggestion ?? null).toBeNull();
  expect(currentItem(state).answer_key.origin).toBe("absent");
  expect(state.isDirty.value).toBe(false);
}

function expectDelivered(state: ReturnType<typeof useExamWorkspaceDocument>): void {
  expect(currentItem(state).ai_suggestion).toEqual(SUGGESTION);
  expect(currentItem(state).answer_key.origin).toBe("machine_proposed");
  expect(state.isDirty.value).toBe(true);
}

describe("an exam opening asks for its lost job", () => {
  it("C1: no job leaves the exam as opened and polls nothing", async () => {
    const { document, enrichment } = composeWorkspace();
    await open(document, "lineage-a");
    await flushPromises();

    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledWith("lineage-a", 1);
    expectUntouched(document);
    expect(enrichment.enrichmentStatus.value).toBeNull();
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_MAX_POLL_MS);
    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).not.toHaveBeenCalled();
  });

  it("C4: a succeeded job arrives on its question, unsaved, as if no reload happened", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld();

    lookup.resolve(jobStatus("succeeded", { withSuggestion: true }));
    await flushPromises();

    expectDelivered(document);
    expect(enrichment.enrichmentMessage.value).toBe("1 facitförslag har lagts in på frågorna.");
  });

  it("C2/C3: a running job is polled in this opening and delivers when it finishes", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld();
    lookup.resolve(jobStatus("running"));
    await flushPromises();
    expect(enrichment.isEnrichmentPending.value).toBe(true);
    expectUntouched(document);

    apiMocks.getExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(
      jobStatus("succeeded", { withSuggestion: true }),
    );
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);

    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledWith(
      "lineage-a",
      "job-a",
    );
    expectDelivered(document);
  });

  it("C2: a resumed pending job blocks a second request in the same opening", async () => {
    const { enrichment, lookup } = await openAWithLookupHeld();
    lookup.resolve(jobStatus("queued"));
    await flushPromises();

    await enrichment.requestSuggestionsForAll();

    expect(apiMocks.requestExamWorkspaceAnswerKeySuggestions).not.toHaveBeenCalled();
  });

  it("C5: a failed job delivers its partial suggestions with its failure message", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld();

    lookup.resolve(jobStatus("failed", { withSuggestion: true, message: "Budget slut." }));
    await flushPromises();

    expectDelivered(document);
    expect(enrichment.enrichmentMessage.value).toBe("Budget slut.");
  });

});

const LOOKUP_FAILURE_COPY = "Kunde inte hämta väntande facitförslag.";

function lookupFailureToasts(): number {
  return useToastStore().toasts.filter((toast) => toast.message === LOOKUP_FAILURE_COPY).length;
}

describe("a failed lookup is shown and can be retried (C12)", () => {
  it("F2-a: the failure is shown once, delivers nothing and is not rerun on its own", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld();

    lookup.reject(new Error("network"));
    await flushPromises();
    expect(lookupFailureToasts()).toBe(1);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_MAX_POLL_MS);

    expectUntouched(document);
    expect(enrichment.enrichmentStatus.value).toBeNull();
    expect(enrichment.enrichmentLookupError.value).toBe(LOOKUP_FAILURE_COPY);
    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(1);
  });

  it("F2-b: retry asks again for the same saved version and delivers the found job", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld();
    lookup.reject(new Error("network"));
    await flushPromises();

    apiMocks.findExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(
      jobStatus("succeeded", { withSuggestion: true }),
    );
    await enrichment.retryEnrichmentLookup();
    await flushPromises();

    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions.mock.calls).toEqual([
      ["lineage-a", 1],
      ["lineage-a", 1],
    ]);
    expectDelivered(document);
    expect(enrichment.enrichmentLookupError.value).toBeNull();
  });

  it("F2-c: a retry that fails again shows the failure again", async () => {
    const { enrichment, lookup } = await openAWithLookupHeld();
    lookup.reject(new Error("network"));
    await flushPromises();

    apiMocks.findExamWorkspaceAnswerKeySuggestions.mockRejectedValueOnce(new Error("500"));
    await enrichment.retryEnrichmentLookup();
    await flushPromises();

    expect(enrichment.enrichmentLookupError.value).toBe(LOOKUP_FAILURE_COPY);
    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(2);
  });

  it("F2-d: a retry that finds no job clears the failure", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld();
    lookup.reject(new Error("network"));
    await flushPromises();

    await enrichment.retryEnrichmentLookup();
    await flushPromises();

    expectUntouched(document);
    expect(enrichment.enrichmentLookupError.value).toBeNull();
    expect(enrichment.enrichmentStatus.value).toBeNull();
  });

  it("F2-h: the teacher's own request clears the failure", async () => {
    const { enrichment, lookup } = await openAWithLookupHeld();
    lookup.reject(new Error("network"));
    await flushPromises();
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(
      jobStatus("queued", { jobId: "job-b" }),
    );

    await enrichment.requestSuggestionsForAll();

    expect(enrichment.enrichmentLookupError.value).toBeNull();
    expect(enrichment.enrichmentStatus.value?.job_id).toBe("job-b");
  });

  it("F2-i: a failure landing while the teacher's own request is in flight is not shown", async () => {
    const { enrichment, lookup } = await openAWithLookupHeld();
    const request = deferred<ExamWorkspaceAnswerKeySuggestionsStatus>();
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockReturnValueOnce(request.promise);
    const requesting = enrichment.requestSuggestionsForAll();

    lookup.reject(new Error("network"));
    await flushPromises();
    request.resolve(jobStatus("queued", { jobId: "job-b" }));
    await requesting;

    expect(enrichment.enrichmentLookupError.value).toBeNull();
    expect(lookupFailureToasts()).toBe(0);
  });
});

describe("a failed lookup affects only the opening that asked", () => {
  it("F2-e: A's failure landing after B opened shows nothing on B", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld();
    await open(document, "lineage-b");
    await flushPromises();

    lookup.reject(new Error("network"));
    await flushPromises();

    expect(document.summary.value?.lineage_id).toBe("lineage-b");
    expect(enrichment.enrichmentLookupError.value).toBeNull();
    expect(lookupFailureToasts()).toBe(0);
    await enrichment.retryEnrichmentLookup();
    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions.mock.calls).toEqual([
      ["lineage-a", 1],
      ["lineage-b", 1],
    ]);
  });

  it("F2-f: an earlier opening's failure does not reach a later opening of the same exam", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld();
    await open(document, "lineage-b");
    await open(document, "lineage-a");
    await flushPromises();

    lookup.reject(new Error("network"));
    await flushPromises();

    expect(enrichment.enrichmentLookupError.value).toBeNull();
    expect(lookupFailureToasts()).toBe(0);
  });

  it("F2-g: a failure landing after disposal shows nothing", async () => {
    const { enrichment, lookup, scope } = await openAWithLookupHeld();
    scope.stop();

    lookup.reject(new Error("network"));
    await flushPromises();

    expect(enrichment.enrichmentLookupError.value).toBeNull();
    expect(lookupFailureToasts()).toBe(0);
  });
});

describe("the answer is admitted only when it lands on the opening that asked", () => {
  it("C8: the copy was saved to a newer version while the lookup was in flight", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld();
    apiMocks.saveExamWorkspaceDocument.mockResolvedValueOnce(examResponse("lineage-a", 2));
    await document.saveDocument("position-1");
    expect(document.savedRevision.value).toBe(2);

    lookup.resolve(jobStatus("succeeded", { withSuggestion: true }));
    await flushPromises();

    expectUntouched(document);
    expect(enrichment.enrichmentStatus.value).toBeNull();
  });

  it("C11: another exam was opened before the lookup landed", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld();
    await open(document, "lineage-b");
    await flushPromises();

    lookup.resolve(jobStatus("succeeded", { withSuggestion: true }));
    await flushPromises();

    expect(document.summary.value?.lineage_id).toBe("lineage-b");
    expectUntouched(document);
    expect(enrichment.enrichmentStatus.value).toBeNull();
  });

  it("C10: the teacher's own request in this opening wins over a later lookup", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld();
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(
      jobStatus("queued", { jobId: "job-b" }),
    );
    await enrichment.requestSuggestionsForAll();

    lookup.resolve(jobStatus("succeeded", { withSuggestion: true }));
    await flushPromises();

    expectUntouched(document);
    expect(enrichment.enrichmentStatus.value?.job_id).toBe("job-b");
  });

  it("C10: a lookup landing while the teacher's request is in flight is dropped", async () => {
    const { document, enrichment, lookup } = await openAWithLookupHeld();
    const request = deferred<ExamWorkspaceAnswerKeySuggestionsStatus>();
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockReturnValueOnce(request.promise);
    const requesting = enrichment.requestSuggestionsForAll();

    lookup.resolve(jobStatus("succeeded", { withSuggestion: true }));
    await flushPromises();
    expectUntouched(document);

    request.resolve(jobStatus("queued", { jobId: "job-b" }));
    await requesting;
    expect(enrichment.enrichmentStatus.value?.job_id).toBe("job-b");
  });

  it("disposal before the lookup lands applies nothing", async () => {
    const { document, lookup, scope } = await openAWithLookupHeld();
    scope.stop();

    lookup.resolve(jobStatus("succeeded", { withSuggestion: true }));
    await flushPromises();

    expectUntouched(document);
  });
});

describe("which openings ask", () => {
  it("C15: switching back to an exam finds the job its earlier opening lost", async () => {
    const { document, enrichment } = composeWorkspace();
    await open(document, "lineage-a");
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(jobStatus("queued"));
    await enrichment.requestSuggestionsForAll();
    await open(document, "lineage-b");
    await flushPromises();

    apiMocks.findExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(
      jobStatus("succeeded", { withSuggestion: true }),
    );
    await open(document, "lineage-a");
    await flushPromises();

    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions.mock.calls).toEqual([
      ["lineage-a", 1],
      ["lineage-b", 1],
      ["lineage-a", 1],
    ]);
    expect(document.summary.value?.lineage_id).toBe("lineage-a");
    expectDelivered(document);
  });

  it("C13/C14: a same-exam reload keeps the opening and asks nothing", async () => {
    const { document } = composeWorkspace();
    await open(document, "lineage-a");
    await flushPromises();
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(examResponse("lineage-a"));

    await document.reloadDocument();
    await flushPromises();

    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(1);
  });

  it("C16 (P7): a resumed running job delivers across a later save", async () => {
    const { document, lookup } = await openAWithLookupHeld();
    lookup.resolve(jobStatus("running"));
    await flushPromises();
    apiMocks.saveExamWorkspaceDocument.mockResolvedValueOnce(examResponse("lineage-a", 2));
    await document.saveDocument("position-1");

    apiMocks.getExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(
      jobStatus("succeeded", { withSuggestion: true }),
    );
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);

    expect(document.savedRevision.value).toBe(2);
    expectDelivered(document);
  });
});
