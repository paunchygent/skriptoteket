/**
 * Skriptoteket-owned exam workspace parent/child structure transport.
 *
 * Domain purpose:
 *   Thin typed client for the exam workspace instruction (parent) and
 *   deluppgift (child) commands: create an instruction, add, reorder and
 *   delete a deluppgift, and delete an instruction with or without its
 *   questions.
 *
 * Relationships:
 *   - Uses `api/client.ts` helpers and `documentPath` from `api/examWorkspace.ts`.
 *   - Types come from the generated OpenAPI schema (`api/openapi.d.ts`).
 *   - Consumed by `views/apps/exam-workspace/useExamWorkspaceStructure.ts`.
 */

import { apiFetch, apiPost, apiPut } from "./client";
import { documentPath } from "./examWorkspace";
import type { ExamWorkspaceDeleteResponse, ExamWorkspaceDocumentResponse } from "./examWorkspace";
import type { components } from "./openapi";

type Schemas = components["schemas"];

export type NewParentChild = Schemas["NewParentChild"];

function parentsPath(lineageId: string): string {
  return `${documentPath(lineageId)}/parents`;
}

/** Parent commands apply to the server's newest undo step and store one step each. */
export async function createExamWorkspaceParent(
  lineageId: string,
  body: Schemas["CreateExamParentRequest"],
): Promise<ExamWorkspaceDocumentResponse> {
  return await apiPost<Schemas["ExamWorkspaceDocumentResponse"]>(parentsPath(lineageId), body);
}

export async function addExamWorkspaceChild(
  lineageId: string,
  parentId: string,
  body: Schemas["AddExamChildRequest"],
): Promise<ExamWorkspaceDocumentResponse> {
  return await apiPost<Schemas["ExamWorkspaceDocumentResponse"]>(
    `${parentsPath(lineageId)}/${encodeURIComponent(parentId)}/children`,
    body,
  );
}

/** Delete one deluppgift; deleting the last one removes its emptied instruction too. */
export async function deleteExamWorkspaceChild(
  lineageId: string,
  parentId: string,
  itemId: string,
  expectedCursor: string,
): Promise<ExamWorkspaceDeleteResponse> {
  const body: Schemas["ParentCommandRequest"] = { expected_cursor: expectedCursor };
  return await apiFetch<Schemas["ExamWorkspaceDeleteResponse"]>(
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
  return await apiPut<Schemas["ExamWorkspaceDocumentResponse"]>(
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
  return await apiFetch<Schemas["ExamWorkspaceDeleteResponse"]>(
    `${parentsPath(lineageId)}/${encodeURIComponent(parentId)}${PARENT_DELETE_SUFFIX[mode]}`,
    { body, method: "DELETE" },
  );
}
