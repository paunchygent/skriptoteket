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
 *   rejected files and keeps service jargon out of all visible copy.
 */

import { createPinia, setActivePinia } from "pinia";
import { flushPromises } from "@vue/test-utils";
import type { DOMWrapper, VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AI_ADMIN_ONLY_NOTE } from "../../composables/useAiAccess";
import { useAuthStore } from "../../stores/auth";
import { createTestRouter, mountWithContext } from "../../test/utils";
import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import { serverExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import {
  arrangeViewApis,
  buildResponse,
  chooseSourceFile,
  mounted,
  queuedImport,
  unmountViews,
} from "./ExamWorkspaceView.specSupport";

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

function findNotes(wrapper: VueWrapper): DOMWrapper<Element>[] {
  return wrapper
    .findAll("p, small, span")
    .filter((node) => node.text().trim() === AI_ADMIN_ONLY_NOTE);
}

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

afterEach(unmountViews);

beforeEach(() => {
  arrangeViewApis(apiMocks);
});

type FrameRole = "admin" | "user" | "contributor";

/**
 * Mount the frame as one signed-in role. The Öppna drawer's Word (.docx)
 * import is an AI control limited to admins (TASK-SKRIPT-REP-0044, L3), so the
 * host-frame specs mount as an admin — the "no change" role — and the appended
 * gate cases mount a denied role.
 */
async function mountView(role: FrameRole = "admin") {
  const pinia = createPinia();
  setActivePinia(pinia);
  useAuthStore().user = {
    id: "teacher-1",
    email: "teacher@example.test",
    role,
    auth_provider: "local",
  };
  const wrapper = mountWithContext(ExamWorkspaceView, {
    props: { store: serverExamWorkspaceStore },
    global: { plugins: [pinia, createTestRouter()] },
  });
  mounted.push(wrapper);
  await flushPromises();
  return wrapper;
}

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

describe("ExamWorkspaceView AI gate in the Öppna drawer", () => {
  const ACCEPT = '[data-test="exam-workspace-source-file-input"]';
  const PICK = '[data-test="exam-workspace-pick-file"]';
  const DROP = '[data-test="exam-workspace-drop-zone"]';

  it("offers a user only DigiExam plus the L3 note, and still imports a .dxe", async () => {
    apiMocks.importExamWorkspaceDigiExam.mockImplementation(async () => {
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(buildResponse());
      return queuedImport;
    });
    const wrapper = await mountView("user");

    expect(wrapper.get(ACCEPT).attributes("accept")).toBe(".dxe");
    expect(findNotes(wrapper).length).toBeGreaterThan(0);
    expect(wrapper.text()).not.toContain("Word .docx");
    expect(wrapper.get(PICK).attributes("disabled")).toBeUndefined();

    await chooseSourceFile(wrapper, new File(["dxe"], "NO_Prov_HT25.dxe"));

    expect(apiMocks.importExamWorkspaceDigiExam).toHaveBeenCalledTimes(1);
    expect(apiMocks.importExamWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("never imports a Word file a user forces past the single-format picker", async () => {
    const wrapper = await mountView("user");

    await chooseSourceFile(wrapper, new File(["prov"], "NO_Prov_HT25.docx"));

    expect(apiMocks.importExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(apiMocks.importExamWorkspaceDigiExam).not.toHaveBeenCalled();
    expect(findNotes(wrapper).length).toBeGreaterThan(0);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(true);
  });

  it("never imports a Word file a user drops on the zone", async () => {
    const wrapper = await mountView("user");

    await wrapper.get(DROP).trigger("drop", {
      dataTransfer: { files: [new File(["prov"], "NO_Prov_HT25.docx")] },
    });
    await flushPromises();

    expect(apiMocks.importExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(apiMocks.importExamWorkspaceDigiExam).not.toHaveBeenCalled();
    expect(findNotes(wrapper).length).toBeGreaterThan(0);
  });

  it("refuses a Word file for a contributor through both the picker and a drop", async () => {
    const wrapper = await mountView("contributor");

    await chooseSourceFile(wrapper, new File(["prov"], "NO_Prov_HT25.docx"));
    await wrapper.get(DROP).trigger("drop", {
      dataTransfer: { files: [new File(["prov"], "Prov_B.docx")] },
    });
    await flushPromises();

    expect(apiMocks.importExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(apiMocks.importExamWorkspaceDigiExam).not.toHaveBeenCalled();
    expect(findNotes(wrapper).length).toBeGreaterThan(0);
  });

  it("keeps every Word control for an admin and imports the .docx", async () => {
    apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(buildResponse());
      return queuedImport;
    });
    const wrapper = await mountView("admin");

    expect(wrapper.get(ACCEPT).attributes("accept")).toBe(".docx,.dxe");
    expect(findNotes(wrapper)).toHaveLength(0);
    expect(wrapper.text()).toContain("Word .docx");

    await chooseSourceFile(wrapper, new File(["prov"], "NO_Prov_HT25.docx"));

    expect(apiMocks.importExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(apiMocks.importExamWorkspaceDigiExam).not.toHaveBeenCalled();
  });
});
