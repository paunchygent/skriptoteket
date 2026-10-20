/**
 * Exam workspace fenced transport (TASK-SKRIPT-40-04-14, F2).
 *
 * Domain purpose:
 *   One fenced call per sync write: every store, move and structure command
 *   settles through the gate's fence, so an answer retired by a newer
 *   generation resolves `stale` at once and never touches state. The editing
 *   session builds one transport over the shared store; the history store,
 *   the navigation moves and the structure commands receive it instead of
 *   the shared calls, so code written against those deps has no unfenced
 *   store, move or command call to make. Reads and the out-of-scope calls
 *   (enrichment, suggestions, exports, print preview, rename, the saved list
 *   and the course catalog) stay on the shared store.
 */

import type { ExamWorkspaceSharedStore } from "./examWorkspaceStore";
import type { FenceToken, Settled, SyncFence } from "./examWorkspaceSyncFence";

type Shared = ExamWorkspaceSharedStore;

export type ExamWorkspaceFencedTransport = {
  storeUndoStep: (
    token: FenceToken,
    ...args: Parameters<Shared["storeExamWorkspaceUndoStep"]>
  ) => Promise<Settled<Awaited<ReturnType<Shared["storeExamWorkspaceUndoStep"]>>>>;
  movePosition: (
    token: FenceToken,
    ...args: Parameters<Shared["moveExamWorkspaceHistoryPosition"]>
  ) => Promise<Settled<Awaited<ReturnType<Shared["moveExamWorkspaceHistoryPosition"]>>>>;
  createParent: (
    token: FenceToken,
    ...args: Parameters<Shared["createExamWorkspaceParent"]>
  ) => Promise<Settled<Awaited<ReturnType<Shared["createExamWorkspaceParent"]>>>>;
  addChild: (
    token: FenceToken,
    ...args: Parameters<Shared["addExamWorkspaceChild"]>
  ) => Promise<Settled<Awaited<ReturnType<Shared["addExamWorkspaceChild"]>>>>;
  deleteChild: (
    token: FenceToken,
    ...args: Parameters<Shared["deleteExamWorkspaceChild"]>
  ) => Promise<Settled<Awaited<ReturnType<Shared["deleteExamWorkspaceChild"]>>>>;
  reorderChildren: (
    token: FenceToken,
    ...args: Parameters<Shared["reorderExamWorkspaceChildren"]>
  ) => Promise<Settled<Awaited<ReturnType<Shared["reorderExamWorkspaceChildren"]>>>>;
  deleteParent: (
    token: FenceToken,
    ...args: Parameters<Shared["deleteExamWorkspaceParent"]>
  ) => Promise<Settled<Awaited<ReturnType<Shared["deleteExamWorkspaceParent"]>>>>;
  groupItems: (
    token: FenceToken,
    ...args: Parameters<Shared["groupExamWorkspaceItems"]>
  ) => Promise<Settled<Awaited<ReturnType<Shared["groupExamWorkspaceItems"]>>>>;
  createEmptyPart: (
    token: FenceToken,
    ...args: Parameters<Shared["createEmptyExamWorkspacePart"]>
  ) => Promise<Settled<Awaited<ReturnType<Shared["createEmptyExamWorkspacePart"]>>>>;
  moveItem: (
    token: FenceToken,
    ...args: Parameters<Shared["moveExamWorkspaceItem"]>
  ) => Promise<Settled<Awaited<ReturnType<Shared["moveExamWorkspaceItem"]>>>>;
  changeItemType: (
    token: FenceToken,
    ...args: Parameters<Shared["changeExamWorkspaceItemType"]>
  ) => Promise<Settled<Awaited<ReturnType<Shared["changeExamWorkspaceItemType"]>>>>;
};

export function createFencedTransport(
  getFence: () => SyncFence,
  shared: Shared,
): ExamWorkspaceFencedTransport {
  return {
    addChild: (token, ...args) => getFence().settle(token, shared.addExamWorkspaceChild(...args)),
    changeItemType: (token, ...args) =>
      getFence().settle(token, shared.changeExamWorkspaceItemType(...args)),
    createEmptyPart: (token, ...args) =>
      getFence().settle(token, shared.createEmptyExamWorkspacePart(...args)),
    createParent: (token, ...args) =>
      getFence().settle(token, shared.createExamWorkspaceParent(...args)),
    deleteChild: (token, ...args) =>
      getFence().settle(token, shared.deleteExamWorkspaceChild(...args)),
    deleteParent: (token, ...args) =>
      getFence().settle(token, shared.deleteExamWorkspaceParent(...args)),
    groupItems: (token, ...args) => getFence().settle(token, shared.groupExamWorkspaceItems(...args)),
    moveItem: (token, ...args) => getFence().settle(token, shared.moveExamWorkspaceItem(...args)),
    movePosition: (token, ...args) =>
      getFence().settle(token, shared.moveExamWorkspaceHistoryPosition(...args)),
    reorderChildren: (token, ...args) =>
      getFence().settle(token, shared.reorderExamWorkspaceChildren(...args)),
    storeUndoStep: (token, ...args) =>
      getFence().settle(token, shared.storeExamWorkspaceUndoStep(...args)),
  };
}
