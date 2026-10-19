/**
 * One-question reconversion through the document state (TASK-SKRIPT-39-05-09 D1).
 *
 * Expected behavior:
 *   A retry sends the draft document, the question and the kept or chosen
 *   type to the saved-source retry route, and the reply replaces exactly that
 *   draft item while the rest of the document stays by reference. A reply is
 *   dropped when its lineage does not match, or when the target item changed
 *   while the request was in flight, so a newer change is never stomped. One
 *   retry runs at a time: a second click sends nothing and the save is
 *   refused. A failed request keeps the draft and reports the server's
 *   message, or the retry copy when there is none.
 *
 *   The opening and saved-revision guards are checked with the same captured
 *   values as the lineage guard; the public surface serializes open, save and
 *   import behind the retry, so only the lineage and changed-item branches
 *   can be reached from here.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceItemRetryResponse,
  NativeAnswerKeySuggestion,
  NativeExamItem,
  NativeExamItemKind,
} from "../../../api/examWorkspace";
import { useAuthStore } from "../../../stores/auth";
import { useToastStore } from "../../../stores/toast";
import { buildResponse, currentItem, deferred, openingOf } from "./useExamWorkspaceDocument.specSupport";
import type { DocumentState } from "./useExamWorkspaceDocument.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";

type NativeExamAsset = ExamWorkspaceDocumentResponse["document"]["assets"][number];

const RETRY_FAILURE_COPY = "Det gick inte att konvertera om frågan. Försök igen.";
const CONFLICT_COPY = "Dokumentet har ändrats sedan det öppnades.";

const apiMocks = vi.hoisted(() => ({
  examWorkspaceAssetUrl: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  retryExamWorkspaceItem: vi.fn(),
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
  match_pairs: [],
  model: "model",
  prompt_template_version: "v1",
  provider_profile_id: "profile",
};

function retrySource(labelKind: NativeExamItemKind): NonNullable<NativeExamItem["retry_source"]> {
  return {
    chunks: [
      {
        anchor: "body:0001",
        images: [],
        missing_images: [],
        kind: "question",
        marked_text: "Förklara begreppet.",
        paragraphs: [],
        runs: [],
        text: "Förklara begreppet.",
      },
    ],
    context_chunks: [],
    owned_context_anchors: [],
    key_chunks: [],
    label_kind: labelKind,
  };
}

function freeTextItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ai_suggestion: null,
    facit_text: null,
    import_record: null,
    criteria: [],
    printed_label: null,
    print_order: [],
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Förklara begreppet." }] }],
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
    sequence: 1,
    source_anchor: "body:0001",
    source_points: null,
    retry_source: retrySource("gap_fill"),
    suggested_kind: null,
    tick_points: null,
    writing_lines: 8,
    leftover_points_text: null,
    ...overrides,
  };
}

function convertedItem(): NativeExamItem {
  return freeTextItem({
    kind: "matching",
    writing_lines: null,
    review: {
      confidence: 0.9,
      parse_origin: "llm_parsed",
      reasons: [],
      state: "review_complete",
    },
  });
}

function responseWith(
  items: NativeExamItem[],
  assets: NativeExamAsset[] = [],
): ExamWorkspaceDocumentResponse {
  const base = buildResponse(items[0]);
  const document = { ...base.document, assets, items };
  return { ...base, document, saved_document: document };
}

async function openRetryDocument(
  items: NativeExamItem[] = [freeTextItem(), freeTextItem({ item_id: "item_002", sequence: 2 })],
  assets: NativeExamAsset[] = [],
): Promise<DocumentState> {
  apiMocks.getExamWorkspaceDocument.mockResolvedValue(responseWith(items, assets));
  const state = effectScope().run(() =>
    useExamWorkspaceDocument({ store: serverExamWorkspaceStore }),
  );
  if (!state) {
    throw new Error("expected the document state to be created");
  }
  await state.openDocument("lineage-1");
  await flushPromises();
  return state;
}

function toastCount(message: string): number {
  return useToastStore().toasts.filter((toast) => toast.message === message).length;
}

beforeEach(() => {
  setActivePinia(createPinia());
  signInAs("admin");
  for (const mock of [...Object.values(apiMocks), ...Object.values(exportApiMocks)]) {
    mock.mockReset();
  }
});

/** Seed the signed-in actor the AI gate reads (TASK-SKRIPT-REP-0044 L3). */
function signInAs(role: "user" | "contributor" | "admin" | "superuser"): void {
  useAuthStore().user = { id: "teacher-a", email: "teacher-a@example.test", role, auth_provider: "local" };
}

describe("retryItem", () => {
  it("sends the draft, question and type, then replaces only that item", async () => {
    const state = await openRetryDocument();
    const before = state.workspaceDocument.value;
    if (!before) {
      throw new Error("expected an open document");
    }
    const sibling = before.items[1];
    const replacement = convertedItem();
    apiMocks.retryExamWorkspaceItem.mockResolvedValue({
      lineage_id: "lineage-1",
      item: replacement,
    });

    await state.retryItem("item_001", "matching");

    expect(apiMocks.retryExamWorkspaceItem).toHaveBeenCalledWith(
      "lineage-1",
      before,
      "item_001",
      "matching",
    );
    const after = state.workspaceDocument.value;
    expect(after?.items[0]).toEqual(replacement);
    expect(after?.items[1]).toBe(sibling);
    expect(after?.parents).toBe(before.parents);
    expect(after?.assets).toBe(before.assets);
    expect(after?.revision).toBe(before.revision);
    expect(after?.document_id).toBe(before.document_id);
    expect(after?.title).toBe(before.title);
    expect(state.selectedItem.value).toEqual(replacement);
    expect(state.savedRevision.value).toBe(1);
    expect(state.isDirty.value).toBe(true);
  });

  it("ignores a reply that names another lineage", async () => {
    const state = await openRetryDocument();
    apiMocks.retryExamWorkspaceItem.mockResolvedValue({
      lineage_id: "lineage-2",
      item: convertedItem(),
    });

    await state.retryItem("item_001", "matching");

    expect(currentItem(state).kind).toBe("free_text");
    expect(state.isDirty.value).toBe(false);
    expect(useToastStore().toasts).toEqual([]);
  });

  it("keeps a change that lands while the reply is in flight", async () => {
    const state = await openRetryDocument();
    const pending = deferred<ExamWorkspaceItemRetryResponse>();
    apiMocks.retryExamWorkspaceItem.mockReturnValue(pending.promise);

    const retrying = state.retryItem("item_001", "matching");
    state.applyArrivingSuggestions(openingOf(state), [
      { item_id: "item_001", suggestion: SUGGESTION },
    ]);
    pending.resolve({ lineage_id: "lineage-1", item: convertedItem() });
    await retrying;

    expect(currentItem(state).ai_suggestion).toEqual(SUGGESTION);
    expect(currentItem(state).kind).toBe("free_text");
  });

  it("sends one request while in flight and refuses the save", async () => {
    const state = await openRetryDocument();
    const pending = deferred<ExamWorkspaceItemRetryResponse>();
    apiMocks.retryExamWorkspaceItem.mockReturnValue(pending.promise);

    const first = state.retryItem("item_001", "matching");
    await state.retryItem("item_001", "free_text");

    expect(apiMocks.retryExamWorkspaceItem).toHaveBeenCalledTimes(1);
    await expect(state.saveDocument("position-1")).resolves.toBe(false);
    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();

    pending.resolve({ lineage_id: "lineage-1", item: convertedItem() });
    await first;
  });

  it("sends nothing for a question without a stored source or outside review", async () => {
    const state = await openRetryDocument([
      freeTextItem({ retry_source: null }),
      freeTextItem({
        item_id: "item_002",
        review: {
          confidence: 0.9,
          parse_origin: "llm_parsed",
          reasons: [],
          state: "review_complete",
        },
        sequence: 2,
      }),
    ]);

    await state.retryItem("item_001", "matching");
    await state.retryItem("item_002", "matching");
    await state.retryItem("item_999", "matching");

    expect(apiMocks.retryExamWorkspaceItem).not.toHaveBeenCalled();
  });

  it("shows the server's message when the retry fails", async () => {
    const state = await openRetryDocument();
    apiMocks.retryExamWorkspaceItem.mockRejectedValue(
      new ApiError({ code: "CONFLICT", message: CONFLICT_COPY, status: 409 }),
    );

    await state.retryItem("item_001", "matching");

    expect(toastCount(CONFLICT_COPY)).toBe(1);
    expect(currentItem(state).kind).toBe("free_text");
    expect(state.isDirty.value).toBe(false);
  });

  it("shows the retry copy when a failure carries no server message", async () => {
    const state = await openRetryDocument();
    apiMocks.retryExamWorkspaceItem.mockRejectedValue(new Error("network down"));

    await state.retryItem("item_001", "matching");

    expect(toastCount(RETRY_FAILURE_COPY)).toBe(1);
  });
});

describe("assetUrls", () => {
  it("maps every declared picture to its protected asset URL", async () => {
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

    const state = await openRetryDocument([freeTextItem()], [asset]);
    const urls = state.assetUrls.value;

    expect(apiMocks.examWorkspaceAssetUrl).toHaveBeenCalledWith("lineage-1", "asset_001", 1);
    expect(urls).toEqual({
      asset_001: "/protected/lineage-1/asset_001?revision=1",
    });
  });
});

describe("useExamWorkspaceItemRetry admin gate (TASK-SKRIPT-REP-0044 L3)", () => {
  it.each(["user", "contributor"] as const)(
    "sends no retry for role %s and leaves the draft untouched",
    async (role) => {
      const state = await openRetryDocument();
      signInAs(role);

      await state.retryItem("item_001", "matching");

      expect(apiMocks.retryExamWorkspaceItem).not.toHaveBeenCalled();
      expect(currentItem(state).kind).toBe("free_text");
      expect(state.isDirty.value).toBe(false);
    },
  );

  it("sends the retry for an admin", async () => {
    const state = await openRetryDocument();
    apiMocks.retryExamWorkspaceItem.mockResolvedValue({
      lineage_id: "lineage-1",
      item: convertedItem(),
    });

    await state.retryItem("item_001", "matching");

    expect(apiMocks.retryExamWorkspaceItem).toHaveBeenCalledTimes(1);
    expect(currentItem(state).kind).toBe("matching");
  });
});
