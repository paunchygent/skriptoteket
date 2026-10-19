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
 *   - The conditional-persistence and command commit machinery lives in
 *     `examWorkspaceGuestStoreCommit.ts`, the server-shaped refusals in
 *     `examWorkspaceGuestStoreErrors.ts`, and the limit-reporting API wrapper
 *     in `examWorkspaceGuestLimitApi.ts`.
 *   - Provides `ExamWorkspaceStore` under the same seam as
 *     `serverExamWorkspaceStore`, so a guest view installs this one.
 */

import type { ExamWorkspaceUndoStep, NativeExamDocument } from "../../../api/examWorkspace";
import {
  guestDocumentResponse,
  guestHistory,
  guestHistoryStep,
  moveGuestHistoryPosition,
  newGuestDraft,
  storeGuestUndoStep,
  type ExamWorkspaceGuestDraftIdSource,
} from "./examWorkspaceGuestDraft";
import type {
  ExamWorkspaceGuestDraftStoragePort,
  StoredGuestDraft,
} from "./examWorkspaceGuestDraftStorage";
import {
  commitGuestCommand,
  loadGuestStored,
  persistGuestStored,
  retainDeclaredAssets,
} from "./examWorkspaceGuestStoreCommit";
import { conflictError, notFoundError, refusalError } from "./examWorkspaceGuestStoreErrors";
import type { GuestPublicApi } from "./examWorkspaceGuestLimitApi";
import { wrapGuestPublicApiForLimit } from "./examWorkspaceGuestLimitApi";
import type { ExamWorkspaceSharedStore, ExamWorkspaceStore } from "./examWorkspaceStore";

export { isGuestLimitError } from "./examWorkspaceGuestStoreErrors";

export type ExamWorkspaceGuestStoreDeps = {
  storage: ExamWorkspaceGuestDraftStoragePort;
  api: GuestPublicApi;
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
  /** Start a guest exam from a QTI .zip through the public parse route. */
  startFromQti(file: File, courseKey: string | null): Promise<string>;
  /**
   * Move the draft to a retained history step (guest Ångra and Gör om): the
   * position and the saved draft follow the step, and no new step is
   * stored. The guest counterpart of the server's history position move
   * (unit K45 wires the server path and the header).
   */
  moveToHistoryStep(
    lineageId: string,
    params: { expectedCursor: string; stepId: string },
  ): Promise<ExamWorkspaceUndoStep>;
  /** Drop the browser draft and every picture byte it kept. */
  clear(): Promise<void>;
};

export function createGuestExamWorkspaceStore(
  deps: ExamWorkspaceGuestStoreDeps,
): ExamWorkspaceGuestStore {
  const api = wrapGuestPublicApiForLimit(deps.api, deps.onLimit);

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

  async function persist(expectedCursor: string | null, stored: StoredGuestDraft): Promise<void> {
    await persistGuestStored(deps.storage, expectedCursor, stored, mountAssets);
  }

  async function loadStored(lineageId: string): Promise<StoredGuestDraft> {
    return await loadGuestStored(deps.storage, lineageId);
  }

  const shared: ExamWorkspaceSharedStore = {
    async getExamWorkspaceDocument(lineageId) {
      const stored = await loadStored(lineageId);
      mountAssets(stored);
      return guestDocumentResponse(stored.draft);
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
      await persist(stored.draft.cursor, {
        assets: retainDeclaredAssets(stored, outcome.draft),
        draft: outcome.draft,
      });
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
    /**
     * Move the draft to a retained history step (guest Ångra and Gör om):
     * the position and the saved draft follow the step, and no new step is
     * stored. Only the cursor guard commits, so a concurrent tab's newer
     * draft reports the conflict instead.
     */
    async moveExamWorkspaceHistoryPosition(lineageId, params) {
      const stored = await loadStored(lineageId);
      const outcome = moveGuestHistoryPosition(stored.draft, params, deps.ids);
      if (outcome.kind === "conflict") {
        throw conflictError();
      }
      if (outcome.kind === "not_found") {
        throw notFoundError(lineageId);
      }
      if (outcome.kind === "refused") {
        throw refusalError(outcome.copy);
      }
      await persist(stored.draft.cursor, {
        assets: retainDeclaredAssets(stored, outcome.draft),
        draft: outcome.draft,
      });
      return outcome.step;
    },
    async createExamWorkspaceParent(lineageId, body) {
      const { draft, result } = await commitGuestCommand({
        guard: (current) => current.cursor === body.expected_cursor,
        ids: deps.ids,
        lineageId,
        onStored: mountAssets,
        run: (document: NativeExamDocument) =>
          api.createPublicExamWorkspaceParent({
            child: body.child,
            document,
            instruction: body.instruction,
            position: body.position,
          }),
        storage: deps.storage,
      });
      return { ...guestDocumentResponse(draft), export_blockers: result.export_blockers };
    },
    async addExamWorkspaceChild(lineageId, parentId, body) {
      const { draft, result } = await commitGuestCommand({
        guard: (current) => current.cursor === body.expected_cursor,
        ids: deps.ids,
        lineageId,
        onStored: mountAssets,
        run: (document: NativeExamDocument) =>
          api.addPublicExamWorkspaceChild(parentId, {
            child: body.child,
            document,
            position: body.position,
          }),
        storage: deps.storage,
      });
      return { ...guestDocumentResponse(draft), export_blockers: result.export_blockers };
    },
    async deleteExamWorkspaceChild(lineageId, parentId, itemId, expectedCursor) {
      const { draft, result } = await commitGuestCommand({
        guard: (current) => current.cursor === expectedCursor,
        ids: deps.ids,
        lineageId,
        onStored: mountAssets,
        run: (document: NativeExamDocument) =>
          api.deletePublicExamWorkspaceChild(parentId, itemId, { document }),
        storage: deps.storage,
      });
      return {
        ...guestDocumentResponse(draft),
        export_blockers: result.export_blockers,
        removed_parent_id: result.removed_parent_id,
      };
    },
    async reorderExamWorkspaceChildren(lineageId, parentId, itemIds, expectedCursor) {
      const { draft, result } = await commitGuestCommand({
        guard: (current) => current.cursor === expectedCursor,
        ids: deps.ids,
        lineageId,
        onStored: mountAssets,
        run: (document: NativeExamDocument) =>
          api.reorderPublicExamWorkspaceChildren(parentId, {
            document,
            item_ids: itemIds,
          }),
        storage: deps.storage,
      });
      return { ...guestDocumentResponse(draft), export_blockers: result.export_blockers };
    },
    async deleteExamWorkspaceParent(lineageId, parentId, mode, expectedCursor) {
      const { draft, result } = await commitGuestCommand({
        guard: (current) => current.cursor === expectedCursor,
        ids: deps.ids,
        lineageId,
        onStored: mountAssets,
        run: (document: NativeExamDocument) =>
          api.deletePublicExamWorkspaceParent(parentId, { document, mode }),
        storage: deps.storage,
      });
      return {
        ...guestDocumentResponse(draft),
        export_blockers: result.export_blockers,
        removed_parent_id: result.removed_parent_id,
      };
    },
    async groupExamWorkspaceItems(lineageId, itemIds, expectedCursor) {
      const { draft, result } = await commitGuestCommand({
        guard: (current) => current.cursor === expectedCursor,
        ids: deps.ids,
        lineageId,
        onStored: mountAssets,
        run: (document: NativeExamDocument) => api.groupPublicExamWorkspaceItems(document, itemIds),
        storage: deps.storage,
      });
      return {
        ...guestDocumentResponse(draft),
        created_parent_id: result.created_parent_id,
        export_blockers: result.export_blockers,
      };
    },
    async createEmptyExamWorkspacePart(lineageId, position, expectedCursor) {
      const { draft, result } = await commitGuestCommand({
        guard: (current) => current.cursor === expectedCursor,
        ids: deps.ids,
        lineageId,
        onStored: mountAssets,
        run: (document: NativeExamDocument) =>
          api.createEmptyPublicExamWorkspacePart(document, position),
        storage: deps.storage,
      });
      return {
        ...guestDocumentResponse(draft),
        created_parent_id: result.created_parent_id,
        export_blockers: result.export_blockers,
      };
    },
    async moveExamWorkspaceItem(lineageId, itemId, targetParentId, expectedCursor) {
      const { draft, result } = await commitGuestCommand({
        guard: (current) => current.cursor === expectedCursor,
        ids: deps.ids,
        lineageId,
        onStored: mountAssets,
        run: (document: NativeExamDocument) =>
          api.movePublicExamWorkspaceItem(document, itemId, targetParentId),
        storage: deps.storage,
      });
      return { ...guestDocumentResponse(draft), export_blockers: result.export_blockers };
    },
    async changeExamWorkspaceItemType(lineageId, body) {
      const { draft, result } = await commitGuestCommand({
        guard: (current) =>
          current.cursor === body.expected_cursor &&
          current.saved_document.revision === body.expected_revision,
        ids: deps.ids,
        lineageId,
        onStored: mountAssets,
        run: (document: NativeExamDocument) =>
          api.changePublicExamWorkspaceItemType({
            document,
            item_id: body.item_id,
            target_kind: body.target_kind,
          }),
        storage: deps.storage,
      });
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

  /**
   * Replace the whole browser slot with the draft `produce` builds. The slot
   * cursor is captured before awaiting `produce`, so a concurrent tab that
   * commits while the public route is in flight owns the slot afterwards and
   * this write reports the established 409 instead of overwriting its draft.
   */
  async function replaceSlotWith(produce: () => Promise<StoredGuestDraft>): Promise<string> {
    const current = await deps.storage.load();
    const expectedCursor = current?.draft.cursor ?? null;
    const next = await produce();
    await persist(expectedCursor, next);
    return next.draft.lineage_id;
  }

  /**
   * Start a fresh blank exam through the public route and store it. A
   * concurrent tab's newer draft is kept and reported as the conflict.
   */
  async function startBlank(): Promise<string> {
    return await replaceSlotWith(async () => {
      const response = await api.createPublicExamWorkspaceBlank();
      const draft = newGuestDraft(response.document, deps.ids, []);
      return { assets: {}, draft };
    });
  }

  /**
   * Start a guest exam from a QTI .zip through the public parse route: the
   * returned document becomes the draft and its picture bytes stay beside
   * it in the browser. A concurrent tab's newer draft is kept, like a lost
   * blank start, and a limit hit reports through `onLimit`.
   */
  async function startFromQti(file: File, courseKey: string | null): Promise<string> {
    return await replaceSlotWith(async () => {
      const response = await api.importPublicExamWorkspaceQti(file, courseKey);
      const draft = newGuestDraft(response.document, deps.ids, response.notes);
      return { assets: response.assets, draft };
    });
  }

  return {
    store: { shared, teacher: null, guest: { startBlank, startFromQti } },
    async currentLineageId() {
      const stored = await deps.storage.load();
      return stored?.draft.lineage_id ?? null;
    },
    startBlank,
    startFromQti,
    /**
     * Move the draft to a retained history step (guest Ångra and Gör om): the
     * same move the shared store runs, exposed here for the guest history
     * wiring (unit K8). The guest counterpart of the server's history
     * position move (unit K45 wires the server path and the header).
     */
    async moveToHistoryStep(lineageId, params) {
      return await shared.moveExamWorkspaceHistoryPosition(lineageId, params);
    },
    /**
     * Drop the browser draft. The write commits only when the loaded snapshot
     * still owns the slot; a concurrent tab's newer draft reports the
     * conflict instead of being deleted by this reset.
     */
    async clear() {
      const current = await deps.storage.load();
      if (current !== null) {
        const cleared = await deps.storage.clearIf(current.draft.cursor);
        if (!cleared) {
          throw conflictError();
        }
      }
      openLineageId = null;
      revokeAssetUrls();
    },
  };
}
