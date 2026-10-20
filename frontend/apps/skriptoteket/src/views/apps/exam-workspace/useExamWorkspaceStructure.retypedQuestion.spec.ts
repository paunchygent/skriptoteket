/**
 * Byt frågetyp on an unconverted question (TASK-SKRIPT-39-05-15 D2).
 *
 * Expected behavior:
 *   Choosing the stored kind on an unbuilt question (review_required with a
 *   source_fallback origin) sends the change-type command, so the server can
 *   flip only the origin; choosing the stored kind on any other question
 *   stays a no-op and sends nothing.
 */

import { createPinia, setActivePinia } from "pinia";
import { effectScope, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { createFencedTransport } from "./examWorkspaceFencedTransport";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { createSyncFence } from "./examWorkspaceSyncFence";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";
import { useExamWorkspaceStructure } from "./useExamWorkspaceStructure";

const apiMocks = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceStructureCommands", () => apiMocks);

function response(document: NativeExamDocument): ExamWorkspaceDocumentResponse {
  return {
    conversion: null,
    document,
    export_blockers: [],
    history_cursor: "cursor-after-command",
    notes: [],
    saved_document: document,
    summary: buildSavedExamSummary({ title: document.title }),
  };
}

/** The parent document with item_001 (gap_fill) left unconverted. */
function unbuiltDocument(): NativeExamDocument {
  const document = buildParentDocument();
  return {
    ...document,
    items: document.items.map((item) =>
      item.item_id === "item_001"
        ? { ...item, review: { ...item.review, confidence: null, parse_origin: "source_fallback", state: "review_required" } }
        : item,
    ),
  };
}

/** A question unbuilt only because of a missing picture: review_required with an
 * llm_parsed origin and a retry_source chunk with missing_images. */
function missingPictureDocument(): NativeExamDocument {
  const document = buildParentDocument();
  return {
    ...document,
    items: document.items.map((item) =>
      item.item_id === "item_001"
        ? {
            ...item,
            retry_source: {
              chunks: [
                {
                  anchor: "body:0001",
                  images: [],
                  kind: "drawing",
                  marked_text: "",
                  missing_images: [
                    { media_type: "image/x-emf", marked_offset: 0, offset: 0, reference: "image3.emf" },
                  ],
                  paragraphs: [],
                  runs: [],
                  text: "",
                },
              ],
              context_chunks: [],
              key_chunks: [],
              label_kind: item.kind,
              owned_context_anchors: [],
            },
            review: { ...item.review, confidence: 0.95, parse_origin: "llm_parsed", state: "review_required" },
          }
        : item,
    ),
  };
}

function setup(document: NativeExamDocument) {
  const workspaceDocument = ref<NativeExamDocument | null>(document);
  const fence = createSyncFence();
  const structure = effectScope().run(() =>
    useExamWorkspaceStructure({
      applyCommandResponse: (token, next) => {
        if (fence.isCurrent(token)) {
          workspaceDocument.value = next.document;
        }
      },
      editDocument: () => true,
      enqueueWrite: (run) => run(fence.begin()),
      flush: async () => true,
      historyCursor: ref("cursor-before-flush"),
      isBusy: () => false,
      isCurrent: (token) => fence.isCurrent(token),
      isReadOnly: () => false,
      lineageId: () => "lineage-1",
      noteLeaseLost: () => undefined,
      onConflict: async () => undefined,
      replaceCopy: (run) => run(),
      savedRevision: () => 7,
      selectItem: () => undefined,
      selectParent: () => undefined,
      selectedItemId: ref<string | null>(null),
      selectedParentId: ref<string | null>(null),
      tabId: () => "tab-1",
      transport: createFencedTransport(() => fence, serverExamWorkspaceStore.shared),
      workspaceDocument,
    }),
  );
  if (!structure) throw new Error("structure composable did not mount");
  return structure;
}

beforeEach(() => {
  setActivePinia(createPinia());
  apiMocks.changeExamWorkspaceItemType.mockReset();
  apiMocks.changeExamWorkspaceItemType.mockResolvedValue({ ...response(unbuiltDocument()), dropped_content: [] });
});

describe("changeType on an unconverted question", () => {
  it("sends the stored kind for an unbuilt question", async () => {
    const structure = setup(unbuiltDocument());

    await structure.changeType("item_001", "gap_fill");

    expect(apiMocks.changeExamWorkspaceItemType).toHaveBeenCalledOnce();
    expect(apiMocks.changeExamWorkspaceItemType.mock.calls.at(0)?.at(1)).toEqual({
      expected_cursor: "cursor-before-flush",
      expected_revision: 7,
      item_id: "item_001",
      tab_id: "tab-1",
      target_kind: "gap_fill",
    });
  });

  it("sends nothing for the stored kind on a missing-picture unbuilt question", async () => {
    const structure = setup(missingPictureDocument());

    await structure.changeType("item_001", "gap_fill");

    expect(apiMocks.changeExamWorkspaceItemType).not.toHaveBeenCalled();
  });

  it("sends nothing for the stored kind on a built question", async () => {
    const structure = setup(buildParentDocument());

    await structure.changeType("item_004", "single_choice");

    expect(apiMocks.changeExamWorkspaceItemType).not.toHaveBeenCalled();
  });
});
