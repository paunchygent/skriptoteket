/**
 * Exam workspace store seam.
 *
 * Domain purpose:
 *   One object that owns every server call the exam workspace makes. The
 *   signed-in workspace runs on `serverExamWorkspaceStore`, which delegates
 *   to `api/examWorkspace.ts` and `api/vault.ts`; a guest workspace runs on a
 *   browser store implementing the same halves. The shared half is what every
 *   mode can do; the teacher half holds the actions only a signed-in teacher
 *   has and is null in guest mode.
 *
 * Relationships:
 *   - Built from `api/examWorkspace.ts` and `api/vault.ts`; each member calls
 *     the imported module function at call time, so `vi.mock` of those modules
 *     still intercepts.
 *   - Provided by `ExamWorkspaceView` under `EXAM_WORKSPACE_STORE_KEY` and read
 *     by the composables and components that call it through
 *     `useInjectedExamWorkspaceStore`.
 */

import { inject, type InjectionKey } from "vue";

import {
  copyExamWorkspaceDocument,
  createExamWorkspaceBlank,
  examWorkspaceAssetUrl,
  findExamWorkspaceAnswerKeySuggestions,
  getExamCourseCatalog,
  getExamCourseContent,
  getExamWorkspaceAnswerKeySuggestions,
  getExamWorkspaceContentSuggestions,
  getExamWorkspaceConversionStatus,
  getExamWorkspaceDocument,
  getExamWorkspaceHistory,
  getExamWorkspaceHistoryStep,
  importExamWorkspaceDigiExam,
  importExamWorkspaceDocument,
  importExamWorkspaceGuestDraft,
  importExamWorkspaceQti,
  listExamWorkspaceDocuments,
  moveExamWorkspaceHistoryPosition,
  requestExamWorkspaceAnswerKeySuggestions,
  requestExamWorkspaceAnswerMisspellings,
  requestExamWorkspaceContentSuggestions,
  retryExamWorkspaceItem,
  storeExamWorkspaceUndoStep,
  updateExamListOrdering,
} from "../../../api/examWorkspace";
import {
  downloadExamWorkspaceExport,
  fetchExamWorkspacePrintPreview,
  getExamWorkspaceExportChecklist,
  saveExamWorkspaceExport,
} from "../../../api/examWorkspaceExports";
import {
  addExamWorkspaceChild,
  changeExamWorkspaceItemType,
  createEmptyExamWorkspacePart,
  createExamWorkspaceParent,
  deleteExamWorkspaceChild,
  deleteExamWorkspaceParent,
  groupExamWorkspaceItems,
  moveExamWorkspaceItem,
  reorderExamWorkspaceChildren,
} from "../../../api/examWorkspaceStructureCommands";
import { renameVaultFile } from "../../../api/vault";

/** What every exam workspace mode can do, guest included. */
export type ExamWorkspaceSharedStore = {
  getExamWorkspaceDocument: typeof getExamWorkspaceDocument;
  storeExamWorkspaceUndoStep: typeof storeExamWorkspaceUndoStep;
  moveExamWorkspaceHistoryPosition: typeof moveExamWorkspaceHistoryPosition;
  getExamWorkspaceHistory: typeof getExamWorkspaceHistory;
  getExamWorkspaceHistoryStep: typeof getExamWorkspaceHistoryStep;
  createExamWorkspaceParent: typeof createExamWorkspaceParent;
  addExamWorkspaceChild: typeof addExamWorkspaceChild;
  deleteExamWorkspaceChild: typeof deleteExamWorkspaceChild;
  reorderExamWorkspaceChildren: typeof reorderExamWorkspaceChildren;
  deleteExamWorkspaceParent: typeof deleteExamWorkspaceParent;
  groupExamWorkspaceItems: typeof groupExamWorkspaceItems;
  createEmptyExamWorkspacePart: typeof createEmptyExamWorkspacePart;
  moveExamWorkspaceItem: typeof moveExamWorkspaceItem;
  changeExamWorkspaceItemType: typeof changeExamWorkspaceItemType;
  downloadExamWorkspaceExport: typeof downloadExamWorkspaceExport;
  getExamWorkspaceExportChecklist: typeof getExamWorkspaceExportChecklist;
  requestExamWorkspaceAnswerMisspellings: typeof requestExamWorkspaceAnswerMisspellings;
  getExamCourseCatalog: typeof getExamCourseCatalog;
  examWorkspaceAssetUrl: typeof examWorkspaceAssetUrl;
};

/** The actions that need a signed-in teacher; null in guest mode. */
export type ExamWorkspaceTeacherServices = {
  createExamWorkspaceBlank: typeof createExamWorkspaceBlank;
  listExamWorkspaceDocuments: typeof listExamWorkspaceDocuments;
  importExamWorkspaceDocument: typeof importExamWorkspaceDocument;
  getExamWorkspaceConversionStatus: typeof getExamWorkspaceConversionStatus;
  importExamWorkspaceDigiExam: typeof importExamWorkspaceDigiExam;
  importExamWorkspaceQti: typeof importExamWorkspaceQti;
  copyExamWorkspaceDocument: typeof copyExamWorkspaceDocument;
  saveExamWorkspaceExport: typeof saveExamWorkspaceExport;
  retryExamWorkspaceItem: typeof retryExamWorkspaceItem;
  requestExamWorkspaceAnswerKeySuggestions: typeof requestExamWorkspaceAnswerKeySuggestions;
  getExamWorkspaceAnswerKeySuggestions: typeof getExamWorkspaceAnswerKeySuggestions;
  findExamWorkspaceAnswerKeySuggestions: typeof findExamWorkspaceAnswerKeySuggestions;
  requestExamWorkspaceContentSuggestions: typeof requestExamWorkspaceContentSuggestions;
  getExamWorkspaceContentSuggestions: typeof getExamWorkspaceContentSuggestions;
  getExamCourseContent: typeof getExamCourseContent;
  updateExamListOrdering: typeof updateExamListOrdering;
  renameVaultFile: typeof renameVaultFile;
  importExamWorkspaceGuestDraft: typeof importExamWorkspaceGuestDraft;
  fetchExamWorkspacePrintPreview: typeof fetchExamWorkspacePrintPreview;
};

/**
 * The authority a guest slot replacement writes under: the tab whose edit
 * lease the write checks, and whether the requesting operation still holds
 * live replacement authority. `isLive` is evaluated inside the atomic slot
 * write, so a retired operation never replaces the retained draft.
 */
export type GuestSlotAdmission = {
  tabId: string;
  isLive: () => boolean;
};

/** The guest-only actions on the shared exam workspace; null in signed-in mode. */
export type ExamWorkspaceGuestServices = {
  startBlank(expectedCursor: string | null, admission: GuestSlotAdmission): Promise<string>;
  startFromQti(file: File, courseKey: string | null): Promise<string>;
};

export type ExamWorkspaceStore = {
  shared: ExamWorkspaceSharedStore;
  teacher: ExamWorkspaceTeacherServices | null;
  guest: ExamWorkspaceGuestServices | null;
};

/** The signed-in workspace's store: a thin delegation to the transport modules. */
export const serverExamWorkspaceStore: ExamWorkspaceStore = {
  shared: {
    getExamWorkspaceDocument: (...args) => getExamWorkspaceDocument(...args),
    storeExamWorkspaceUndoStep: (...args) => storeExamWorkspaceUndoStep(...args),
    moveExamWorkspaceHistoryPosition: (...args) => moveExamWorkspaceHistoryPosition(...args),
    getExamWorkspaceHistory: (...args) => getExamWorkspaceHistory(...args),
    getExamWorkspaceHistoryStep: (...args) => getExamWorkspaceHistoryStep(...args),
    createExamWorkspaceParent: (...args) => createExamWorkspaceParent(...args),
    addExamWorkspaceChild: (...args) => addExamWorkspaceChild(...args),
    deleteExamWorkspaceChild: (...args) => deleteExamWorkspaceChild(...args),
    reorderExamWorkspaceChildren: (...args) => reorderExamWorkspaceChildren(...args),
    deleteExamWorkspaceParent: (...args) => deleteExamWorkspaceParent(...args),
    groupExamWorkspaceItems: (...args) => groupExamWorkspaceItems(...args),
    createEmptyExamWorkspacePart: (...args) => createEmptyExamWorkspacePart(...args),
    moveExamWorkspaceItem: (...args) => moveExamWorkspaceItem(...args),
    changeExamWorkspaceItemType: (...args) => changeExamWorkspaceItemType(...args),
    downloadExamWorkspaceExport: (...args) => downloadExamWorkspaceExport(...args),
    getExamWorkspaceExportChecklist: (...args) => getExamWorkspaceExportChecklist(...args),
    requestExamWorkspaceAnswerMisspellings: (...args) =>
      requestExamWorkspaceAnswerMisspellings(...args),
    getExamCourseCatalog: (...args) => getExamCourseCatalog(...args),
    examWorkspaceAssetUrl: (...args) => examWorkspaceAssetUrl(...args),
  },
  teacher: {
    createExamWorkspaceBlank: (...args) => createExamWorkspaceBlank(...args),
    listExamWorkspaceDocuments: (...args) => listExamWorkspaceDocuments(...args),
    importExamWorkspaceDocument: (...args) => importExamWorkspaceDocument(...args),
    getExamWorkspaceConversionStatus: (...args) => getExamWorkspaceConversionStatus(...args),
    importExamWorkspaceDigiExam: (...args) => importExamWorkspaceDigiExam(...args),
    importExamWorkspaceQti: (...args) => importExamWorkspaceQti(...args),
    copyExamWorkspaceDocument: (...args) => copyExamWorkspaceDocument(...args),
    saveExamWorkspaceExport: (...args) => saveExamWorkspaceExport(...args),
    retryExamWorkspaceItem: (...args) => retryExamWorkspaceItem(...args),
    requestExamWorkspaceAnswerKeySuggestions: (...args) =>
      requestExamWorkspaceAnswerKeySuggestions(...args),
    getExamWorkspaceAnswerKeySuggestions: (...args) =>
      getExamWorkspaceAnswerKeySuggestions(...args),
    findExamWorkspaceAnswerKeySuggestions: (...args) =>
      findExamWorkspaceAnswerKeySuggestions(...args),
    requestExamWorkspaceContentSuggestions: (...args) =>
      requestExamWorkspaceContentSuggestions(...args),
    getExamWorkspaceContentSuggestions: (...args) => getExamWorkspaceContentSuggestions(...args),
    getExamCourseContent: (...args) => getExamCourseContent(...args),
    updateExamListOrdering: (...args) => updateExamListOrdering(...args),
    renameVaultFile: (...args) => renameVaultFile(...args),
    importExamWorkspaceGuestDraft: (...args) => importExamWorkspaceGuestDraft(...args),
    fetchExamWorkspacePrintPreview: (...args) => fetchExamWorkspacePrintPreview(...args),
  },
  guest: null,
};

export const EXAM_WORKSPACE_STORE_KEY: InjectionKey<ExamWorkspaceStore> =
  Symbol("exam-workspace-store");

/** The store the surrounding `ExamWorkspaceView` provided; required, never defaulted. */
export function useInjectedExamWorkspaceStore(): ExamWorkspaceStore {
  const store = inject(EXAM_WORKSPACE_STORE_KEY);
  if (!store) {
    throw new Error("ExamWorkspaceStore was not provided by an ExamWorkspaceView ancestor.");
  }
  return store;
}
