/**
 * Exam workspace retry slice behavior (TASK-SKRIPT-39-05-09 D1).
 *
 * Slice purpose:
 *   Lock the wiring from the review drawer to the one-question retry route:
 *   the drawer shows the labeler's first type and a "Konvertera igen" button,
 *   the view sends the draft document, question and chosen type, and the
 *   converted reply replaces only that question in the editor. The open
 *   document's picture URLs reach the item editor, and a reply that comes
 *   back as a review item keeps the teacher's chosen type in the selector.
 */

import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamItem,
  NativeExamItemKind,
} from "../../api/examWorkspace";
import ExamWorkspaceItemEditor from "./exam-workspace/ExamWorkspaceItemEditor.vue";
import { buildResponse, mountExamWorkspace } from "./ExamWorkspaceSlice.specSupport";
import type { ViewWrapper } from "./ExamWorkspaceSlice.specSupport";

type NativeExamAsset = ExamWorkspaceDocumentResponse["document"]["assets"][number];

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  examWorkspaceAssetUrl: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  retryExamWorkspaceItem: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));

vi.mock("../../api/examWorkspace", () => apiMocks);

function retrySource(labelKind: NativeExamItemKind): NonNullable<NativeExamItem["retry_source"]> {
  return {
    chunks: [
      {
        anchor: "body:0001",
        images: [],
        missing_images: [],
        kind: "question",
        marked_text: "Förklara begreppet.",
        text: "Förklara begreppet.",
      },
    ],
    context_chunks: [],
    key_chunks: [],
    label_kind: labelKind,
  };
}

function reviewItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ai_suggestion: null,
    facit_text: null,
    marking_guide: null,
    printed_label: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    body: [{ segments: [{ kind: "text", text: "Förklara begreppet." }] }],
    choices: [],
    gaps: [],
    item_id: "item_001",
    kind: "free_text",
    match_left: [],
    match_right: [],
    points: 2,
    points_estimated: false,
    review: {
      confidence: 0.4,
      parse_origin: "llm_parsed",
      reasons: ["osäker tolkning"],
      state: "review_required",
    },
    retry_source: retrySource("gap_fill"),
    sequence: 1,
    source_anchor: "body:0001",
    tick_points: null,
    ...overrides,
  };
}

function convertedItem(): NativeExamItem {
  return reviewItem({
    answer_key: {
      correct_choice_ids: [],
      match_pairs: [{ left_id: "left_001", right_id: "right_001" }],
      origin: "source_provided",
    },
    kind: "matching",
    match_left: [{ left_id: "left_001", text: "Första begreppet" }],
    match_right: [{ right_id: "right_001", text: "Första svaret" }],
    review: {
      confidence: 0.9,
      parse_origin: "llm_parsed",
      reasons: [],
      state: "review_complete",
    },
  });
}

function retryResponse(assets: NativeExamAsset[] = []): ExamWorkspaceDocumentResponse {
  const base = buildResponse({ version: 1 });
  return { ...base, document: { ...base.document, assets, items: [reviewItem()] } };
}

async function openRetryDocument(assets: NativeExamAsset[] = []) {
  apiMocks.getExamWorkspaceDocument.mockResolvedValue(retryResponse(assets));
  const mounted = await mountExamWorkspace({ document: "lineage-1" });
  await flushPromises();
  return mounted;
}

async function openDrawer(wrapper: ViewWrapper): Promise<void> {
  await wrapper.get('[data-test="exam-workspace-item-details-toggle"]').trigger("click");
  await flushPromises();
}

async function chooseRetryKind(wrapper: ViewWrapper, kind: NativeExamItemKind): Promise<void> {
  await wrapper.get('[data-test="exam-workspace-retry-kind"]').setValue(kind);
}

async function clickRetry(wrapper: ViewWrapper): Promise<void> {
  await wrapper.get('[data-test="exam-workspace-retry-button"]').trigger("click");
  await flushPromises();
}

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
});

describe("ExamWorkspaceView retry slice", () => {
  it("shows the labeler's type and reconverts the question with the chosen type", async () => {
    const { wrapper } = await openRetryDocument();
    await openDrawer(wrapper);

    expect(
      wrapper.get<HTMLSelectElement>('[data-test="exam-workspace-retry-kind"]').element.value,
    ).toBe("gap_fill");
    await chooseRetryKind(wrapper, "matching");
    apiMocks.retryExamWorkspaceItem.mockResolvedValue({
      lineage_id: "lineage-1",
      item: convertedItem(),
    });

    await clickRetry(wrapper);

    expect(apiMocks.retryExamWorkspaceItem).toHaveBeenCalledTimes(1);
    const [lineageId, document, itemId, kind] = apiMocks.retryExamWorkspaceItem.mock.calls[0];
    expect(lineageId).toBe("lineage-1");
    expect(itemId).toBe("item_001");
    expect(kind).toBe("matching");
    expect(document.items[0].retry_source.label_kind).toBe("gap_fill");
    expect(wrapper.find('[data-test="exam-workspace-retry"]').exists()).toBe(false);
    expect(
      wrapper.find('[data-test="exam-workspace-match-left-text-left_001"]').exists(),
    ).toBe(true);
  });

  it("keeps the chosen type visible when the reply comes back as a review item", async () => {
    const { wrapper } = await openRetryDocument();
    await openDrawer(wrapper);
    await chooseRetryKind(wrapper, "multiple_response");
    apiMocks.retryExamWorkspaceItem.mockResolvedValue({
      lineage_id: "lineage-1",
      item: reviewItem(),
    });

    await clickRetry(wrapper);

    expect(wrapper.find('[data-test="exam-workspace-retry"]').exists()).toBe(true);
    expect(
      wrapper.get<HTMLSelectElement>('[data-test="exam-workspace-retry-kind"]').element.value,
    ).toBe("multiple_response");
  });

  it("passes the open document's picture URLs to the item editor", async () => {
    const asset: NativeExamAsset = {
      asset_id: "asset_001",
      byte_length: 10,
      media_type: "image/png",
      sha256: "a".repeat(64),
    };
    apiMocks.examWorkspaceAssetUrl.mockImplementation(
      (lineageId: string, assetId: string, revision?: number) =>
        `/protected/${lineageId}/${assetId}?revision=${revision}`,
    );

    const { wrapper } = await openRetryDocument([asset]);

    expect(wrapper.findComponent(ExamWorkspaceItemEditor).props("assetUrls")).toEqual({
      asset_001: "/protected/lineage-1/asset_001?revision=1",
    });
  });
});
