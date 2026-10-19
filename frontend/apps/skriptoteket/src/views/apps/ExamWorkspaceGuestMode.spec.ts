/**
 * Guest mode inside the shared exam workspace.
 *
 * Expected behavior:
 *   With a guest store (teacher null, guest startBlank present) the same view
 *   starts a blank exam through "Tomt prov" and a QTI .zip through the file
 *   picker or a drop; every AI control and the DigiExam/Word import show the
 *   sign-in prompt instead of calling; Spara som, save-to-Mina-filer, rename
 *   and the saved-exams list are absent while Spara keeps saving to the
 *   browser store. AI controls stay enabled and show no admin-only note.
 *   With the server store nothing changes (covered by the frame, saveAs,
 *   exports, enrichment, retry and conversion slices).
 */

import { createPinia } from "pinia";
import { flushPromises } from "@vue/test-utils";
import { ref } from "vue";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { NativeExamDocument, NativeExamItem } from "../../api/examWorkspace";
import { AI_ADMIN_ONLY_NOTE } from "../../composables/useAiAccess";
import { createTestRouter, mountWithContext } from "../../test/utils";
import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import {
  GUEST_AI_SIGN_IN,
  GUEST_IMPORT_SIGN_IN,
} from "./exam-workspace/examWorkspaceGuestCopy";
import { createGuestExamWorkspaceStore } from "./exam-workspace/examWorkspaceGuestStore";
import type { ExamWorkspaceGuestStoreDeps } from "./exam-workspace/examWorkspaceGuestStore";
import { createGuestPublicApiMocks } from "./exam-workspace/examWorkspaceGuestStore.specSupport";
import { createInMemoryExamWorkspaceGuestDraftStorage } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import {
  EXAM_WORKSPACE_LAYOUT_KEY,
  type ExamWorkspaceLayout,
} from "./exam-workspace/useExamWorkspaceLayout";

const apiMocks = vi.hoisted(() => ({
  addExamWorkspaceChild: vi.fn(),
  changeExamWorkspaceItemType: vi.fn(),
  copyExamWorkspaceDocument: vi.fn(),
  createEmptyExamWorkspacePart: vi.fn(),
  createExamWorkspaceParent: vi.fn(),
  deleteExamWorkspaceChild: vi.fn(),
  deleteExamWorkspaceParent: vi.fn(),
  downloadExamWorkspaceExport: vi.fn(),
  examWorkspaceAssetUrl: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamCourseCatalog: vi.fn(),
  getExamCourseContent: vi.fn(),
  getExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceContentSuggestions: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceExportChecklist: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  groupExamWorkspaceItems: vi.fn(),
  importExamWorkspaceDigiExam: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  moveExamWorkspaceItem: vi.fn(),
  reorderExamWorkspaceChildren: vi.fn(),
  requestExamWorkspaceAnswerKeySuggestions: vi.fn(),
  requestExamWorkspaceAnswerMisspellings: vi.fn(),
  requestExamWorkspaceContentSuggestions: vi.fn(),
  retryExamWorkspaceItem: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  saveExamWorkspaceExport: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  updateExamListOrdering: vi.fn(),
}));

vi.mock("../../api/examWorkspace", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/examWorkspace")>()),
  ...apiMocks,
}));

vi.mock("../../api/examWorkspaceStructureCommands", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/examWorkspaceStructureCommands")>()),
  addExamWorkspaceChild: apiMocks.addExamWorkspaceChild,
  changeExamWorkspaceItemType: apiMocks.changeExamWorkspaceItemType,
  createEmptyExamWorkspacePart: apiMocks.createEmptyExamWorkspacePart,
  createExamWorkspaceParent: apiMocks.createExamWorkspaceParent,
  deleteExamWorkspaceChild: apiMocks.deleteExamWorkspaceChild,
  deleteExamWorkspaceParent: apiMocks.deleteExamWorkspaceParent,
  groupExamWorkspaceItems: apiMocks.groupExamWorkspaceItems,
  moveExamWorkspaceItem: apiMocks.moveExamWorkspaceItem,
  reorderExamWorkspaceChildren: apiMocks.reorderExamWorkspaceChildren,
}));

vi.mock("../../api/vault", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/vault")>()),
  renameVaultFile: vi.fn(),
}));

beforeAll(() => {
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:picture");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
});

function textBody(text: string): NativeExamDocument["instructions"] {
  return [{ heading_level: null, segments: [{ kind: "text", marks: [], text }] }];
}

function choice(choiceId: string, text: string) {
  return { body: textBody(text), choice_id: choiceId };
}

/** A keyed question without a key: its export blocker carries the AI fix. */
function keylessItem(sequence: number, kind: "single_choice" | "multiple_response"): NativeExamItem {
  const itemId = `item_${String(sequence).padStart(3, "0")}`;
  return {
    ai_suggestion: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    body: textBody(`Fråga ${sequence}: välj rätt alternativ.`),
    choices: [choice("choice_001", "Avdunstning"), choice("choice_002", "Kondensation"), choice("choice_003", "Nederbörd")],
    criteria: [],
    facit_text: null,
    gaps: [],
    import_record: null,
    item_id: itemId,
    kind,
    match_left: [],
    match_right: [],
    points: 2,
    points_estimated: false,
    print_order: [],
    printed_label: null,
    retry_source: null,
    review: { confidence: 0.9, parse_origin: "deterministic", reasons: [], state: "review_complete" },
    sequence,
    source_anchor: null,
    suggested_kind: null,
    tick_points: null,
    writing_lines: null,
  };
}

/** A converted question awaiting review with its stored source: shows Konvertera igen. */
function retryItem(): NativeExamItem {
  return {
    ai_suggestion: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    body: textBody("Förklara begreppet."),
    choices: [],
    criteria: [],
    facit_text: null,
    gaps: [],
    import_record: {
      original_wording: { answer_key_text: null, question_text: "Förklara begreppet." },
      steps: [],
    },
    item_id: "item_003",
    kind: "free_text",
    match_left: [],
    match_right: [],
    points: 2,
    points_estimated: false,
    print_order: [],
    printed_label: null,
    retry_source: {
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
      key_chunks: [],
      label_kind: "gap_fill",
      owned_context_anchors: [],
    },
    review: {
      confidence: 0.4,
      parse_origin: "llm_parsed",
      reasons: ["osäker tolkning"],
      state: "review_required",
    },
    sequence: 3,
    source_anchor: "body:0001",
    suggested_kind: null,
    tick_points: null,
    writing_lines: 8,
  };
}

function blankDocument(): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    header: { tags: [] },
    instructions: [],
    items: [keylessItem(1, "single_choice"), keylessItem(2, "multiple_response"), retryItem()],
    origin: { kind: "docx_import" },
    parents: [],
    revision: 1,
    schema_version: "native_exam_document_v8",
    title: "Nytt prov",
  };
}

type PublicApi = ExamWorkspaceGuestStoreDeps["api"];

function setupGuest() {
  const storage = createInMemoryExamWorkspaceGuestDraftStorage();
  const publicMocks = createGuestPublicApiMocks();
  publicMocks.importPublicExamWorkspaceQti.mockResolvedValue({
    assets: {},
    document: blankDocument(),
    notes: [],
  });
  publicMocks.createPublicExamWorkspaceBlank.mockResolvedValue({
    document: blankDocument(),
    export_blockers: [],
  });
  publicMocks.getPublicExamCourseCatalog.mockResolvedValue({
    courses: [],
    generated_at: "2026-10-18T00:00:00Z",
    registered_course_keys: [],
  });
  const api: PublicApi = publicMocks;
  let counter = 0;
  const guest = createGuestExamWorkspaceStore({
    api,
    ids: {
      now: () => "2026-10-18T10:00:00.000Z",
      uuid: () => {
        counter += 1;
        return `10000000-0000-4000-8000-${String(counter).padStart(12, "0")}`;
      },
    },
    onLimit: () => undefined,
    storage,
  });
  return { guest, publicMocks, storage };
}

type GuestWrapper = Awaited<ReturnType<typeof mountGuestView>>;

async function mountGuestView(store: ReturnType<typeof createGuestExamWorkspaceStore>["store"]) {
  const layout = ref<ExamWorkspaceLayout>("desktop");
  const wrapper = mountWithContext(ExamWorkspaceView, {
    props: { store },
    global: {
      plugins: [createPinia(), createTestRouter()],
      provide: { [EXAM_WORKSPACE_LAYOUT_KEY]: layout },
    },
  });
  await flushPromises();
  return wrapper;
}

function promptText(wrapper: GuestWrapper): string | null {
  const prompt = wrapper.find('[data-test="exam-workspace-sign-in-prompt"]');
  return prompt.exists() ? prompt.text() : null;
}

async function chooseGuestFile(wrapper: GuestWrapper, file: File): Promise<void> {
  const input = wrapper.find<HTMLInputElement>(
    '[data-test="exam-workspace-source-file-input"]',
  );
  Object.defineProperty(input.element, "files", {
    configurable: true,
    value: [file],
  });
  await input.trigger("change");
  await flushPromises();
}

function expectNoServerCalls(): void {
  for (const mock of Object.values(apiMocks)) {
    expect(mock).not.toHaveBeenCalled();
  }
}

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  document.body.replaceChildren();
  window.history.replaceState({}, "", "/");
});

describe("ExamWorkspaceView guest mode", () => {
  it("starts blank through Tomt prov and keeps the teacher-only list and course choice hidden", async () => {
    const { guest, publicMocks } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').text()).toContain("Börja med ett tomt prov.");
    expect(wrapper.find('[data-test="exam-workspace-sign-in-prompt"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-guest-blank"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("Word .docx");
    expect(wrapper.text()).toContain("DigiExam .dxe");
    expect(wrapper.find('[data-test="exam-workspace-saved-documents"]').exists()).toBe(false);
    expect(document.querySelector("#exam-workspace-import-course")).toBeNull();

    await wrapper.get('[data-test="exam-workspace-guest-blank"]').trigger("click");
    await flushPromises();

    expect(publicMocks.createPublicExamWorkspaceBlank).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-row-item_001"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("Nytt prov");
    expectNoServerCalls();
    wrapper.unmount();
  });

  it("shows the import sign-in prompt for a chosen or dropped .docx without importing", async () => {
    const { guest, publicMocks } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    await chooseGuestFile(wrapper, new File(["prov"], "NO_Prov_HT25.docx"));
    await flushPromises();

    expect(promptText(wrapper)).toContain(GUEST_IMPORT_SIGN_IN);

    await wrapper.get('[data-test="exam-workspace-drop-zone"]').trigger("drop", {
      dataTransfer: { files: [new File(["prov"], "NO_Prov_HT25.docx")] },
    });
    await flushPromises();

    expect(promptText(wrapper)).toContain(GUEST_IMPORT_SIGN_IN);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(true);
    expect(publicMocks.importPublicExamWorkspaceQti).not.toHaveBeenCalled();
    expectNoServerCalls();
    wrapper.unmount();
  });

  it("shows the import sign-in prompt for a dropped .dxe without importing", async () => {
    const { guest, publicMocks } = setupGuest();
    const wrapper = await mountGuestView(guest.store);

    await wrapper.get('[data-test="exam-workspace-drop-zone"]').trigger("drop", {
      dataTransfer: { files: [new File(["dxe"], "Prov_HT25.dxe")] },
    });
    await flushPromises();

    expect(promptText(wrapper)).toContain(GUEST_IMPORT_SIGN_IN);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(true);
    expect(publicMocks.importPublicExamWorkspaceQti).not.toHaveBeenCalled();
    expectNoServerCalls();
    wrapper.unmount();
  });

  it("accepts a guest .zip chosen in the picker and opens the parsed exam", async () => {
    const { guest, publicMocks } = setupGuest();
    publicMocks.importPublicExamWorkspaceQti.mockResolvedValue({
      assets: {},
      document: blankDocument(),
      notes: [],
    });
    const wrapper = await mountGuestView(guest.store);

    await chooseGuestFile(wrapper, new File(["qti"], "Prov_HT25.zip", { type: "application/zip" }));
    await flushPromises();

    expect(publicMocks.importPublicExamWorkspaceQti).toHaveBeenCalledTimes(1);
    const [file, courseKey] = publicMocks.importPublicExamWorkspaceQti.mock.calls[0]!;
    expect(file.name).toBe("Prov_HT25.zip");
    expect(courseKey).toBeNull();
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("Nytt prov");
    expect(wrapper.find('[data-test="exam-workspace-row-item_001"]').exists()).toBe(true);
    expectNoServerCalls();
    wrapper.unmount();
  });

  it("accepts a dropped guest .zip and opens the parsed exam", async () => {
    const { guest, publicMocks } = setupGuest();
    publicMocks.importPublicExamWorkspaceQti.mockResolvedValue({
      assets: {},
      document: blankDocument(),
      notes: [],
    });
    const wrapper = await mountGuestView(guest.store);

    await wrapper.get('[data-test="exam-workspace-drop-zone"]').trigger("drop", {
      dataTransfer: { files: [new File(["qti"], "Prov_HT25.zip", { type: "application/zip" })] },
    });
    await flushPromises();

    expect(publicMocks.importPublicExamWorkspaceQti).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("Nytt prov");
    expectNoServerCalls();
    wrapper.unmount();
  });

  it("shows the AI sign-in prompt from the header control without calling", async () => {
    const { guest } = setupGuest();
    const wrapper = await mountGuestView(guest.store);
    await wrapper.get('[data-test="exam-workspace-guest-blank"]').trigger("click");
    await flushPromises();

    const suggest = wrapper.get('[data-test="exam-workspace-suggest-all"]');
    expect(suggest.attributes("disabled")).toBeUndefined();
    await suggest.trigger("click");
    await flushPromises();

    expect(promptText(wrapper)).toContain(GUEST_AI_SIGN_IN);
    expectNoServerCalls();
    wrapper.unmount();
  });

  it("shows the AI sign-in prompt from both export-blocker controls without calling", async () => {
    const { guest } = setupGuest();
    const wrapper = await mountGuestView(guest.store);
    await wrapper.get('[data-test="exam-workspace-guest-blank"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    await flushPromises();

    const suggestAll = document.querySelector<HTMLElement>(
      '[data-test="exam-workspace-blocker-suggest-all"]',
    )!;
    expect(suggestAll.hasAttribute("disabled")).toBe(false);
    suggestAll.click();
    await flushPromises();
    expect(promptText(wrapper)).toContain(GUEST_AI_SIGN_IN);

    const fix = document.querySelector<HTMLElement>(
      '[data-test="exam-workspace-blocker-fix-item_001"]',
    )!;
    expect(fix.hasAttribute("disabled")).toBe(false);
    fix.click();
    await flushPromises();
    expect(promptText(wrapper)).toContain(GUEST_AI_SIGN_IN);
    expectNoServerCalls();
    wrapper.unmount();
  });

  it("shows the AI sign-in prompt from Föreslå innehåll without calling", async () => {
    const { guest } = setupGuest();
    const wrapper = await mountGuestView(guest.store);
    await wrapper.get('[data-test="exam-workspace-guest-blank"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-test="exam-workspace-title"]').trigger("click");
    await flushPromises();

    const suggest = wrapper.get('[data-test="exam-workspace-content-suggest"]');
    expect(suggest.attributes("disabled")).toBeUndefined();
    await suggest.trigger("click");
    await flushPromises();

    expect(promptText(wrapper)).toContain(GUEST_AI_SIGN_IN);
    expectNoServerCalls();
    wrapper.unmount();
  });

  it("shows the AI sign-in prompt from Konvertera igen without calling", async () => {
    const { guest } = setupGuest();
    const wrapper = await mountGuestView(guest.store);
    await wrapper.get('[data-test="exam-workspace-guest-blank"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-test="exam-workspace-row-item_003"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-import-toggle"]').trigger("click");
    await flushPromises();

    const retry = wrapper.get('[data-test="exam-workspace-retry"]');
    expect(retry.attributes("disabled")).toBeUndefined();
    expect(wrapper.get('[data-test="exam-workspace-retry-kind"]').attributes("disabled")).toBeUndefined();
    await retry.trigger("click");
    await flushPromises();

    expect(promptText(wrapper)).toContain(GUEST_AI_SIGN_IN);
    expectNoServerCalls();
    wrapper.unmount();
  });

  it("renders no admin-only note and leaves every AI control enabled", async () => {
    const { guest } = setupGuest();
    const wrapper = await mountGuestView(guest.store);
    await wrapper.get('[data-test="exam-workspace-guest-blank"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).not.toContain(AI_ADMIN_ONLY_NOTE);
    expect(document.body.textContent ?? "").not.toContain(AI_ADMIN_ONLY_NOTE);
    expect(wrapper.get('[data-test="exam-workspace-suggest-all"]').attributes("disabled")).toBeUndefined();

    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    await flushPromises();
    expect(document.body.textContent ?? "").not.toContain(AI_ADMIN_ONLY_NOTE);

    await wrapper.get('[data-test="exam-workspace-title"]').trigger("click");
    await flushPromises();
    expect(wrapper.get('[data-test="exam-workspace-content-suggest"]').attributes("disabled")).toBeUndefined();

    await wrapper.get('[data-test="exam-workspace-row-item_003"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-import-toggle"]').trigger("click");
    await flushPromises();
    expect(wrapper.get('[data-test="exam-workspace-retry"]').attributes("disabled")).toBeUndefined();
    expect(wrapper.text()).not.toContain(AI_ADMIN_ONLY_NOTE);
    wrapper.unmount();
  });

  it("hides Spara som, save-to-Mina-filer and rename while Spara saves to the browser store", async () => {
    const { guest, storage } = setupGuest();
    const wrapper = await mountGuestView(guest.store);
    await wrapper.get('[data-test="exam-workspace-guest-blank"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-save-menu"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-save"]').exists()).toBe(true);

    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    await flushPromises();
    expect(
      document.querySelectorAll('[data-test^="exam-workspace-export-save-"]').length,
    ).toBe(0);

    await wrapper.get('[data-test="exam-workspace-title"]').trigger("click");
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-metadata-name"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-metadata-rename"]').exists()).toBe(false);

    await wrapper.get('[data-test="exam-workspace-row-item_001"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("5");
    await wrapper.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();

    const stored = await storage.load();
    const saved = stored?.draft.saved_document.items.find((item) => item.item_id === "item_001");
    expect(saved?.points).toBe(5);
    expectNoServerCalls();
    wrapper.unmount();
  });
});
