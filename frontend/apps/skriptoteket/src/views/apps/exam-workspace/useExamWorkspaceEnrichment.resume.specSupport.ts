/**
 * Shared setup for the useExamWorkspaceEnrichment resume responsibility specs
 * (TASK-SKRIPT-40-04-14, rereview 5 V6 and R5-N1).
 *
 * The lost suggestion-job fixtures plus the composed workspace harness: the
 * suggestion status builder with an explicitly typed message option, the
 * saved-version exam responses, the per-opening lookup helpers, and the
 * untouched/delivered assertions. Each responsibility spec keeps its own api
 * doubles and calls `setupResumeEnv`; nothing here is duplicated per spec.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { expect, vi, type Mock } from "vitest";
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
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";
import { buildResponse, currentItem, deferred } from "./useExamWorkspaceDocument.specSupport";
import { useExamWorkspaceEnrichment } from "./useExamWorkspaceEnrichment";

/** The api double each resume spec mocks "../../../api/examWorkspace" with. */
export type ResumeApiMocks = {
  findExamWorkspaceAnswerKeySuggestions: Mock;
  getExamWorkspaceAnswerKeySuggestions: Mock;
  getExamWorkspaceConversionStatus: Mock;
  getExamWorkspaceDocument: Mock;
  importExamWorkspaceDocument: Mock;
  listExamWorkspaceDocuments: Mock;
  requestExamWorkspaceAnswerKeySuggestions: Mock;
};

/** The api double each resume spec mocks "../../../api/examWorkspaceExports" with. */
export type ResumeExportApiMocks = {
  downloadExamWorkspaceExport: Mock;
};

export const SUGGESTION: NativeAnswerKeySuggestion = {
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

export function keylessItem(): NativeExamItem {
  return buildMatchingItem({
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
  });
}

export function examResponse(lineageId: string, revision = 1): ExamWorkspaceDocumentResponse {
  const base = buildResponse(keylessItem());
  const document = { ...base.document, document_id: lineageId, revision };
  return {
    ...base,
    document,
    saved_document: document,
    summary: { ...base.summary, lineage_id: lineageId, version: revision },
  };
}

export type ResumeJobStatusOptions = {
  jobId?: string;
  withSuggestion?: boolean;
  message?: string | null;
};

export function jobStatus(
  state: ExamWorkspaceAnswerKeySuggestionsStatus["state"],
  { jobId = "job-a", withSuggestion = false, message = null }: ResumeJobStatusOptions = {},
): ExamWorkspaceAnswerKeySuggestionsStatus {
  return {
    job_id: jobId,
    lineage_id: "lineage-a",
    message,
    state,
    suggestions: withSuggestion ? [{ item_id: "item_001", suggestion: SUGGESTION }] : [],
  };
}

export const LOOKUP_FAILURE_COPY = "Kunde inte hämta väntande facitförslag.";

export function lookupFailureToasts(): number {
  return useToastStore().toasts.filter((toast) => toast.message === LOOKUP_FAILURE_COPY).length;
}

/** Fake timers, teacher identity and reset doubles; a lookup finds no job unless held. */
export function setupResumeEnv(api: ResumeApiMocks, exportApi: ResumeExportApiMocks): void {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  setActivePinia(createPinia());
  useAuthStore().user = {
    id: "teacher-a", email: "teacher-a@example.test", role: "admin", auth_provider: "local",
  };
  for (const mock of [...Object.values(api), ...Object.values(exportApi)]) {
    mock.mockReset();
  }
  api.findExamWorkspaceAnswerKeySuggestions.mockResolvedValue(null);
}

/** Restore real timers. Each spec wires this into its own `afterEach`. */
export function teardownResumeEnv(): void {
  vi.clearAllTimers();
  vi.useRealTimers();
}

export function composeWorkspace() {
  const scope = effectScope();
  const composed = scope.run(() => {
    const document = useExamWorkspaceDocument({ beginOpenGeneration: () => undefined, store: serverExamWorkspaceStore });
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

export async function open(
  state: ReturnType<typeof useExamWorkspaceDocument>,
  lineageId: string,
  api: ResumeApiMocks,
): Promise<void> {
  api.getExamWorkspaceDocument.mockResolvedValueOnce(examResponse(lineageId));
  await state.openDocument(lineageId);
}

/** Open exam A while its lookup is held; returns the held lookup. */
export async function openAWithLookupHeld(api: ResumeApiMocks) {
  const composed = composeWorkspace();
  const lookup = deferred<ExamWorkspaceAnswerKeySuggestionsStatus | null>();
  api.findExamWorkspaceAnswerKeySuggestions.mockReturnValueOnce(lookup.promise);
  await open(composed.document, "lineage-a", api);
  await flushPromises();
  return { ...composed, lookup };
}

export function expectUntouched(state: ReturnType<typeof useExamWorkspaceDocument>): void {
  expect(currentItem(state).ai_suggestion ?? null).toBeNull();
  expect(currentItem(state).answer_key.origin).toBe("absent");
  expect(state.isDirty.value).toBe(false);
}

export function expectDelivered(state: ReturnType<typeof useExamWorkspaceDocument>): void {
  expect(currentItem(state).ai_suggestion).toEqual(SUGGESTION);
  expect(currentItem(state).answer_key.origin).toBe("machine_proposed");
  expect(state.isDirty.value).toBe(true);
}
