/**
 * Progressive-conversion slice test harness.
 *
 * Domain purpose:
 *   Shared fixtures, lifecycle and editor assertions for the progressive DOCX
 *   conversion specs (batch delivery, completion, save conflicts).
 *
 * Relationships:
 *   - Builds on `ExamWorkspaceSlice.specSupport.ts` for the mounted view.
 *   - Each spec owns its own `api/examWorkspace` module mock and passes it to
 *     `installProgressiveConversionLifecycle`.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, expect, vi, type Mock } from "vitest";

import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceConversionUnit,
  ExamWorkspaceDocumentResponse,
  NativeExamItem,
} from "../../api/examWorkspace";
import { EXAM_WORKSPACE_CONVERSION_POLL_MS } from "./exam-workspace/useExamWorkspaceDocument";
import {
  buildFreeTextItem,
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  selectItemRow,
  type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";

type UnitState = ExamWorkspaceConversionUnit["state"];

export function placeholder(sequence: number): NativeExamItem {
  return {
    ...buildFreeTextItem(sequence),
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: `Källtext ${sequence }` }] }],
    review: {
      confidence: 0,
      parse_origin: "llm_parsed",
      reasons: ["Frågan konverteras fortfarande."],
      state: "review_required",
    },
  };
}

/** A converted item is told apart from its placeholder by its points: `20 + sequence`. */
export function converted(sequence: number): NativeExamItem {
  return { ...buildFreeTextItem(sequence), points: 20 + sequence };
}

/** A saved revision with the conversion state the server reads under the same lock. */
export function revision(
  version: number,
  items: NativeExamItem[],
  conversion: ExamWorkspaceConversionStatus | null,
): ExamWorkspaceDocumentResponse {
  const response = buildResponse({ version });
  const document = { ...response.document, items };
  return { ...response, conversion, document, saved_document: document };
}

export function status(
  state: ExamWorkspaceConversionStatus["state"],
  documentRevision: number | null,
  units: UnitState[],
): ExamWorkspaceConversionStatus {
  return {
    job_id: "job-1",
    lineage_id: "lineage-1",
    state,
    error_message: null,
    summary: null,
    document_revision: documentRevision,
    questions_total: 3,
    questions_done: units.filter((unit) => unit !== "converting").length,
    units: units.map((unitState, index) => ({
      unit_id: `q${index + 1}`,
      question: true,
      state: unitState,
      item_ids: [`item_00${index + 1}`],
    })),
  };
}

export const FIRST_STATUS = status("running", 1, ["ready", "converting", "converting"]);
export const FIRST = revision(1, [converted(1), placeholder(2), placeholder(3)], FIRST_STATUS);
export const SECOND_STATUS = status("running", 2, ["ready", "ready", "ready"]);
export const SECOND = revision(2, [converted(1), converted(2), converted(3)], SECOND_STATUS);

export type ProgressiveApiMocks = Record<string, Mock>;

let mountedView: ViewWrapper | undefined;

/**
 * Registers the lifecycle every progressive spec shares: fake timers, mocks
 * reset to a first-batch import, and the mounted view unmounted afterwards.
 */
export function installProgressiveConversionLifecycle(apiMocks: ProgressiveApiMocks) {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    for (const mock of Object.values(apiMocks)) mock.mockReset();
    apiMocks.importExamWorkspaceDocument.mockResolvedValue(status("queued", null, []));
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(FIRST_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(FIRST);
    apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  });
  afterEach(() => {
    mountedView?.unmount();
    mountedView = undefined;
    vi.useRealTimers();
  });
}

/** Mount the view and unmount it after the test. */
export async function mountTracked(query: Record<string, string> = {}) {
  const mounted = await mountExamWorkspace(query);
  mountedView = mounted.wrapper;
  return mounted;
}

export async function uploadFirstBatch(): Promise<ViewWrapper> {
  const { wrapper } = await mountTracked();
  await importFixtureDocument(wrapper);
  return wrapper;
}

export async function tick() {
  await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_CONVERSION_POLL_MS);
  await flushPromises();
}

export async function editPoints(view: ViewWrapper, itemId: string, points: string) {
  await selectItemRow(view, itemId);
  await view.get('[data-test="exam-workspace-item-points-input"]').setValue(points);
}

export async function pointsOf(view: ViewWrapper, itemId: string): Promise<string> {
  await selectItemRow(view, itemId);
  return (view.get('[data-test="exam-workspace-item-points-input"]').element as HTMLInputElement).value;
}

/** Dispatch an input event straight on the element, past its `disabled` attribute. */
export async function forceInput(view: ViewWrapper, control: string, value: string) {
  const element = view.get(`[data-test="${control}"]`).element as HTMLInputElement;
  element.value = value;
  element.dispatchEvent(new Event("input"));
  await flushPromises();
}

/** Dispatch a click straight on the element, past its `disabled` attribute. */
export async function forceClick(view: ViewWrapper, control: string) {
  view.get(`[data-test="${control}"]`).element.dispatchEvent(new MouseEvent("click"));
  await flushPromises();
}

const EDIT_CONTROLS = [
  "exam-workspace-item-points-input",
  "exam-workspace-type",
  "exam-workspace-review",
  "exam-workspace-criterion-add",
];

/**
 * Every edit control of the selected item's editor is editable, or every one is
 * locked. A converting question hides its criteria/choice/category fields and
 * disables points, body, type and review, so a locked control may be absent or
 * disabled; an editable control must be present and enabled.
 */
export function expectEditable(view: ViewWrapper, editable: boolean) {
  for (const control of EDIT_CONTROLS) {
    const element = view.find(`[data-test="${control}"]`);
    if (editable) {
      expect(element.exists(), `${control} present`).toBe(true);
      expect(element.attributes("disabled"), `${control} enabled`).toBeUndefined();
    } else if (element.exists()) {
      expect(element.attributes("disabled"), `${control} disabled`).toBe("");
    }
  }
  const body = view.get('[data-test="exam-workspace-body-paragraph-0"]').attributes("contenteditable");
  if (editable) {
    expect(body).not.toBe("false");
  } else {
    expect(body).toBe("false");
  }
}

export function convertingNoticeShown(view: ViewWrapper): boolean {
  return view.find('[data-test="exam-workspace-converting-notice"]').exists();
}
