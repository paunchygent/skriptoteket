/**
 * Exam workspace answer-key suggestion slice test harness.
 *
 * Slice purpose:
 *   Lock the AI suggestion loop: request suggestions for the questions as
 *   the editor shows them, poll until the job settles, and write each
 *   arriving suggestion onto its question.
 *
 * Relationships:
 *   - Shared fixtures and interactions for the enrichment specs.
 *   - Builds on `ExamWorkspaceSlice.specSupport.ts` for the document fixture
 *     and view mounting.
 *   - Each spec owns its own `api/examWorkspace` module mock and passes it in.
 */

import { flushPromises } from "@vue/test-utils";
import type { Mock } from "vitest";

import type {
  ExamWorkspaceAnswerKeySuggestionsStatus,
  ExamWorkspaceConversionStatus,
  ExamWorkspaceDocumentResponse,
  NativeAnswerKeySuggestion,
  NativeExamItem,
} from "../../api/examWorkspace";
import { buildResponse, type ViewWrapper } from "./ExamWorkspaceSlice.specSupport";

/** The `api/examWorkspace` module mock every enrichment spec declares. */
export interface EnrichmentApiMocks {
  findExamWorkspaceAnswerKeySuggestions: Mock;
  getExamWorkspaceAnswerKeySuggestions: Mock;
  getExamWorkspaceDocument: Mock;
  getExamWorkspaceHistory: Mock;
  getExamWorkspaceHistoryStep: Mock;
  moveExamWorkspaceHistoryPosition: Mock;
  storeExamWorkspaceUndoStep: Mock;
  importExamWorkspaceDocument: Mock;
  getExamWorkspaceConversionStatus: Mock;
  listExamWorkspaceDocuments: Mock;
  requestExamWorkspaceAnswerKeySuggestions: Mock;
}

/** The finished import conversion that every imported revision 1 carries. */
export const SUCCEEDED_CONVERSION: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};

/** Item 2 arrives without a key, so it is the one the provider suggests for. */
export function buildUnkeyedResponse(
  version: number,
  conversion: ExamWorkspaceConversionStatus | null = null,
): ExamWorkspaceDocumentResponse {
  const response = buildResponse({ conversion, version });
  return {
    ...response,
    document: {
      ...response.document,
      items: response.document.items.map((item) =>
        item.item_id === "item_002"
          ? {
              ...item,
              answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
              review: { ...item.review, reasons: ["facit saknas"], state: "review_required" },
            }
          : item,
      ),
    },
  };
}

export const SUGGESTION: NativeAnswerKeySuggestion = {
  correct_choice_ids: ["choice_003"],
  fingerprint: "a".repeat(64),
  gap_accepted_values: [],
  match_pairs: [],
  model: "luna-low",
  prompt_template_version: "v1",
  provider_profile_id: "luna",
};

export function status(
  state: ExamWorkspaceAnswerKeySuggestionsStatus["state"],
  extra: Partial<ExamWorkspaceAnswerKeySuggestionsStatus> = {},
): ExamWorkspaceAnswerKeySuggestionsStatus {
  return { job_id: "job-suggest-1", lineage_id: "lineage-1", suggestions: [], state, ...extra };
}

export const SUCCEEDED = status("succeeded", {
  suggestions: [{ item_id: "item_002", suggestion: SUGGESTION }],
});

/** Resets every API mock and imports an unkeyed document with no job requested. */
export function resetEnrichmentApiMocks(apiMocks: EnrichmentApiMocks): void {
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(SUCCEEDED_CONVERSION);
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(buildUnkeyedResponse(1, SUCCEEDED_CONVERSION));
    return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null, summary: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
  });
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
}

export function lastSavedItem(saveMock: Mock, itemId: string): NativeExamItem | undefined {
  const calls = saveMock.mock.calls;
  const [, params] = calls[calls.length - 1] as [
    string,
    { document: { items: NativeExamItem[] } },
  ];
  return params.document.items.find((item) => item.item_id === itemId);
}

export async function requestProposals(wrapper: ViewWrapper) {
  await wrapper.find('[data-test="exam-workspace-suggest-all"]').trigger("click");
  await flushPromises();
}
