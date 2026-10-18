/**
 * Skriptoteket-owned exam workspace server structure commands.
 *
 * Domain purpose:
 *   Thin typed client for the server-side structure commands on an exam
 *   workspace document: create an instruction, group marked questions into a
 *   new part, insert an empty part, move a question into, out of or between
 *   parts, add, delete and reorder a part's deluppgifter, delete an
 *   instruction, and change one question's type. Every command runs against
 *   the server's newest undo step and stores one step each.
 *
 * Relationships:
 *   - Transport types and the document path helper come from `./examWorkspace`.
 *   - Consumed by `views/apps/exam-workspace/useExamWorkspaceStructure.ts`.
 */

import { apiFetch, apiPost, apiPut } from "./client";
import { documentPath } from "./examWorkspace";
import type {
  ChangeExamWorkspaceItemTypeResponse,
  ExamWorkspaceCreatedPartResponse,
  ExamWorkspaceDeleteResponse,
  ExamWorkspaceDocumentResponse,
} from "./examWorkspace";
import type { components } from "./openapi";

type Schemas = components["schemas"];

function parentsPath(lineageId: string): string {
  return `${documentPath(lineageId)}/parents`;
}

/** Parent commands apply to the server's newest undo step and store one step each. */
export async function createExamWorkspaceParent(
  lineageId: string,
  body: Schemas["CreateExamParentRequest"],
): Promise<ExamWorkspaceDocumentResponse> {
  return await apiPost<ExamWorkspaceDocumentResponse>(parentsPath(lineageId), body);
}

/** Group marked standalone questions into one new part (G2, G10). */
export async function groupExamWorkspaceItems(
  lineageId: string,
  itemIds: string[],
  expectedCursor: string,
): Promise<ExamWorkspaceCreatedPartResponse> {
  const body: Schemas["GroupExamItemsRequest"] = {
    expected_cursor: expectedCursor,
    item_ids: itemIds,
  };
  return await apiPost<ExamWorkspaceCreatedPartResponse>(`${parentsPath(lineageId)}/group`, body);
}

/** Insert a part with an empty instruction at the chosen top-level position (G9). */
export async function createEmptyExamWorkspacePart(
  lineageId: string,
  position: number,
  expectedCursor: string,
): Promise<ExamWorkspaceCreatedPartResponse> {
  const body: Schemas["CreateEmptyExamPartRequest"] = {
    expected_cursor: expectedCursor,
    position,
  };
  return await apiPost<ExamWorkspaceCreatedPartResponse>(`${parentsPath(lineageId)}/empty`, body);
}

/** Move one question into a part, out to standalone, or between parts (G3, R3, R4). */
export async function moveExamWorkspaceItem(
  lineageId: string,
  itemId: string,
  targetParentId: string | null,
  expectedCursor: string,
): Promise<ExamWorkspaceDocumentResponse> {
  const body: Schemas["MoveExamItemRequest"] = {
    expected_cursor: expectedCursor,
    item_id: itemId,
    target_parent_id: targetParentId,
  };
  return await apiPost<ExamWorkspaceDocumentResponse>(`${parentsPath(lineageId)}/move`, body);
}

export async function addExamWorkspaceChild(
  lineageId: string,
  parentId: string,
  body: Schemas["AddExamChildRequest"],
): Promise<ExamWorkspaceDocumentResponse> {
  return await apiPost<ExamWorkspaceDocumentResponse>(
    `${parentsPath(lineageId)}/${encodeURIComponent(parentId)}/children`,
    body,
  );
}

/** Delete one deluppgift; deleting the last one keeps the part as an instruction block. */
export async function deleteExamWorkspaceChild(
  lineageId: string,
  parentId: string,
  itemId: string,
  expectedCursor: string,
): Promise<ExamWorkspaceDeleteResponse> {
  const body: Schemas["ParentCommandRequest"] = { expected_cursor: expectedCursor };
  return await apiFetch<ExamWorkspaceDeleteResponse>(
    `${parentsPath(lineageId)}/${encodeURIComponent(parentId)}/children/${encodeURIComponent(itemId)}`,
    { body, method: "DELETE" },
  );
}

export async function reorderExamWorkspaceChildren(
  lineageId: string,
  parentId: string,
  itemIds: string[],
  expectedCursor: string,
): Promise<ExamWorkspaceDocumentResponse> {
  const body: Schemas["ReorderExamChildrenRequest"] = {
    expected_cursor: expectedCursor,
    item_ids: itemIds,
  };
  return await apiPut<ExamWorkspaceDocumentResponse>(
    `${parentsPath(lineageId)}/${encodeURIComponent(parentId)}/children/order`,
    body,
  );
}

/** "keep_questions" removes only the heading; "with_questions" removes its questions too. */
export type ExamParentDeleteMode = "keep_questions" | "with_questions";

const PARENT_DELETE_SUFFIX: Record<ExamParentDeleteMode, string> = {
  keep_questions: "",
  with_questions: "/with-children",
};

/**
 * Delete an instruction (user ruling 2026-10-17). By default its questions
 * stay in place as standalone questions; "with_questions" deletes them too.
 * A deletion that would leave the exam without a question is refused with
 * 422 `details.reason` "exam_requires_question".
 */
export async function deleteExamWorkspaceParent(
  lineageId: string,
  parentId: string,
  mode: ExamParentDeleteMode,
  expectedCursor: string,
): Promise<ExamWorkspaceDeleteResponse> {
  const body: Schemas["ParentCommandRequest"] = { expected_cursor: expectedCursor };
  return await apiFetch<ExamWorkspaceDeleteResponse>(
    `${parentsPath(lineageId)}/${encodeURIComponent(parentId)}${PARENT_DELETE_SUFFIX[mode]}`,
    { body, method: "DELETE" },
  );
}

/** Change one question's type; the response names the content the new type could not keep. */
export async function changeExamWorkspaceItemType(
  lineageId: string,
  body: Schemas["ChangeExamWorkspaceItemTypeRequest"],
): Promise<ChangeExamWorkspaceItemTypeResponse> {
  return await apiPost<ChangeExamWorkspaceItemTypeResponse>(
    `${documentPath(lineageId)}/change-type`,
    body,
  );
}
