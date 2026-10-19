/**
 * Exam workspace host-frame test harness.
 *
 * Domain purpose:
 *   Shared fixture exam, mount and interaction helpers for the host-frame,
 *   keyboard and Spara som specs.
 *
 * Relationships:
 *   - Each spec owns its own `api/examWorkspace` module mock (vi.mock is
 *     hoisted per file) and passes its mocks to the arrange helpers.
 */

import { createTestingPinia } from "@pinia/testing";
import { flushPromises } from "@vue/test-utils";
import { vi, type Mock } from "vitest";

import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../api/examWorkspace";
import { buildFreeTextItem } from "../../test/examWorkspaceFixtures";
import { createTestRouter, mountWithContext } from "../../test/utils";
import { adminUser } from "./ExamWorkspaceSlice.specSupport";
import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import { buildSavedExamSummary } from "./exam-workspace/useExamWorkspaceDocument.specSupport";
import { serverExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";

export function buildDocument(): NativeExamDocument {
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
    schema_version: "native_exam_document_v9",
    title: "NO-prov HT25",
  };
}

/** The finished import: its poll status, and the conversion its fetched document carries. */
export const succeededConversion: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};

/** The imported exam's document, fetched once its conversion has succeeded. */
export function buildResponse(): ExamWorkspaceDocumentResponse {
  return {
    export_blockers: [],
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

export type ViewWrapper = ReturnType<typeof mountWithContext>;

export const mounted: ViewWrapper[] = [];

export async function mountView() {
  const pinia = createTestingPinia({
    createSpy: vi.fn,
    initialState: { auth: { user: adminUser } },
    // `hasAtLeastRole` is a setup-store function, so `createTestingPinia`
    // registers it as an action and would stub it to a no-op, refusing AI.
    stubActions: (name) => name !== "hasAtLeastRole",
  });
  const wrapper = mountWithContext(ExamWorkspaceView, {
    props: { store: serverExamWorkspaceStore },
    global: { plugins: [pinia, createTestRouter()] },
  });
  mounted.push(wrapper);
  await flushPromises();
  return wrapper;
}

export async function chooseSourceFile(wrapper: ViewWrapper, file: File) {
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

export const queuedImport = {
  job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
  document_revision: null, questions_total: 0, questions_done: 0, units: [],
};

/** Import resolves, and the fetched document is the one `buildResponse` returns. */
export function importsTheFixture(api: {
  getExamWorkspaceDocument: Mock;
  importExamWorkspaceDocument: Mock;
}) {
  api.importExamWorkspaceDocument.mockImplementation(async () => {
    api.getExamWorkspaceDocument.mockResolvedValue(buildResponse());
    return queuedImport;
  });
}

export async function importFixture(wrapper: ViewWrapper) {
  await chooseSourceFile(wrapper, new File(["prov"], "NO_Prov_HT25.docx", { type: "application/octet-stream" }));
}

export async function editPoints(wrapper: ViewWrapper, points: string) {
  await wrapper.find('[data-test="exam-workspace-row-item_001"]').trigger("click");
  await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue(points);
}

export function pressKey(init: KeyboardEventInit, target: EventTarget = window): KeyboardEvent {
  const event = new KeyboardEvent("keydown", { bubbles: true, cancelable: true, ...init });
  target.dispatchEvent(event);
  return event;
}

/** The mocks `arrangeViewApis` resets and primes before every test. */
export type ViewApiMocks = Record<string, Mock> & {
  getExamWorkspaceConversionStatus: Mock;
  listExamWorkspaceDocuments: Mock;
};

export function arrangeViewApis(api: ViewApiMocks): void {
  for (const mock of Object.values(api)) {
    mock.mockReset();
  }
  api.getExamWorkspaceConversionStatus.mockResolvedValue(succeededConversion);
  api.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
}

export function unmountViews(): void {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  // The test router uses the browser history: an open exam's address must not leak into the next test.
  window.history.replaceState({}, "", "/");
  document.body.replaceChildren();
}
