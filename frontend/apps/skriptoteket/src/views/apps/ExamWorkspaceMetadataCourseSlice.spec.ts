/** Teacher course choices travel through the real drawer, dirty state and toolbar save. */
import { createTestingPinia } from "@pinia/testing";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamCourse, ExamWorkspaceDocumentResponse } from "../../api/examWorkspace";
import {
  buildResponse, mountExamWorkspace, saveDocument, type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";

import { arrangeStepHistory } from "./ExamWorkspaceHistory.specSupport";

const api = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamCourseCatalog: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));
const rename = vi.hoisted(() => vi.fn());
vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspace", () => ({ ...api }));
vi.mock("../../api/vault", () => ({ renameVaultFile: rename }));

// Identities from the committed Skolverket snapshot, not model-generated courses.
const courses: ExamCourse[] = [
  { key: "SVESVE02", code: "SVESVE02", name: "Svenska 2", school_form: "gymnasiet", reform: "GY11", subject_code: "SVE", subject_name: "Svenska", points: 100 },
  { key: "GRGRMAT01/7-9", code: "GRGRMAT01", name: "Matematik, åk 7–9", school_form: "grundskolan", subject_code: "GRGRMAT01", subject_name: "Matematik", year_band: "7-9", year_band_label: "åk 7–9" },
];
const wrappers: ViewWrapper[] = [];
let original: ExamWorkspaceDocumentResponse;

async function openMetadata() {
  const pinia = createTestingPinia({
    createSpy: vi.fn,
    stubActions: false,
    initialState: {
      auth: { user: { id: "teacher-a", email: "teacher-a@example.test", role: "user", auth_provider: "local" } },
    },
  });
  const { wrapper } = await mountExamWorkspace({ document: "lineage-1" }, "desktop", document.body, pinia);
  wrappers.push(wrapper);
  await wrapper.get('[data-test="exam-workspace-title"]').trigger("click");
  return wrapper;
}
/** The header's save state: "Osparat" while the draft differs, otherwise "Sparat …". */
function saveState(wrapper: ViewWrapper): string {
  return wrapper.get('[data-test="exam-workspace-save-state"]').text();
}
async function choose(wrapper: ViewWrapper, query: string) {
  const drawer = wrapper.get('[data-test="exam-workspace-drawer-details"]');
  await drawer.get('[role="combobox"]').setValue(query);
  await drawer.get('[role="option"]').trigger("click");
}

beforeEach(() => {
  for (const mock of [...Object.values(api), ...Object.values(exportApiMocks)]) mock.mockReset();
  arrangeStepHistory(api);
  rename.mockReset();
  original = buildResponse({ version: 1 });
  original.document.header = { course: null, course_hint: "Lokalt temaprov", printed_total: 36, printed_total_dismissed: false, tags: [] };
  original.saved_document = original.document;
  api.getExamWorkspaceDocument.mockResolvedValue(original);
  api.getExamCourseCatalog.mockResolvedValue({ courses, registered_course_keys: [], generated_at: "2026-10-17T17:00:00Z" });
  api.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  api.saveExamWorkspaceDocument.mockImplementation(async (_id, payload) => ({
    ...original, document: payload.document, saved_document: payload.document,
    summary: { ...original.summary, version: 2 },
  }));
});
afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount();
});

describe("ExamWorkspaceMetadataDrawer course save workflow", () => {
  it("shows an unresolved hint, snapshots the picked name, and saves only with Spara", async () => {
    const wrapper = await openMetadata();
    const drawer = wrapper.get('[data-test="exam-workspace-drawer-details"]');
    expect((drawer.get('[role="combobox"]').element as HTMLInputElement).value).toBe("");
    expect(drawer.text()).toContain("Lokalt temaprov");
    expect(saveState(wrapper)).not.toContain("Osparat");
    await choose(wrapper, "SVESVE02");
    expect(drawer.get('[data-test="exam-workspace-metadata-subject"]').text()).toContain("Svenska");
    expect(saveState(wrapper)).toContain("Osparat");
    expect(api.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(rename).not.toHaveBeenCalled();
    await saveDocument(wrapper);
    expect(api.saveExamWorkspaceDocument).toHaveBeenCalledWith("lineage-1", expect.objectContaining({
      expectedRevision: 1,
      document: expect.objectContaining({
        revision: 2,
        header: { course: { key: "SVESVE02", name: "Svenska 2" }, course_hint: "Lokalt temaprov", printed_total: 36, printed_total_dismissed: false, tags: [] },
      }),
    }));
    expect(saveState(wrapper)).not.toContain("Osparat");
    // Saving must not mutate the installed server response in place.
    expect(original.document.header.course).toBeNull();
  });

  it("clears a persisted course without erasing the hint or printed total", async () => {
    original.document.header.course = { key: "SVESVE02", name: "Svenska 2" };
    const wrapper = await openMetadata();
    const drawer = wrapper.get('[data-test="exam-workspace-drawer-details"]');
    expect((drawer.get('[role="combobox"]').element as HTMLInputElement).value).toBe("Svenska 2");
    await drawer.get('button[aria-label*="ensa"]').trigger("click");
    expect(drawer.text()).toContain("Lokalt temaprov");
    expect(drawer.find('[data-test="exam-workspace-metadata-subject"]').exists()).toBe(false);
    expect(saveState(wrapper)).toContain("Osparat");
    await saveDocument(wrapper);
    expect(api.saveExamWorkspaceDocument).toHaveBeenCalledWith("lineage-1", expect.objectContaining({
      document: expect.objectContaining({ header: { course: null, course_hint: "Lokalt temaprov", printed_total: 36, printed_total_dismissed: false, tags: [] } }),
    }));
  });

  it("binds grundskolan to its chosen band without showing a gymnasiet subject field", async () => {
    const wrapper = await openMetadata();
    await choose(wrapper, "åk 7-9");
    const drawer = wrapper.get('[data-test="exam-workspace-drawer-details"]');
    expect(drawer.find('[data-test="exam-workspace-metadata-subject"]').exists()).toBe(false);
    await saveDocument(wrapper);
    expect(api.saveExamWorkspaceDocument).toHaveBeenCalledWith("lineage-1", expect.objectContaining({
      document: expect.objectContaining({ header: expect.objectContaining({
        course: { key: "GRGRMAT01/7-9", name: "Matematik, åk 7–9" },
      }) }),
    }));
  });
});
