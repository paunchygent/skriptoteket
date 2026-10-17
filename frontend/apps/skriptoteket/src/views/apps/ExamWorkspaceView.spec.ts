/**
 * Exam workspace host-frame behavior.
 *
 * Slice purpose:
 *   Provide the teacher exam workspace frame: a header, the Öppna drawer with
 *   file intake, and a workspace that stays on an empty state until a
 *   document is imported or opened.
 *
 * Expected behavior:
 *   The frame accepts .docx and .dxe source files with Swedish guidance for
 *   rejected files and keeps service jargon out of all visible copy. Ctrl/Cmd+S
 *   never reaches the browser's save page and saves only a changed exam;
 *   Ctrl/Cmd+Z steps back outside text fields and leaves text fields alone;
 *   Spara som refuses a taken name at the field and reports success as state,
 *   not as a toast.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../api/examWorkspace";
import { ApiError } from "../../api/client";
import { useToastStore } from "../../stores/toast";
import { buildFreeTextItem } from "../../test/examWorkspaceFixtures";
import { mountWithContext } from "../../test/utils";
import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import { buildSavedExamSummary } from "./exam-workspace/useExamWorkspaceDocument.specSupport";

const apiMocks = vi.hoisted(() => ({
  copyExamWorkspaceDocument: vi.fn(),
  downloadExamWorkspaceExport: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  importExamWorkspaceDigiExam: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));

vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const FORBIDDEN_VISIBLE_WORDS = [
  "artefakt",
  "manifest",
  "bundle",
  "runtime",
  "Vault",
  "grant",
  "lease",
  "pipeline",
  "lineage",
];

function buildDocument(): NativeExamDocument {
  return {
    assets: [],
    document_id: "doc-1",
    instructions: [],
    items: [
      buildFreeTextItem(1, {
        body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Beskriv vattnets kretslopp." }] }],
      }),
    ],
    origin: {
      extractor_version: "docx-extractor-1",
      kind: "docx_import",
      source_filename: "NO_Prov_HT25.docx",
      source_sha256: "abc123",
    },
    parents: [],
    revision: 1,
    header: { tags: [] },
    schema_version: "native_exam_document_v6",
    title: "NO-prov HT25",
  };
}

/** The finished import: its poll status, and the conversion its fetched document carries. */
const succeededConversion: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};

/** The imported exam's document, fetched once its conversion has succeeded. */
function buildResponse(): ExamWorkspaceDocumentResponse {
  return {
    history_cursor: "00000000-0000-4000-8000-000000000001",
    conversion: succeededConversion,
    document: buildDocument(),
    saved_document: buildDocument(),
    notes: [],
    summary: buildSavedExamSummary({
      name: "NO-prov HT25",
      saved_at: "2026-10-09T08:00:00Z",
      title: "NO-prov HT25",
    }),
  };
}

type ViewWrapper = ReturnType<typeof mountWithContext>;

const mounted: ViewWrapper[] = [];

async function mountView() {
  const wrapper = mountWithContext(ExamWorkspaceView);
  mounted.push(wrapper);
  await flushPromises();
  return wrapper;
}

async function chooseSourceFile(wrapper: ViewWrapper, file: File) {
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

const queuedImport = {
  job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
  document_revision: null, questions_total: 0, questions_done: 0, units: [],
};

/** Import resolves, and the fetched document is the one `buildResponse` returns. */
function importsTheFixture() {
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(buildResponse());
    return queuedImport;
  });
}

async function importFixture(wrapper: ViewWrapper) {
  await chooseSourceFile(wrapper, new File(["prov"], "NO_Prov_HT25.docx", { type: "application/octet-stream" }));
}

async function editPoints(wrapper: ViewWrapper, points: string) {
  await wrapper.find('[data-test="exam-workspace-row-item_001"]').trigger("click");
  await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue(points);
}

function pressKey(init: KeyboardEventInit, target: EventTarget = window): KeyboardEvent {
  const event = new KeyboardEvent("keydown", { bubbles: true, cancelable: true, ...init });
  target.dispatchEvent(event);
  return event;
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  // The test router uses the browser history: an open exam's address must not leak into the next test.
  window.history.replaceState({}, "", "/");
  document.body.replaceChildren();
});

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeededConversion);
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
});

describe("ExamWorkspaceView host frame", () => {
  it("renders the frame with the empty workspace state and the Öppna drawer open", async () => {
    const wrapper = await mountView();

    expect(wrapper.find('[data-test="exam-workspace-frame"]').exists()).toBe(true);
    expect(
      wrapper.find('[data-test="exam-workspace-frame"]').attributes("aria-label"),
    ).toBe("Provredigering");
    expect(wrapper.find('[data-test="exam-workspace-header"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-workspace"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-drawer-open"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-drop-zone"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("Inget prov öppet");
    expect(wrapper.text()).toContain("Välj provfil");
    expect(wrapper.text()).toContain("Word .docx");
    expect(wrapper.text()).toContain("DigiExam .dxe");
    expect(wrapper.find('[data-test="exam-workspace-question-list"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').exists()).toBe(false);
  });

  it("accepts a .docx source file and shows the imported document", async () => {
    apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(buildResponse());
      return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
    });
    const wrapper = await mountView();

    await chooseSourceFile(
      wrapper,
      new File(["prov"], "NO_Prov_HT25.docx", {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      }),
    );

    expect(apiMocks.importExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-workspace-source-file-error"]').exists()).toBe(
      false,
    );
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("NO-prov HT25");
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toMatch(/^Sparat/);
    expect(wrapper.find('[data-test="exam-workspace-row-item_001"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
  });

  it("rejects a .pdf with Swedish guidance and without importing", async () => {
    const wrapper = await mountView();

    await chooseSourceFile(
      wrapper,
      new File(["pdf"], "NO_Prov_HT25.pdf", { type: "application/pdf" }),
    );

    expect(apiMocks.importExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(wrapper.find('[data-test="exam-workspace-source-file-error"]').text()).toBe(
      "Det gick inte att använda filen. Välj en Word-fil (.docx) eller en DigiExam-fil (.dxe).",
    );
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(true);
  });

  it("keeps single-exam intake explicit when several .docx files are dropped", async () => {
    const wrapper = await mountView();

    await wrapper.find('[data-test="exam-workspace-drop-zone"]').trigger("drop", {
      dataTransfer: {
        files: [
          new File(["a"], "Prov_A.docx", { type: "application/octet-stream" }),
          new File(["b"], "Prov_B.docx", { type: "application/octet-stream" }),
        ],
      },
    });
    await flushPromises();

    expect(apiMocks.importExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("Välj en provfil åt gången.");
  });

  it("imports a dropped .docx while ignoring files that cannot be used", async () => {
    apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(buildResponse());
      return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
    });
    const wrapper = await mountView();

    await wrapper.find('[data-test="exam-workspace-drop-zone"]').trigger("drop", {
      dataTransfer: {
        files: [
          new File(["prov"], "NO_Prov_HT25.docx", { type: "application/octet-stream" }),
          new File(["pdf"], "NO_Prov_HT25.pdf", { type: "application/pdf" }),
        ],
      },
    });
    await flushPromises();

    expect(apiMocks.importExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    const [file] = apiMocks.importExamWorkspaceDocument.mock.calls[0] as [File];
    expect(file.name).toBe("NO_Prov_HT25.docx");
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("NO-prov HT25");
  });

  it("keeps the frame free of service jargon before and after import", async () => {
    apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(buildResponse());
      return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
    });
    const wrapper = await mountView();

    for (const forbiddenWord of FORBIDDEN_VISIBLE_WORDS) {
      expect(wrapper.text()).not.toContain(forbiddenWord);
    }

    await chooseSourceFile(
      wrapper,
      new File(["prov"], "NO_Prov_HT25.docx", {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      }),
    );

    for (const forbiddenWord of FORBIDDEN_VISIBLE_WORDS) {
      expect(wrapper.text()).not.toContain(forbiddenWord);
    }
    expect(wrapper.text()).not.toContain("file-1");
  });

  it("sends a DigiExam .dxe file chosen in the Öppna drawer to the DigiExam importer, not the Word one", async () => {
    apiMocks.importExamWorkspaceDigiExam.mockImplementation(async () => {
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(buildResponse());
      return queuedImport;
    });
    const wrapper = await mountView();

    await chooseSourceFile(wrapper, new File(["dxe"], "Prov_HT25.dxe", { type: "application/octet-stream" }));

    expect(wrapper.find('[data-test="exam-workspace-source-file-error"]').exists()).toBe(false);
    expect(apiMocks.importExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(apiMocks.importExamWorkspaceDigiExam).toHaveBeenCalledTimes(1);
    const [file] = apiMocks.importExamWorkspaceDigiExam.mock.calls[0] as [File];
    expect(file.name).toBe("Prov_HT25.dxe");
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("NO-prov HT25");
  });
});

describe("ExamWorkspaceView keyboard shortcuts", () => {
  it.each([
    ["Ctrl+S", { ctrlKey: true }],
    ["Meta+S", { metaKey: true }],
  ])("%s never opens the browser's save page, with or without an exam, and saves nothing unchanged", async (_name, modifier) => {
    importsTheFixture();
    const wrapper = await mountView();

    expect(pressKey({ key: "s", ...modifier }).defaultPrevented).toBe(true);

    await importFixture(wrapper);

    expect(pressKey({ key: "s", ...modifier }).defaultPrevented).toBe(true);
    expect(pressKey({ key: "S", ...modifier }).defaultPrevented).toBe(true);
    await flushPromises();
    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(pressKey({ key: "s" }).defaultPrevented).toBe(false);
  });

  it.each([
    ["Ctrl+S", { ctrlKey: true }],
    ["Meta+S", { metaKey: true }],
  ])("%s saves the changed exam once, with the previous revision expected", async (_name, modifier) => {
    importsTheFixture();
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue({ ...buildResponse(), summary: buildSavedExamSummary({ title: "NO-prov HT25", version: 2 }) });
    const wrapper = await mountView();
    await importFixture(wrapper);
    await editPoints(wrapper, "7");
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toBe("Osparat");

    expect(pressKey({ key: "s", ...modifier }).defaultPrevented).toBe(true);
    await flushPromises();

    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    const [lineageId, params] = apiMocks.saveExamWorkspaceDocument.mock.calls[0] as [
      string,
      { document: NativeExamDocument; expectedRevision: number },
    ];
    expect(lineageId).toBe("lineage-1");
    expect(params.expectedRevision).toBe(1);
    expect(params.document.items[0]?.points).toBe(7);
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toMatch(/^Sparat/);

    pressKey({ key: "s", ...modifier });
    await flushPromises();
    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("Ctrl+Z outside a text field steps back through the stored history", async () => {
    importsTheFixture();
    const baselineId = "step-baseline";
    apiMocks.getExamWorkspaceHistory.mockResolvedValue({
      baseline_step_id: baselineId,
      cursor: buildResponse().history_cursor,
      step_ids: [buildResponse().history_cursor],
    });
    apiMocks.getExamWorkspaceHistoryStep.mockResolvedValue({ document: buildDocument(), step_id: baselineId });
    const wrapper = await mountView();
    await importFixture(wrapper);

    const event = pressKey({ key: "z", ctrlKey: true }, document.body);
    await flushPromises();

    expect(event.defaultPrevented).toBe(true);
    expect(apiMocks.getExamWorkspaceHistoryStep).toHaveBeenCalledExactlyOnceWith("lineage-1", baselineId);
  });

  it("Ctrl+Z inside a text field is left to the field and does not undo the exam", async () => {
    importsTheFixture();
    apiMocks.getExamWorkspaceHistory.mockResolvedValue({
      baseline_step_id: "step-baseline",
      cursor: buildResponse().history_cursor,
      step_ids: [buildResponse().history_cursor],
    });
    apiMocks.getExamWorkspaceHistoryStep.mockResolvedValue({ document: buildDocument(), step_id: "step-baseline" });
    const wrapper = await mountView();
    await importFixture(wrapper);
    const field = document.createElement("input");
    document.body.append(field);

    const event = pressKey({ key: "z", ctrlKey: true }, field);
    const shifted = pressKey({ key: "z", ctrlKey: true, shiftKey: true }, field);
    await flushPromises();
    field.remove();

    expect(event.defaultPrevented).toBe(false);
    expect(shifted.defaultPrevented).toBe(false);
    expect(apiMocks.getExamWorkspaceHistoryStep).not.toHaveBeenCalled();
  });
});

describe("ExamWorkspaceView Spara som", () => {
  async function openSaveAs(wrapper: ViewWrapper) {
    await wrapper.find('[data-test="exam-workspace-save-menu"]').trigger("click");
    document.querySelector<HTMLElement>('[data-test="exam-workspace-save-as-option"]')!.click();
    await flushPromises();
  }

  async function submitName(wrapper: ViewWrapper, name: string) {
    await wrapper.find('[data-test="exam-workspace-save-as-name"]').setValue(name);
    await wrapper.find('[data-test="exam-workspace-save-as"] form').trigger("submit");
    await flushPromises();
  }

  function submit(wrapper: ViewWrapper) {
    return wrapper.find<HTMLButtonElement>('[data-test="exam-workspace-save-as-submit"]');
  }

  it("prefills the name as '<name> (kopia)'", async () => {
    importsTheFixture();
    const wrapper = await mountView();
    await importFixture(wrapper);

    await openSaveAs(wrapper);

    expect(wrapper.find('[data-test="exam-workspace-save-as"]').exists()).toBe(true);
    expect(
      wrapper.find<HTMLInputElement>('[data-test="exam-workspace-save-as-name"]').element.value,
    ).toBe("NO-prov HT25 (kopia)");
    expect(submit(wrapper).element.disabled).toBe(false);
  });

  it("refuses a name another file uses at the field and keeps the dialog open", async () => {
    importsTheFixture();
    apiMocks.copyExamWorkspaceDocument.mockRejectedValue(
      new ApiError({
        code: "VALIDATION_ERROR",
        details: { code: "vault_name_in_use" },
        message: "Name in use",
        status: 422,
      }),
    );
    const wrapper = await mountView();
    await importFixture(wrapper);
    await openSaveAs(wrapper);

    await wrapper.find('[data-test="exam-workspace-save-as"] form').trigger("submit");
    await flushPromises();

    expect(apiMocks.copyExamWorkspaceDocument).toHaveBeenCalledExactlyOnceWith(
      "lineage-1",
      "NO-prov HT25 (kopia)",
      expect.objectContaining({ title: "NO-prov HT25" }),
    );
    expect(wrapper.find('[data-test="exam-workspace-save-as"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-save-as-error"]').text()).toContain(
      "Namnet används redan av en annan fil.",
    );
    expect(submit(wrapper).element.disabled).toBe(true);
    expect(vi.mocked(useToastStore().failure)).not.toHaveBeenCalled();

    await wrapper.find('[data-test="exam-workspace-save-as-name"]').setValue("Annat namn");
    expect(wrapper.find('[data-test="exam-workspace-save-as-error"]').exists()).toBe(false);
    expect(submit(wrapper).element.disabled).toBe(false);

    await wrapper.find('[data-test="exam-workspace-save-as-name"]').setValue("  NO-prov HT25 (kopia) ");
    expect(wrapper.find('[data-test="exam-workspace-save-as-error"]').exists()).toBe(true);
    expect(submit(wrapper).element.disabled).toBe(true);
  });

  it("closes on success, opens the copy and shows no toast", async () => {
    importsTheFixture();
    const copy = buildResponse();
    apiMocks.copyExamWorkspaceDocument.mockResolvedValue({
      ...copy,
      document: { ...copy.document, title: "Kopia av provet" },
      saved_document: { ...copy.saved_document, title: "Kopia av provet" },
      summary: buildSavedExamSummary({
        lineage_id: "lineage-2",
        name: "Provkopia",
        title: "Kopia av provet",
        version: 1,
      }),
    });
    const wrapper = await mountView();
    await importFixture(wrapper);
    await openSaveAs(wrapper);

    await submitName(wrapper, "Provkopia");

    expect(apiMocks.copyExamWorkspaceDocument).toHaveBeenCalledExactlyOnceWith(
      "lineage-1",
      "Provkopia",
      expect.objectContaining({ title: "NO-prov HT25" }),
    );
    expect(wrapper.find('[data-test="exam-workspace-save-as"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("Kopia av provet");
    const toasts = useToastStore();
    expect(vi.mocked(toasts.failure)).not.toHaveBeenCalled();
    expect(vi.mocked(toasts.success)).not.toHaveBeenCalled();
    expect(vi.mocked(toasts.info)).not.toHaveBeenCalled();
  });
});
