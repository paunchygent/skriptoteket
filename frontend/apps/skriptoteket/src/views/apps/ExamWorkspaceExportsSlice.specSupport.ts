/**
 * Exam workspace export slice test harness.
 *
 * Domain purpose:
 *   Shared fixtures and Exportera menu/drawer interactions for the export
 *   slice specs (blockers, download, checklist).
 *
 * Relationships:
 *   - Each spec owns its own `api/examWorkspace` and `browserDownload` module
 *     mocks (vi.mock is hoisted per file) and passes them to
 *     `arrangeExportApis`.
 */

import { DOMWrapper, flushPromises } from "@vue/test-utils";
import { expect, type Mock } from "vitest";

import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceExportChecklistResponse,
} from "../../api/examWorkspace";
import {
  buildFreeTextItem,
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";

export const ZERO_POINTS_NOTE =
  "Exam.net ger frågor med 0 poäng 1 poäng. Ändra poängen i Exam.net efter importen.";

/** The finished import: its poll status, and the conversion its fetched document carries. */
export const succeededConversion: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};

export function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, reject, resolve };
}

/** One entry per loss the checklist lists, as the server sends them. */
export const LOST_CHECKLIST: ExamWorkspaceExportChecklistResponse = {
  inline_choice_min_options: 2,
  entries: [
    {
      kind: "free_text_criteria",
      question_number: "2",
      question_text: "Förklara fotosyntesen.",
      points: 3,
      criteria: [
        { text: "Tar upp koldioxid", points: 1 },
        { text: "Beskriver sockerbildningen", points: 2 },
      ],
    },
    {
      kind: "all_or_nothing",
      question_number: "4",
      question_text: "Vatten kokar vid ...",
      points: 2,
    },
    {
      kind: "rounded_gaps",
      question_number: "6",
      question_text: "Fyll i luckorna.",
      points: 4,
      gap_points: 1.33,
    },
  ],
};

/**
 * The fixture exam without client-side export blockers. The default fixture
 * holds two questions whose proposed key is unreviewed, which the menu
 * blocks before any request, so exports that must reach the server use this.
 */
export function exportableResponse(params: {
  conversion?: ExamWorkspaceConversionStatus | null;
  version: number;
}) {
  const response = buildResponse(params);
  for (const document of [response.document, response.saved_document]) {
    document.items = document.items.map((item) =>
      item.item_id === "item_003" || item.item_id === "item_004"
        ? buildFreeTextItem(Number(item.item_id.slice(-1)))
        : item,
    );
  }
  return response;
}

export const wrappers: ViewWrapper[] = [];

/** The mocks `arrangeExportApis` resets and primes before every test. */
export interface ExportApiMocks {
  api: Record<string, Mock> & {
    getExamWorkspaceConversionStatus: Mock;
    getExamWorkspaceDocument: Mock;
    getExamWorkspaceExportChecklist: Mock;
    importExamWorkspaceDocument: Mock;
    listExamWorkspaceDocuments: Mock;
  };
  download: { triggerBrowserDownload: Mock };
}

/** Reset every mock and prime the finished import of the exportable fixture exam. */
export function arrangeExportApis({ api, download }: ExportApiMocks): void {
  for (const mock of Object.values(api)) {
    mock.mockReset();
  }
  api.getExamWorkspaceConversionStatus.mockResolvedValue(succeededConversion);
  download.triggerBrowserDownload.mockReset();
  api.importExamWorkspaceDocument.mockImplementation(async () => {
    api.getExamWorkspaceDocument.mockResolvedValueOnce(
      exportableResponse({ conversion: succeededConversion, version: 1 }),
    );
    return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
  });
  api.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  api.getExamWorkspaceExportChecklist.mockResolvedValue({ entries: [] });
}

export function unmountWrappers(): void {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount();
  document.body.replaceChildren();
}

/** The workspace with the fixture exam imported, attached so the body-level menu is reachable. */
export async function mountImported(): Promise<ViewWrapper> {
  const { wrapper } = await mountExamWorkspace({}, "desktop", document.body);
  wrappers.push(wrapper);
  await importFixtureDocument(wrapper);
  return wrapper;
}

/** An element anywhere in the page: the Exportera menu is teleported to the body. */
export function page(testId: string): DOMWrapper<HTMLElement> | null {
  const element = document.body.querySelector<HTMLElement>(`[data-test="${testId}"]`);
  return element ? new DOMWrapper(element) : null;
}

export function pageAll(testId: string): DOMWrapper<HTMLElement>[] {
  return Array.from(document.body.querySelectorAll<HTMLElement>(`[data-test="${testId}"]`)).map(
    (element) => new DOMWrapper(element),
  );
}

export function requirePage(testId: string): DOMWrapper<HTMLElement> {
  const found = page(testId);
  if (!found) throw new Error(`Missing [data-test="${testId}"]`);
  return found;
}

export async function openMenu(wrapper: ViewWrapper): Promise<void> {
  if (!page("exam-workspace-export-menu")) {
    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    await flushPromises();
  }
}

/** Download `target` through the header menu. */
export async function exportFromMenu(wrapper: ViewWrapper, target: "qti" | "pdf" | "docx"): Promise<void> {
  await openMenu(wrapper);
  await requirePage(`exam-workspace-export-${target}`).trigger("click");
  await flushPromises();
}

/** Open the Exportera drawer through "Fler val …". */
export async function openExportDrawer(wrapper: ViewWrapper): Promise<void> {
  await openMenu(wrapper);
  await requirePage("exam-workspace-export-more").trigger("click");
  await flushPromises();
  expect(wrapper.find('[data-test="exam-workspace-drawer-export"]').exists()).toBe(true);
}

/** Open the Exportera drawer through the menu's "Det här tappar Exam.net" entry. */
export async function openChecklistDrawer(wrapper: ViewWrapper): Promise<void> {
  await openMenu(wrapper);
  await requirePage("exam-workspace-export-checklist-open").trigger("click");
  await flushPromises();
  expect(wrapper.find('[data-test="exam-workspace-export-checklist"]').exists()).toBe(true);
}

export function menuFormatDisabled(target: string): string | undefined {
  return requirePage(`exam-workspace-export-${target}`).attributes("aria-disabled");
}

/** Close the Exportera menu so a later `openMenu` reopens it from the current state. */
export async function closeMenu(wrapper: ViewWrapper): Promise<void> {
  if (page("exam-workspace-export-menu")) {
    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    await flushPromises();
  }
}
