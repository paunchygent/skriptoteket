/**
 * Exam workspace structure commands.
 *
 * Domain purpose:
 *   Add a question of any kind after the selected top-level unit — the selected
 *   part entry when one is selected, otherwise the selected question — delete a
 *   standalone question, add an instruction with deluppgifter, group marked
 *   questions into a new part, add an empty part, move a question into, out of
 *   or between parts, add, move and delete a deluppgift, and change a question's
 *   type (TASK-SKRIPT-39-06-03, 39-06-05, 39-06-10, 40-04-03). Adding and
 *   deleting a standalone question are local structural edits; the parent
 *   commands and Byt frågetyp run on the server against its newest undo step, so
 *   the pending edit is stored first and the response's document becomes the
 *   next step. After Byt frågetyp the question shows an inline notice naming what
 *   the change removed;
 *   the header Ångra reverts it (user ruling 2026-10-17: no Ångra in toasts).
 *   Deleting an instruction keeps its questions as standalone questions by
 *   default, or deletes them with it; deleting its last question keeps the part
 *   as an instruction block (TASK-SKRIPT-39-06-10 G8; TASK-SKRIPT-39-06-07,
 *   user ruling 2026-10-17). A delete that would leave the exam without a
 *   question is refused inline, never in a toast.
 *
 * Relationships:
 *   - Edits through `useExamWorkspaceDocument` (`editDocument`,
 *     `applyCommandResponse`); stores through `useExamWorkspaceHistory.flush`.
 *   - Pure transitions and copy in `examWorkspaceStructure`.
 */

import { computed, ref } from "vue";
import type { Ref } from "vue";

import { isApiError } from "../../../api/client";
import { isEditLeaseHeldError } from "./useExamWorkspaceEditLease";
import type { ExamParentDeleteMode } from "../../../api/examWorkspaceStructureCommands";
import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
  NativeExamItemKind,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { nextItemId } from "./examWorkspaceConversionMerge";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import type { TeacherItemKind } from "./examWorkspaceItemEdits";
import type { ExamWorkspaceSharedStore } from "./examWorkspaceStore";
import {
  examWorkspaceChangeTypeNotice,
  examWorkspaceIsOnlyQuestion,
  examWorkspaceNeighbourId,
  examWorkspaceUnitIndex,
  examWorkspaceUnits,
  withItemAfterUnit,
  withoutStandaloneItem,
} from "./examWorkspaceStructure";

const COMMAND_FAILURE_COPY = "Ändringen kunde inte göras. Försök igen.";
const NEW_INSTRUCTION_TEXT = "Ny instruktion";

export type ExamWorkspaceStructureDeps = {
  workspaceDocument: Ref<NativeExamDocument | null>;
  selectedItemId: Ref<string | null>;
  /** The part entry the teacher selected, or null; a structural insert lands after it (G9). */
  selectedParentId: Ref<string | null>;
  historyCursor: Ref<string | null>;
  lineageId: () => string | null;
  savedRevision: () => number | null;
  isBusy: () => boolean;
  /** The shared store half the structure commands run through. */
  shared: ExamWorkspaceSharedStore;
  /** The tab id the edit lease holds; every command carries it. */
  tabId: () => string;
  /** True while another tab holds the edit lease: every command refuses. */
  isReadOnly: () => boolean;
  /** A command met `EDIT_LEASE_HELD`: turn read-only and keep the pending edit. */
  noteLeaseLost: () => void;
  editDocument: (
    edit: (document: NativeExamDocument) => NativeExamDocument,
    selectId?: string | null,
  ) => boolean;
  applyCommandResponse: (response: ExamWorkspaceDocumentResponse) => void;
  selectItem: (itemId: string) => void;
  /** Open a part's instruction in the editor, reusing the selection composable's entry selection. */
  selectParent: (parentId: string) => void;
  /** Store the pending edit, and an undone step as the newest one; false when that failed. */
  flush: (settle: boolean) => Promise<boolean>;
  onConflict: () => Promise<void>;
  /** Run a command whose response replaces the copy: locks editing and keeps arrivals. */
  replaceCopy: <T>(run: () => Promise<T>) => Promise<T>;
};

export type ExamWorkspaceTypeNotice = { itemId: string; kind: NativeExamItemKind; text: string };

/** An inline outcome: a type change, or a refused delete. */
export type ExamWorkspaceNotice = { kind: "type" | "refused"; text: string };

const LAST_QUESTION_COPY = "Provet måste ha minst en fråga.";

/** The server's refusal of a delete that would leave the exam without a question. */
function isExamRequiresQuestion(error: unknown): boolean {
  return (
    isApiError(error) &&
    error.status === 422 &&
    typeof error.details === "object" &&
    error.details !== null &&
    (error.details as { reason?: unknown }).reason === "exam_requires_question"
  );
}

function newChildContent(kind: TeacherItemKind) {
  // The server assigns the child's id and sequence.
  return newTeacherItem("item_001", 1, kind);
}

export function useExamWorkspaceStructure(deps: ExamWorkspaceStructureDeps) {
  const toast = useToast();
  const running = ref(false);
  const typeNotice = ref<ExamWorkspaceTypeNotice | null>(null);
  /** The refusal of a delete that would leave the exam without a question, shown inline. */
  const deleteNotice = ref<ExamWorkspaceNotice | null>(null);

  const blocked = computed(() => running.value || deps.isBusy() || deps.isReadOnly());

  /**
   * The unit a structural insert lands after: the selected part entry when the
   * teacher selected one, otherwise the document's selected question.
   */
  function selectedUnitIndex(document: NativeExamDocument): number {
    const parentId = deps.selectedParentId.value;
    return examWorkspaceUnitIndex(
      examWorkspaceUnits(document),
      parentId === null ? { itemId: deps.selectedItemId.value } : { parentId },
    );
  }

  /** Run one server command against the newest stored step; select what it added. */
  async function runCommand<Response extends ExamWorkspaceDocumentResponse>(
    command: (lineageId: string, cursor: string) => Promise<Response>,
  ): Promise<Response | null> {
    if (blocked.value) {
      return null;
    }
    running.value = true;
    deleteNotice.value = null;
    try {
      return await deps.replaceCopy(() => commandOutcome(command));
    } finally {
      running.value = false;
    }
  }

  async function commandOutcome<Response extends ExamWorkspaceDocumentResponse>(
    command: (lineageId: string, cursor: string) => Promise<Response>,
  ): Promise<Response | null> {
    try {
      // The response replaces the copy: without the pending edit stored, it would be lost.
      if (!(await deps.flush(true))) {
        return null;
      }
      const lineageId = deps.lineageId();
      const cursor = deps.historyCursor.value;
      const before = new Set(deps.workspaceDocument.value?.items.map((item) => item.item_id) ?? []);
      if (!lineageId || !cursor) {
        return null;
      }
      const response = await command(lineageId, cursor);
      if (deps.lineageId() !== lineageId) {
        return null;
      }
      deps.applyCommandResponse(response);
      const added = response.document.items.find((item) => !before.has(item.item_id));
      if (added) {
        deps.selectItem(added.item_id);
      }
      return response;
    } catch (error) {
      if (isEditLeaseHeldError(error)) {
        deps.noteLeaseLost();
      } else if (isApiError(error) && error.status === 409) {
        await deps.onConflict();
      } else if (isExamRequiresQuestion(error)) {
        deleteNotice.value = { kind: "refused", text: (error as Error).message };
      } else if (isApiError(error) && error.status === 422) {
        toast.failure(error.message);
      } else {
        toast.failure(COMMAND_FAILURE_COPY);
      }
      return null;
    }
  }

  function addItem(kind: TeacherItemKind): void {
    const document = deps.workspaceDocument.value;
    if (!document || blocked.value) {
      return;
    }
    const itemId = nextItemId(document.items.map((item) => item.item_id));
    const item = newTeacherItem(itemId, 1, kind);
    const after = selectedUnitIndex(document);
    deps.editDocument(
      (current) => withItemAfterUnit(current, item, after < 0 ? examWorkspaceUnits(current).length - 1 : after),
      itemId,
    );
  }

  function deleteItem(itemId: string): void {
    const document = deps.workspaceDocument.value;
    if (!document || blocked.value) {
      return;
    }
    const parent = document.parents.find((entry) => entry.item_ids.includes(itemId));
    if (parent) {
      const next = examWorkspaceNeighbourId(document, itemId);
      void runCommand((lineageId, cursor) =>
        deps.shared.deleteExamWorkspaceChild(lineageId, parent.parent_id, itemId, cursor, deps.tabId()),
      ).then((response) => {
        if (!response) {
          return;
        }
        // The part stays as an instruction block, so no notice is needed.
        if (next && response.document.items.some((item) => item.item_id === next)) {
          deps.selectItem(next);
        }
      });
      return;
    }
    if (examWorkspaceIsOnlyQuestion(document, itemId)) {
      deleteNotice.value = { kind: "refused", text: LAST_QUESTION_COPY };
      return;
    }
    deleteNotice.value = null;
    deps.editDocument(
      (current) => withoutStandaloneItem(current, itemId),
      examWorkspaceNeighbourId(document, itemId),
    );
  }

  /** Remove an instruction: only its heading, or with its questions. */
  async function deleteParent(parentId: string, mode: ExamParentDeleteMode): Promise<void> {
    const document = deps.workspaceDocument.value;
    const parent = document?.parents.find((entry) => entry.parent_id === parentId);
    if (!document || !parent) {
      return;
    }
    const firstChild = parent.item_ids[0] ?? null;
    const lastChild = parent.item_ids[parent.item_ids.length - 1] ?? null;
    const next =
      mode === "keep_questions" ? firstChild : lastChild && examWorkspaceNeighbourId(document, lastChild);
    const response = await runCommand((lineageId, cursor) =>
      deps.shared.deleteExamWorkspaceParent(lineageId, parentId, mode, cursor, deps.tabId()),
    );
    if (response && next && response.document.items.some((item) => item.item_id === next)) {
      deps.selectItem(next);
    }
  }

  function dismissDeleteNotice(): void {
    deleteNotice.value = null;
  }

  async function addInstruction(): Promise<void> {
    const document = deps.workspaceDocument.value;
    if (!document) {
      return;
    }
    const after = selectedUnitIndex(document);
    const position = after < 0 ? examWorkspaceUnits(document).length : after + 1;
    await runCommand((lineageId, cursor) =>
      deps.shared.createExamWorkspaceParent(lineageId, {
        child: newChildContent("free_text"),
        expected_cursor: cursor,
        instruction: [
          { heading_level: null, segments: [{ kind: "text", marks: [], text: NEW_INSTRUCTION_TEXT }] },
        ],
        position,
        tab_id: deps.tabId(),
      }),
    );
  }

  async function addChild(parentId: string, kind: TeacherItemKind): Promise<void> {
    const parent = deps.workspaceDocument.value?.parents.find((entry) => entry.parent_id === parentId);
    if (!parent) {
      return;
    }
    await runCommand((lineageId, cursor) =>
      deps.shared.addExamWorkspaceChild(lineageId, parentId, {
        child: newChildContent(kind),
        expected_cursor: cursor,
        position: parent.item_ids.length,
        tab_id: deps.tabId(),
      }),
    );
  }

  /** Group marked standalone questions into one new part and open its instruction (G4, G10). */
  async function groupItems(itemIds: string[]): Promise<boolean> {
    const response = await runCommand((lineageId, cursor) =>
      deps.shared.groupExamWorkspaceItems(lineageId, itemIds, cursor, deps.tabId()),
    );
    if (!response) {
      return false;
    }
    deps.selectParent(response.created_parent_id);
    return true;
  }

  /** Insert a part with an empty instruction after the selected top-level unit and open its editor (G9). */
  async function addEmptyPart(): Promise<void> {
    const document = deps.workspaceDocument.value;
    if (!document) {
      return;
    }
    const after = selectedUnitIndex(document);
    const position = after < 0 ? examWorkspaceUnits(document).length : after + 1;
    const response = await runCommand((lineageId, cursor) =>
      deps.shared.createEmptyExamWorkspacePart(lineageId, position, cursor, deps.tabId()),
    );
    if (response) {
      deps.selectParent(response.created_parent_id);
    }
  }

  /** Move one question into a part, out to standalone, or between parts (G3, R3, R4). */
  async function moveItem(itemId: string, targetParentId: string | null): Promise<void> {
    const response = await runCommand((lineageId, cursor) =>
      deps.shared.moveExamWorkspaceItem(lineageId, itemId, targetParentId, cursor, deps.tabId()),
    );
    if (response) {
      deps.selectItem(itemId);
    }
  }

  async function moveChild(parentId: string, itemId: string, delta: -1 | 1): Promise<void> {
    const parent = deps.workspaceDocument.value?.parents.find((entry) => entry.parent_id === parentId);
    const from = parent?.item_ids.indexOf(itemId) ?? -1;
    const to = from + delta;
    if (!parent || from < 0 || to < 0 || to >= parent.item_ids.length) {
      return;
    }
    const itemIds = [...parent.item_ids];
    itemIds.splice(from, 1);
    itemIds.splice(to, 0, itemId);
    await runCommand((lineageId, cursor) =>
      deps.shared.reorderExamWorkspaceChildren(lineageId, parentId, itemIds, cursor, deps.tabId()),
    );
  }

  async function changeType(itemId: string, kind: NativeExamItemKind): Promise<void> {
    const current = deps.workspaceDocument.value?.items.find((item) => item.item_id === itemId);
    if (!current || current.kind === kind) {
      return;
    }
    let dropped: string[] = [];
    const response = await runCommand(async (lineageId, cursor) => {
      const revision = deps.savedRevision();
      const changed = await deps.shared.changeExamWorkspaceItemType(lineageId, {
        expected_cursor: cursor,
        expected_revision: revision ?? 0,
        item_id: itemId,
        tab_id: deps.tabId(),
        target_kind: kind,
      });
      dropped = changed.dropped_content;
      return changed;
    });
    if (response) {
      typeNotice.value = { itemId, kind, text: examWorkspaceChangeTypeNotice(kind, dropped) };
    }
  }

  function dismissTypeNotice(): void {
    typeNotice.value = null;
  }

  return {
    addChild,
    addEmptyPart,
    addInstruction,
    addItem,
    changeType,
    deleteItem,
    deleteNotice: computed(() => deleteNotice.value),
    deleteParent,
    dismissDeleteNotice,
    dismissTypeNotice,
    groupItems,
    moveChild,
    moveItem,
    running: computed(() => running.value),
    typeNotice: computed(() => typeNotice.value),
  };
}
