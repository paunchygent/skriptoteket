/**
 * Exam workspace walking-skeleton slice spec support.
 *
 * Purpose:
 *   Shared builders and view interactions for the walking-skeleton slice
 *   specs: the finished-import status, the accepted-answer row helpers for
 *   the teleported gap popover rows, gap clicking without layout, adding a
 *   question, and reading the saved document back from the mocked transport.
 *   Each spec file owns its own `api/examWorkspace` module mock, because a
 *   `vi.hoisted` mock cannot be shared across files; the save-reading helpers
 *   take the spec's save mock they read.
 */

import { Editor } from "@tiptap/core";
import { DOMWrapper, flushPromises } from "@vue/test-utils";
import type { Mock } from "vitest";

import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
  storeExamWorkspaceUndoStep,
} from "../../api/examWorkspace";
import {
  dispatchGapToolClick,
  gapPointerMiddle,
  stubLinearGapPointerGeometry,
} from "./exam-workspace/examWorkspaceGapToolPointer.specSupport";
import {
  buildResponse,
  type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";

/** The mocked step store one walking-skeleton spec reads back. */
export type StoreUndoStepMock = Mock<typeof storeExamWorkspaceUndoStep>;

/** Every input of one accepted-answer row list (a gap popover's or the Kort svar Svar field's). */
export function answerRowInputs(groupTestId: string): HTMLInputElement[] {
  return Array.from(
    document.querySelectorAll<HTMLInputElement>(`[data-test="${groupTestId}-input"]`),
  );
}

/** The accepted-answer row inputs of one gap in the open popover (teleported to the body). */
export function gapRowInputs(gapId: string): HTMLInputElement[] {
  return answerRowInputs(`exam-workspace-gap-values-${gapId}`);
}

/** Type a value into one accepted-answer row and commit the list, as leaving the row does. */
export async function commitAnswerRow(groupTestId: string, index: number, value: string): Promise<void> {
  const row = new DOMWrapper(answerRowInputs(groupTestId)[index]!);
  row.element.value = value;
  await row.trigger("input");
  row.element.dispatchEvent(new Event("change", { bubbles: true }));
  await flushPromises();
}

/** Type a value into one gap popover row and commit, as leaving the row does. */
export async function commitGapRow(gapId: string, index: number, value: string): Promise<void> {
  await commitAnswerRow(`exam-workspace-gap-values-${gapId}`, index, value);
}

/**
 * The TipTap editor mounted behind a surface element. The editor instance is
 * attached to its DOM node at mount; narrow the unknown attachment instead
 * of asserting its shape.
 */
function editorBehind(element: Element): Editor {
  if (!(element instanceof HTMLElement) || !("editor" in element)) {
    throw new Error("the question editor did not mount");
  }
  const attached: unknown = element.editor;
  if (!(attached instanceof Editor)) {
    throw new Error("the question editor did not mount");
  }
  return attached;
}

/** The Kort svar question-text surface's editor, to insert text jsdom cannot type. */
export function shortAnswerEditor(wrapper: ViewWrapper): Editor {
  return editorBehind(wrapper.get('[data-test="exam-workspace-short-answer-question"]').element);
}

/**
 * Click a gap in the question text as a user does. jsdom has no layout, so the
 * editor's own click handler is called with the gap as the clicked node.
 */
export async function clickGap(wrapper: ViewWrapper, gapId: string): Promise<void> {
  const editor = editorBehind(
    wrapper.get('[data-test="exam-workspace-body-editor-surface"]').element,
  );
  let pos = -1;
  editor.state.doc.descendants((node, nodePos) => {
    if (pos < 0 && node.type.name === "examGap" && node.attrs.gapId === gapId) pos = nodePos;
    return pos < 0;
  });
  const node = editor.state.doc.nodeAt(pos)!;
  editor.view.someProp("handleClickOn", (handler) =>
    handler(editor.view, pos, node, pos, new MouseEvent("click"), true),
  );
  await flushPromises();
}

/** Choose a question type from the list's Ny fråga menu (teleported to the body). */
export async function addQuestion(wrapper: ViewWrapper, kind: string): Promise<void> {
  await wrapper.find('[data-test="exam-workspace-new"]').trigger("click");
  document.body.querySelector<HTMLElement>(`[data-test="exam-workspace-new-${kind}"]`)!.click();
  await flushPromises();
}

/**
 * Click a word in the question text as the gap tool does. jsdom has no
 * layout, so the editor's own click handler is called at a position inside
 * the word, with the caret placed first as a real pointer press would and
 * the pointer stubbed onto the same 10px grid the gap tool reads.
 */
export async function clickWord(wrapper: ViewWrapper, word: string): Promise<void> {
  const editor = editorBehind(
    wrapper.get('[data-test="exam-workspace-body-editor-surface"]').element,
  );
  stubLinearGapPointerGeometry(editor);
  let pos = -1;
  editor.state.doc.descendants((node, nodePos) => {
    if (pos < 0 && node.isText && node.text?.includes(word)) {
      pos = nodePos + (node.text.indexOf(word) + 1);
    }
    return pos < 0;
  });
  if (pos < 0) {
    throw new Error(`no text "${word}"`);
  }
  editor.commands.setTextSelection(pos);
  dispatchGapToolClick(editor, pos, gapPointerMiddle(pos));
  await flushPromises();
}

export function rowStatus(wrapper: ViewWrapper, itemId: string): string | undefined {
  return wrapper
    .find(`[data-test="exam-workspace-row-${itemId}"] [role="img"][aria-label$="granskas"], [data-test="exam-workspace-row-${itemId}"] [role="img"][aria-label="Granskad"]`)
    .attributes("aria-label");
}

/** The imported exam with the given items as gap items keyed in two gaps, so one gap can be cleared on its own. */
export function buildTwoGapResponse(
  gapItemIds: string[] = ["item_004"],
): ExamWorkspaceDocumentResponse {
  const response = buildResponse({ conversion: succeededConversion, version: 1 });
  return {
    ...response,
    document: {
      ...response.document,
      items: response.document.items.map((item) =>
        gapItemIds.includes(item.item_id)
          ? {
              ...item,
              answer_key: { correct_choice_ids: [], match_pairs: [], origin: "teacher_authored" },
              kind: "gap_fill",
              body: [
                { heading_level: null, segments: [
                    { kind: "text", marks: [], text: "Vatten kokar vid" },
                    { gap_id: "gap_001", kind: "gap" },
                    { kind: "text", marks: [], text: "grader och fryser vid" },
                    { gap_id: "gap_002", kind: "gap" },
                    { kind: "text", marks: [], text: "grader." },
                  ],
                },
              ],
              gaps: [
                { accepted_values: ["100"], automatic_values: [], excluded_automatic_values: [], gap_id: "gap_001", options: [], correct_option_id: null },
                { accepted_values: ["0"], automatic_values: [], excluded_automatic_values: [], gap_id: "gap_002", options: [], correct_option_id: null },
              ],
            }
          : item,
      ),
    },
  };
}

/** The finished import: its poll status, and the conversion its fetched document carries. */
export const succeededConversion: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, phase: null, phase_started_at: null, questions_total: 0, questions_done: 0, units: [],
};

/** The first step store request the mocked transport received. */
export function firstStoreRequest(storeMock: StoreUndoStepMock): {
  lineageId: string;
  params: { expectedCursor: string; document: NativeExamDocument; afterStepId: string | null };
} {
  const first = storeMock.mock.calls[0];
  if (!first) {
    throw new Error("expected a store request");
  }
  const [lineageId, params] = first;
  return { lineageId, params };
}

/** The document of the latest step the mocked transport stored. */
export function lastStoredDocument(storeMock: StoreUndoStepMock): NativeExamDocument {
  const calls = storeMock.mock.calls;
  const last = calls[calls.length - 1];
  if (!last) {
    throw new Error("expected a stored document");
  }
  return last[1].document;
}
