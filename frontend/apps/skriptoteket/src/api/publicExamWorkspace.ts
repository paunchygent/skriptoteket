/**
 * Skriptoteket public exam workspace transport for guests.
 *
 * Domain purpose:
 *   The stateless public routes a signed-out guest uses: start a blank exam,
 *   apply one structural command or a type change, ask for answer
 *   misspellings, read the course catalog, and render an export or its
 *   Exam.net import checklist. A guest's exam lives only in the browser, so
 *   every call carries the whole document (and, for an export, the declared
 *   picture bytes) instead of naming a stored lineage.
 *
 * Relationships:
 *   - Uses the credential-omitting public API helpers of `api/client.ts`; a
 *     429 from the hourly limiter arrives as an `ApiError` exactly as any
 *     other public refusal does.
 *   - Mounts under the public Exam Converter namespace and its capability
 *     gate, next to `views/apps/exam-converter-public`.
 *   - Wrapped into the guest store by `examWorkspaceGuestStore.ts`, which
 *     checks the local cursor/revision before calling here.
 */

import {
  publicApiFetchBlobResponse,
  publicApiGet,
  publicApiPost,
  type ApiBlobResponse,
} from "./client";
import type {
  ExamCourseCatalogResponse,
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceExportChecklistResponse,
  ExamWorkspaceExportDownload,
  ExamWorkspaceExportTarget,
  ExamWorkspaceMisspellingsRequest,
  ExamWorkspaceMisspellingsResponse,
  NativeExamBodyParagraph,
  NativeExamDocument,
  NativeExamItemKind,
  NewParentChild,
} from "./examWorkspace";
import type { ExamParentDeleteMode } from "./examWorkspaceStructureCommands";

/** `/api/v1/public/apps/documents.conversion_hub/exam-converter/workspace`. */
const PUBLIC_WORKSPACE_ROOT =
  "/api/v1/public/apps/documents.conversion_hub/exam-converter/workspace";

/** The export gate's per-question/title verdict, taken straight from the public response. */
type PublicExportBlockers = ExamWorkspaceDocumentResponse["export_blockers"];

/** What a public command returns: the new document and the export gate's verdict on it. */
export type PublicExamWorkspaceCommandResult = {
  document: NativeExamDocument;
  export_blockers: PublicExportBlockers;
};

/** A public deletion, which may name the instruction it emptied. */
export type PublicExamWorkspaceDeleteResult = PublicExamWorkspaceCommandResult & {
  removed_parent_id: string | null;
};

/** A public part creation, which names the new part the UI opens. */
export type PublicExamWorkspaceCreatedPartResult = PublicExamWorkspaceCommandResult & {
  created_parent_id: string;
};

/** A public type change, which names the content the new type could not keep. */
export type PublicExamWorkspaceChangeTypeResult = PublicExamWorkspaceCommandResult & {
  dropped_content: string[];
};

export type CreatePublicExamParentRequest = {
  document: NativeExamDocument;
  instruction: NativeExamBodyParagraph[];
  child: NewParentChild;
  position: number;
};

export type AddPublicExamChildRequest = {
  document: NativeExamDocument;
  child: NewParentChild;
  position: number;
};

export type DeletePublicExamChildRequest = {
  document: NativeExamDocument;
};

export type ReorderPublicExamChildrenRequest = {
  document: NativeExamDocument;
  item_ids: string[];
};

export type DeletePublicExamParentRequest = {
  document: NativeExamDocument;
  mode: ExamParentDeleteMode;
};

export type ChangePublicExamWorkspaceItemTypeRequest = {
  document: NativeExamDocument;
  item_id: string;
  target_kind: NativeExamItemKind;
};

/** The saved copy plus the stored bytes of its declared pictures, keyed by asset id. */
export type PublicExamWorkspaceExportRequest = {
  document: NativeExamDocument;
  assets: Record<string, Blob>;
};

function parentsPath(parentId: string): string {
  return `${PUBLIC_WORKSPACE_ROOT}/parents/${encodeURIComponent(parentId)}`;
}

/** Build the multipart body: the document JSON plus one `asset:<id>` part per declared picture. */
function buildExportFormData(request: PublicExamWorkspaceExportRequest): FormData {
  const form = new FormData();
  form.append("document", JSON.stringify(request.document));
  for (const asset of request.document.assets) {
    const blob = request.assets[asset.asset_id];
    if (!blob) {
      throw new Error(
        `The export request is missing the picture bytes for asset ${asset.asset_id}.`,
      );
    }
    form.append(`asset:${asset.asset_id}`, blob);
  }
  return form;
}

export async function createPublicExamWorkspaceBlank(): Promise<PublicExamWorkspaceCommandResult> {
  return await publicApiPost<PublicExamWorkspaceCommandResult>(`${PUBLIC_WORKSPACE_ROOT}/blank`);
}

export async function createPublicExamWorkspaceParent(
  request: CreatePublicExamParentRequest,
): Promise<PublicExamWorkspaceCommandResult> {
  return await publicApiPost<PublicExamWorkspaceCommandResult>(
    `${PUBLIC_WORKSPACE_ROOT}/parents`,
    request,
  );
}

export async function addPublicExamWorkspaceChild(
  parentId: string,
  request: AddPublicExamChildRequest,
): Promise<PublicExamWorkspaceCommandResult> {
  return await publicApiPost<PublicExamWorkspaceCommandResult>(
    `${parentsPath(parentId)}/children`,
    request,
  );
}

export async function deletePublicExamWorkspaceChild(
  parentId: string,
  itemId: string,
  request: DeletePublicExamChildRequest,
): Promise<PublicExamWorkspaceDeleteResult> {
  return await publicApiPost<PublicExamWorkspaceDeleteResult>(
    `${parentsPath(parentId)}/children/${encodeURIComponent(itemId)}/delete`,
    request,
  );
}

export async function reorderPublicExamWorkspaceChildren(
  parentId: string,
  request: ReorderPublicExamChildrenRequest,
): Promise<PublicExamWorkspaceCommandResult> {
  return await publicApiPost<PublicExamWorkspaceCommandResult>(
    `${parentsPath(parentId)}/children/order`,
    request,
  );
}

export async function deletePublicExamWorkspaceParent(
  parentId: string,
  request: DeletePublicExamParentRequest,
): Promise<PublicExamWorkspaceDeleteResult> {
  return await publicApiPost<PublicExamWorkspaceDeleteResult>(
    `${parentsPath(parentId)}/delete`,
    request,
  );
}

/** Group marked standalone questions into one new part. */
export async function groupPublicExamWorkspaceItems(
  document: NativeExamDocument,
  itemIds: string[],
): Promise<PublicExamWorkspaceCreatedPartResult> {
  return await publicApiPost<PublicExamWorkspaceCreatedPartResult>(
    `${PUBLIC_WORKSPACE_ROOT}/parents/group`,
    { document, item_ids: itemIds },
  );
}

/** Insert a part with an empty instruction at the chosen top-level position. */
export async function createEmptyPublicExamWorkspacePart(
  document: NativeExamDocument,
  position: number,
): Promise<PublicExamWorkspaceCreatedPartResult> {
  return await publicApiPost<PublicExamWorkspaceCreatedPartResult>(
    `${PUBLIC_WORKSPACE_ROOT}/parents/empty`,
    { document, position },
  );
}

/** Move one question into a part, out to standalone, or between parts. */
export async function movePublicExamWorkspaceItem(
  document: NativeExamDocument,
  itemId: string,
  targetParentId: string | null,
): Promise<PublicExamWorkspaceCommandResult> {
  return await publicApiPost<PublicExamWorkspaceCommandResult>(
    `${PUBLIC_WORKSPACE_ROOT}/parents/move`,
    { document, item_id: itemId, target_parent_id: targetParentId },
  );
}

export async function changePublicExamWorkspaceItemType(
  request: ChangePublicExamWorkspaceItemTypeRequest,
): Promise<PublicExamWorkspaceChangeTypeResult> {
  return await publicApiPost<PublicExamWorkspaceChangeTypeResult>(
    `${PUBLIC_WORKSPACE_ROOT}/change-type`,
    request,
  );
}

export async function requestPublicExamWorkspaceAnswerMisspellings(
  request: ExamWorkspaceMisspellingsRequest,
): Promise<ExamWorkspaceMisspellingsResponse> {
  return await publicApiPost<ExamWorkspaceMisspellingsResponse>(
    `${PUBLIC_WORKSPACE_ROOT}/answer-misspellings`,
    request,
  );
}

export async function getPublicExamCourseCatalog(): Promise<ExamCourseCatalogResponse> {
  return await publicApiGet<ExamCourseCatalogResponse>(`${PUBLIC_WORKSPACE_ROOT}/courses`);
}

export async function downloadPublicExamWorkspaceExport(
  target: ExamWorkspaceExportTarget,
  request: PublicExamWorkspaceExportRequest,
): Promise<ExamWorkspaceExportDownload> {
  const response: ApiBlobResponse = await publicApiFetchBlobResponse(
    `${PUBLIC_WORKSPACE_ROOT}/exports/${encodeURIComponent(target)}`,
    { method: "POST", body: buildExportFormData(request) },
  );
  if (response.filename === null) {
    throw new Error("The export response carries no file name in Content-Disposition.");
  }
  return { ...response, filename: response.filename };
}

export async function getPublicExamWorkspaceExportChecklist(
  request: PublicExamWorkspaceExportRequest,
): Promise<ExamWorkspaceExportChecklistResponse> {
  return await publicApiPost<ExamWorkspaceExportChecklistResponse>(
    `${PUBLIC_WORKSPACE_ROOT}/export-checklist`,
    buildExportFormData(request),
  );
}
