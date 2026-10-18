/**
 * Exam workspace structure commands.
 *
 * Domain purpose:
 *   Add a question of any kind after the selected unit, delete a standalone
 *   question, add an instruction with deluppgifter, add, move and delete a
 *   deluppgift, and change a question's type (TASK-SKRIPT-39-06-03, 39-06-05,
 *   40-04-03). Adding and deleting a standalone question are local structural
 *   edits; the parent commands and Byt frågetyp run on the server against its
 *   newest undo step, so the pending edit is stored first and the response's
 *   document becomes the next step. After Byt frågetyp the question shows an
 *   inline notice naming what the change removed; the header Ångra reverts it
 *   (user ruling 2026-10-17: no Ångra in toasts). Deleting an instruction
 *   keeps its questions as standalone questions by default, or deletes them
 *   with it; deleting its last question removes the emptied heading too, and
 *   an inline notice says so (TASK-SKRIPT-39-06-07, user ruling 2026-10-17).
 *   A delete that would leave the exam without a question is refused inline,
 *   never in a toast.
 *
 * Relationships:
 *   - Edits through `useExamWorkspaceDocument` (`editDocument`,
 *     `applyCommandResponse`); stores through `useExamWorkspaceHistory.flush`.
 *   - Pure transitions and copy in `examWorkspaceStructure`.
 */

import { computed, ref } from "vue";
import type { Ref } from "vue";

import { isApiError } from "../../../api/client";
import type {
  ExamParentDeleteMode,
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
  historyCursor: Ref<string | null>;
  lineageId: () => string | null;
  savedRevision: () => number | null;
  isBusy: () => boolean;
  /** The shared store half the structure commands run through. */
  shared: ExamWorkspaceSharedStore;
  editDocument: (
    edit: (document: NativeExamDocument) => NativeExamDocument,
    selectId?: string | null,
  ) => boolean;
  applyCommandResponse: (response: ExamWorkspaceDocumentResponse) => void;
  selectItem: (itemId: string) => void;
  /** Store the pending edit, and an undone step as the newest one; false when that failed. */
  flush: (settle: boolean) => Promise<boolean>;
  onConflict: () => Promise<void>;
  /** Run a command whose response replaces the copy: locks editing and keeps arrivals. */
  replaceCopy: <T>(run: () => Promise<T>) => Promise<T>;
};

export type ExamWorkspaceTypeNotice = { itemId: string; kind: NativeExamItemKind; text: string };

/** An inline outcome: a type change, an instruction removed with its last question, or a refused delete. */
export type ExamWorkspaceNotice = { kind: "type" | "delete" | "refused"; text: string };

const LAST_QUESTION_COPY = "Provet måste ha minst en fråga.";
const HEADING_REMOVED_COPY = "Instruktionen hade inga frågor kvar och togs också bort.";

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
  /** Said once where the selection lands after a delete took more than the teacher picked. */
  const deleteNotice = ref<ExamWorkspaceNotice | null>(null);

  const blocked = computed(() => running.value || deps.isBusy());

  function selectedUnitIndex(document: NativeExamDocument): number {
    return examWorkspaceUnitIndex(examWorkspaceUnits(document), { itemId: deps.selectedItemId.value });
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
      if (isApiError(error) && error.status === 409) {
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
        deps.shared.deleteExamWorkspaceChild(lineageId, parent.parent_id, itemId, cursor),
      ).then((response) => {
        if (!response) {
          return;
        }
        if (next && response.document.items.some((item) => item.item_id === next)) {
          deps.selectItem(next);
        }
        if (response.removed_parent_id !== null) {
          deleteNotice.value = { kind: "delete", text: HEADING_REMOVED_COPY };
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
      deps.shared.deleteExamWorkspaceParent(lineageId, parentId, mode, cursor),
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
      }),
    );
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
      deps.shared.reorderExamWorkspaceChildren(lineageId, parentId, itemIds, cursor),
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
    addInstruction,
    addItem,
    changeType,
    deleteItem,
    deleteNotice: computed(() => deleteNotice.value),
    deleteParent,
    dismissDeleteNotice,
    dismissTypeNotice,
    moveChild,
    running: computed(() => running.value),
    typeNotice: computed(() => typeNotice.value),
  };
}
