/**
 * Guest exam workspace store.
 *
 * Domain purpose:
 *   The one exam a guest edits without signing in lives only in this browser:
 *   the draft, its bounded undo history and its picture bytes stay in local
 *   storage, and this store runs the same `ExamWorkspaceStore` interface the
 *   signed-in workspace runs. Teacher services are null, so the shared editor
 *   shows the sign-in prompts for Word/DigiExam import and AI instead of
 *   calling. The parts that need the exam domain (structure commands,
 *   misspellings, exports, checklist, catalog) call the stateless public
 *   routes, which take the whole document in the request.
 *
 * Relationships:
 *   - Built on `examWorkspaceGuestDraft.ts` (draft and history state machine)
 *     and `examWorkspaceGuestDraftStorage.ts` (its browser storage).
 *   - Calls the stateless public routes through `api/publicExamWorkspace.ts`;
 *     the API object is injected so specs supply a fake.
 *   - Provides `ExamWorkspaceStore` under the same seam as
 *     `serverExamWorkspaceStore`, so a guest view installs this one.
 */

import { ApiError, isApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import {
  guestDocumentResponse,
  guestHistory,
  guestHistoryStep,
  newGuestDraft,
  saveGuestDraft,
  storeGuestUndoStep,
  type ExamWorkspaceGuestDraft,
  type ExamWorkspaceGuestDraftIdSource,
} from "./examWorkspaceGuestDraft";
import type {
  ExamWorkspaceGuestDraftStoragePort,
  StoredGuestDraft,
} from "./examWorkspaceGuestDraftStorage";
import type { ExamWorkspaceSharedStore, ExamWorkspaceStore } from "./examWorkspaceStore";

const CONFLICT_MESSAGE = "Dokumentet har ändrats sedan det öppnades.";
const NOT_FOUND_MESSAGE = "Provdokumentet finns inte.";

/** The server's cursor/revision conflict (`ExamWorkspaceParentsHandler._apply`). */
function conflictError(): ApiError {
  return new ApiError({ code: "CONFLICT", message: CONFLICT_MESSAGE, status: 409 });
}

/** The server's refusal of a document the save rules reject; carries the Swedish copy. */
function refusalError(copy: string): ApiError {
  return new ApiError({ code: "VALIDATION_ERROR", message: copy, status: 422 });
}

/** The server's document-not-found (`_document_not_found`), for an unknown guest lineage. */
function notFoundError(lineageId: string): ApiError {
  return new ApiError({
    code: "NOT_FOUND",
    message: NOT_FOUND_MESSAGE,
    status: 404,
    details: { lineage_id: lineageId },
  });
}

/** The public routes' hourly guest limit arrives as a plain 429. */
export function isGuestLimitError(error: unknown): boolean {
  return isApiError(error) && error.status === 429;
}

/** The pictures a retained snapshot or the saved copy still declares. */
function declaredAssetIds(draft: ExamWorkspaceGuestDraft): Set<string> {
  const ids = new Set<string>();
  for (const step of [draft.baseline, ...draft.steps]) {
    for (const asset of step.document.assets) {
      ids.add(asset.asset_id);
    }
  }
  for (const asset of draft.saved_document.assets) {
    ids.add(asset.asset_id);
  }
  return ids;
}

/** Keep only the stored picture bytes whose id a retained snapshot or the saved copy declares. */
function retainDeclaredAssets(
  stored: StoredGuestDraft,
  draft: ExamWorkspaceGuestDraft,
): Record<string, Blob> {
  const declared = declaredAssetIds(draft);
  const kept: Record<string, Blob> = {};
  for (const [assetId, blob] of Object.entries(stored.assets)) {
    if (declared.has(assetId)) {
      kept[assetId] = blob;
    }
  }
  return kept;
}

type PublicCommandResult = {
  document: NativeExamDocument;
  export_blockers: ExamWorkspaceDocumentResponse["export_blockers"];
};

export type ExamWorkspaceGuestStoreDeps = {
  storage: ExamWorkspaceGuestDraftStoragePort;
  api: typeof import("../../../api/publicExamWorkspace");
  ids: ExamWorkspaceGuestDraftIdSource;
  /** Called once per failing public call whose rejection is the guest limit. */
  onLimit: () => void;
};

export type ExamWorkspaceGuestStore = {
  store: ExamWorkspaceStore;
  /** The lineage of the stored draft, or null when the guest has none. */
  currentLineageId(): Promise<string | null>;
  /** Start a fresh blank exam through the public route and store it. */
  startBlank(): Promise<string>;
  /** Drop the browser draft and every picture byte it kept. */
  clear(): Promise<void>;
};

export function createGuestExamWorkspaceStore(
  deps: ExamWorkspaceGuestStoreDeps,
): ExamWorkspaceGuestStore {
  /**
   * Every public call goes through this wrapper once so a 429 from the hourly
   * guest limiter reports `onLimit` before the same error reaches the caller.
   */
  function guardLimit<TArgs extends unknown[], TResult>(
    call: (...args: TArgs) => Promise<TResult>,
  ): (...args: TArgs) => Promise<TResult> {
    return async (...args: TArgs): Promise<TResult> => {
      try {
        return await call(...args);
      } catch (error: unknown) {
        if (isGuestLimitError(error)) {
          deps.onLimit();
        }
        throw error;
      }
    };
  }

  const api: ExamWorkspaceGuestStoreDeps["api"] = {
    createPublicExamWorkspaceBlank: guardLimit((...args) =>
      deps.api.createPublicExamWorkspaceBlank(...args),
    ),
    createPublicExamWorkspaceParent: guardLimit((...args) =>
      deps.api.createPublicExamWorkspaceParent(...args),
    ),
    addPublicExamWorkspaceChild: guardLimit((...args) =>
      deps.api.addPublicExamWorkspaceChild(...args),
    ),
    deletePublicExamWorkspaceChild: guardLimit((...args) =>
      deps.api.deletePublicExamWorkspaceChild(...args),
    ),
    reorderPublicExamWorkspaceChildren: guardLimit((...args) =>
      deps.api.reorderPublicExamWorkspaceChildren(...args),
    ),
    deletePublicExamWorkspaceParent: guardLimit((...args) =>
      deps.api.deletePublicExamWorkspaceParent(...args),
    ),
    groupPublicExamWorkspaceItems: guardLimit((...args) =>
      deps.api.groupPublicExamWorkspaceItems(...args),
    ),
    createEmptyPublicExamWorkspacePart: guardLimit((...args) =>
      deps.api.createEmptyPublicExamWorkspacePart(...args),
    ),
    movePublicExamWorkspaceItem: guardLimit((...args) =>
      deps.api.movePublicExamWorkspaceItem(...args),
    ),
    changePublicExamWorkspaceItemType: guardLimit((...args) =>
      deps.api.changePublicExamWorkspaceItemType(...args),
    ),
    requestPublicExamWorkspaceAnswerMisspellings: guardLimit((...args) =>
      deps.api.requestPublicExamWorkspaceAnswerMisspellings(...args),
    ),
    getPublicExamCourseCatalog: guardLimit((...args) => deps.api.getPublicExamCourseCatalog(...args)),
    downloadPublicExamWorkspaceExport: guardLimit((...args) =>
      deps.api.downloadPublicExamWorkspaceExport(...args),
    ),
    getPublicExamWorkspaceExportChecklist: guardLimit((...args) =>
      deps.api.getPublicExamWorkspaceExportChecklist(...args),
    ),
  };

  /** The draft whose picture bytes currently have object URLs. */
  let openLineageId: string | null = null;
  const assetUrls = new Map<string, string>();

  function revokeAssetUrls(): void {
    for (const url of assetUrls.values()) {
      URL.revokeObjectURL(url);
    }
    assetUrls.clear();
  }

  /** Point the object-URL map at `stored`'s picture bytes, keeping unchanged ones stable. */
  function mountAssets(stored: StoredGuestDraft): void {
    if (openLineageId !== stored.draft.lineage_id) {
      revokeAssetUrls();
    }
    const declared = new Set(Object.keys(stored.assets));
    for (const [assetId, url] of [...assetUrls]) {
      if (!declared.has(assetId)) {
        URL.revokeObjectURL(url);
        assetUrls.delete(assetId);
      }
    }
    for (const [assetId, blob] of Object.entries(stored.assets)) {
      if (!assetUrls.has(assetId)) {
        assetUrls.set(assetId, URL.createObjectURL(blob));
      }
    }
    openLineageId = stored.draft.lineage_id;
  }

  async function loadStored(lineageId: string): Promise<StoredGuestDraft> {
    const stored = await deps.storage.load();
    if (!stored || stored.draft.lineage_id !== lineageId) {
      throw notFoundError(lineageId);
    }
    return stored;
  }

  async function persist(stored: StoredGuestDraft): Promise<void> {
    await deps.storage.save(stored);
    mountAssets(stored);
  }

  /**
   * Run one server command against the editor's document. The cursor (and, for
   * a type change, the revision) is checked against the draft exactly as the
   * server checks it, a mismatch is a 409, and the returned document becomes
   * one new undo step after the current position, as the server's commands do.
   */
  async function commitCommand<Result extends PublicCommandResult>(
    lineageId: string,
    guard: (draft: ExamWorkspaceGuestDraft) => boolean,
    run: (document: NativeExamDocument) => Promise<Result>,
  ): Promise<{ result: Result; draft: ExamWorkspaceGuestDraft }> {
    const stored = await loadStored(lineageId);
    if (!guard(stored.draft)) {
      throw conflictError();
    }
    const current = guestDocumentResponse(stored.draft).document;
    const result = await run(current);
    const outcome = storeGuestUndoStep(
      stored.draft,
      { afterStepId: null, document: result.document, expectedCursor: stored.draft.cursor },
      deps.ids,
    );
    if (outcome.kind === "conflict") {
      throw conflictError();
    }
    if (outcome.kind === "refused") {
      throw refusalError(outcome.copy);
    }
    await persist({ assets: retainDeclaredAssets(stored, outcome.draft), draft: outcome.draft });
    return { draft: outcome.draft, result };
  }

  const shared: ExamWorkspaceSharedStore = {
    async getExamWorkspaceDocument(lineageId) {
      const stored = await loadStored(lineageId);
      mountAssets(stored);
      return guestDocumentResponse(stored.draft);
    },
    async saveExamWorkspaceDocument(lineageId, params) {
      const stored = await loadStored(lineageId);
      const outcome = saveGuestDraft(
        stored.draft,
        {
          document: params.document,
          expectedRevision: params.expectedRevision,
          positionStepId: params.positionStepId,
        },
        deps.ids,
      );
      if (outcome.kind === "conflict") {
        throw conflictError();
      }
      if (outcome.kind === "refused") {
        throw refusalError(outcome.copy);
      }
      await persist({ assets: retainDeclaredAssets(stored, outcome.draft), draft: outcome.draft });
      return outcome.response;
    },
    async storeExamWorkspaceUndoStep(lineageId, params) {
      const stored = await loadStored(lineageId);
      const outcome = storeGuestUndoStep(
        stored.draft,
        {
          afterStepId: params.afterStepId,
          document: params.document,
          expectedCursor: params.expectedCursor,
        },
        deps.ids,
      );
      if (outcome.kind === "conflict") {
        throw conflictError();
      }
      if (outcome.kind === "refused") {
        throw refusalError(outcome.copy);
      }
      await persist({ assets: retainDeclaredAssets(stored, outcome.draft), draft: outcome.draft });
      return outcome.step;
    },
    async getExamWorkspaceHistory(lineageId) {
      const stored = await loadStored(lineageId);
      return guestHistory(stored.draft);
    },
    async getExamWorkspaceHistoryStep(lineageId, stepId) {
      const stored = await loadStored(lineageId);
      const outcome = guestHistoryStep(stored.draft, stepId);
      if (outcome.kind === "not_found") {
        throw notFoundError(lineageId);
      }
      return outcome.step;
    },
    async createExamWorkspaceParent(lineageId, body) {
      const { draft, result } = await commitCommand(
        lineageId,
        (current) => current.cursor === body.expected_cursor,
        (document) =>
          api.createPublicExamWorkspaceParent({
            child: body.child,
            document,
            instruction: body.instruction,
            position: body.position,
          }),
      );
      return { ...guestDocumentResponse(draft), export_blockers: result.export_blockers };
    },
    async addExamWorkspaceChild(lineageId, parentId, body) {
      const { draft, result } = await commitCommand(
        lineageId,
        (current) => current.cursor === body.expected_cursor,
        (document) =>
          api.addPublicExamWorkspaceChild(parentId, {
            child: body.child,
            document,
            position: body.position,
          }),
      );
      return { ...guestDocumentResponse(draft), export_blockers: result.export_blockers };
    },
    async deleteExamWorkspaceChild(lineageId, parentId, itemId, expectedCursor) {
      const { draft, result } = await commitCommand(
        lineageId,
        (current) => current.cursor === expectedCursor,
        (document) => api.deletePublicExamWorkspaceChild(parentId, itemId, { document }),
      );
      return {
        ...guestDocumentResponse(draft),
        export_blockers: result.export_blockers,
        removed_parent_id: result.removed_parent_id,
      };
    },
    async reorderExamWorkspaceChildren(lineageId, parentId, itemIds, expectedCursor) {
      const { draft, result } = await commitCommand(
        lineageId,
        (current) => current.cursor === expectedCursor,
        (document) =>
          api.reorderPublicExamWorkspaceChildren(parentId, {
            document,
            item_ids: itemIds,
          }),
      );
      return { ...guestDocumentResponse(draft), export_blockers: result.export_blockers };
    },
    async deleteExamWorkspaceParent(lineageId, parentId, mode, expectedCursor) {
      const { draft, result } = await commitCommand(
        lineageId,
        (current) => current.cursor === expectedCursor,
        (document) => api.deletePublicExamWorkspaceParent(parentId, { document, mode }),
      );
      return {
        ...guestDocumentResponse(draft),
        export_blockers: result.export_blockers,
        removed_parent_id: result.removed_parent_id,
      };
    },
    async groupExamWorkspaceItems(lineageId, itemIds, expectedCursor) {
      const { draft, result } = await commitCommand(
        lineageId,
        (current) => current.cursor === expectedCursor,
        (document) => api.groupPublicExamWorkspaceItems(document, itemIds),
      );
      return {
        ...guestDocumentResponse(draft),
        created_parent_id: result.created_parent_id,
        export_blockers: result.export_blockers,
      };
    },
    async createEmptyExamWorkspacePart(lineageId, position, expectedCursor) {
      const { draft, result } = await commitCommand(
        lineageId,
        (current) => current.cursor === expectedCursor,
        (document) => api.createEmptyPublicExamWorkspacePart(document, position),
      );
      return {
        ...guestDocumentResponse(draft),
        created_parent_id: result.created_parent_id,
        export_blockers: result.export_blockers,
      };
    },
    async moveExamWorkspaceItem(lineageId, itemId, targetParentId, expectedCursor) {
      const { draft, result } = await commitCommand(
        lineageId,
        (current) => current.cursor === expectedCursor,
        (document) => api.movePublicExamWorkspaceItem(document, itemId, targetParentId),
      );
      return { ...guestDocumentResponse(draft), export_blockers: result.export_blockers };
    },
    async changeExamWorkspaceItemType(lineageId, body) {
      const { draft, result } = await commitCommand(
        lineageId,
        (current) =>
          current.cursor === body.expected_cursor &&
          current.saved_document.revision === body.expected_revision,
        (document) =>
          api.changePublicExamWorkspaceItemType({
            document,
            item_id: body.item_id,
            target_kind: body.target_kind,
          }),
      );
      return {
        ...guestDocumentResponse(draft),
        dropped_content: result.dropped_content,
        export_blockers: result.export_blockers,
      };
    },
    async downloadExamWorkspaceExport(lineageId, target, expectedRevision) {
      const stored = await loadStored(lineageId);
      if (stored.draft.saved_document.revision !== expectedRevision) {
        throw conflictError();
      }
      return await api.downloadPublicExamWorkspaceExport(target, {
        assets: stored.assets,
        document: stored.draft.saved_document,
      });
    },
    async getExamWorkspaceExportChecklist(lineageId, expectedRevision) {
      const stored = await loadStored(lineageId);
      if (stored.draft.saved_document.revision !== expectedRevision) {
        throw conflictError();
      }
      return await api.getPublicExamWorkspaceExportChecklist({
        assets: stored.assets,
        document: stored.draft.saved_document,
      });
    },
    async requestExamWorkspaceAnswerMisspellings(request) {
      return await api.requestPublicExamWorkspaceAnswerMisspellings(request);
    },
    async getExamCourseCatalog() {
      return await api.getPublicExamCourseCatalog();
    },
    examWorkspaceAssetUrl(lineageId, assetId) {
      if (openLineageId !== lineageId) {
        return "";
      }
      return assetUrls.get(assetId) ?? "";
    },
  };

  async function startBlank(): Promise<string> {
    const response = await api.createPublicExamWorkspaceBlank();
    const draft = newGuestDraft(response.document, deps.ids);
    await persist({ assets: {}, draft });
    return draft.lineage_id;
  }

  return {
    store: { shared, teacher: null, guest: { startBlank } },
    async currentLineageId() {
      const stored = await deps.storage.load();
      return stored?.draft.lineage_id ?? null;
    },
    startBlank,
    async clear() {
      await deps.storage.clear();
      openLineageId = null;
      revokeAssetUrls();
    },
  };
}
