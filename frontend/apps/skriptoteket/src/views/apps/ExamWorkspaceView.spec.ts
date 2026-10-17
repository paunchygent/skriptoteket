/**
 * Exam workspace host-frame behavior.
 *
 * Slice purpose:
 *   Provide the minimal teacher exam workspace frame: a left rail with .docx
 *   intake and document summary, and a right workspace that stays on an empty
 *   state until a document is imported.
 *
 * Expected behavior:
 *   The frame renders the two-zone workspace, accepts only .docx source files
 *   with Swedish guidance for rejected files, and keeps service jargon out of
 *   all visible copy.
 */

import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../api/examWorkspace";
import { mountWithContext } from "../../test/utils";
import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import { buildSavedExamSummary } from "./exam-workspace/useExamWorkspaceDocument.specSupport";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
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
      {
        ai_suggestion: null,
        facit_text: null,
        criteria: [],
        printed_label: null,
        retry_source: null,
        answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
        body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Beskriv vattnets kretslopp." }] }],
        choices: [],
        gaps: [],
        match_left: [],
        match_right: [],
        item_id: "item_001",
        kind: "free_text",
        points: 2,
        points_estimated: false,
        review: {
          confidence: 0.9,
          parse_origin: "deterministic",
          reasons: [],
          state: "review_complete",
        },
        sequence: 1,
        source_anchor: null,
        tick_points: null,
      },
    ],
    origin: {
      extractor_version: "docx-extractor-1",
      kind: "docx_import",
      source_filename: "NO_Prov_HT25.docx",
      source_sha256: "abc123",
    },
    parents: [],
    revision: 1,
    header: {},
    schema_version: "native_exam_document_v4",
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

function mountView() {
  return mountWithContext(ExamWorkspaceView);
}

type ViewWrapper = ReturnType<typeof mountView>;

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

beforeEach(() => {
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeededConversion);
  apiMocks.getExamWorkspaceDocument.mockReset();
  apiMocks.importExamWorkspaceDocument.mockReset();
  apiMocks.saveExamWorkspaceDocument.mockReset();
  apiMocks.listExamWorkspaceDocuments.mockReset();
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
});

describe("ExamWorkspaceView host frame", () => {
  it("renders the two-zone exam workspace frame with the empty workspace state", () => {
    const wrapper = mountView();

    expect(wrapper.find('[data-test="exam-workspace-frame"]').exists()).toBe(true);
    expect(
      wrapper.find('[data-test="exam-workspace-frame"]').attributes("aria-label"),
    ).toBe("Provredigering");
    expect(wrapper.find('[data-test="exam-workspace-rail"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-workspace"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-drop-zone"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("Provredigering");
    expect(wrapper.text()).toContain("Välj provfil (.docx)");
    expect(wrapper.text()).toContain(
      "Ladda upp ett .docx-prov eller öppna ett sparat prov för att börja.",
    );
    expect(wrapper.find('[data-test="exam-workspace-summary"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-item-table"]').exists()).toBe(false);
  });

  it("accepts a .docx source file and shows the imported document", async () => {
    apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(buildResponse());
      return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
    });
    const wrapper = mountView();

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
    expect(wrapper.find('[data-test="exam-workspace-summary"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("NO-prov HT25");
    expect(wrapper.text()).toContain("Version 1");
    expect(wrapper.find('[data-test="exam-workspace-item-row-item_001"]').exists()).toBe(
      true,
    );
  });

  it("rejects a .pdf with Swedish guidance and without importing", async () => {
    const wrapper = mountView();

    await chooseSourceFile(
      wrapper,
      new File(["pdf"], "NO_Prov_HT25.pdf", { type: "application/pdf" }),
    );

    expect(apiMocks.importExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(wrapper.find('[data-test="exam-workspace-source-file-error"]').text()).toBe(
      "Det gick inte att använda filen. Välj en .docx-fil.",
    );
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(true);
  });

  it("keeps single-exam intake explicit when several .docx files are dropped", async () => {
    const wrapper = mountView();

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
    const wrapper = mountView();

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
    expect(wrapper.find('[data-test="exam-workspace-summary"]').exists()).toBe(true);
  });

  it("keeps the frame free of service jargon before and after import", async () => {
    apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(buildResponse());
      return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
    });
    const wrapper = mountView();

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
});
