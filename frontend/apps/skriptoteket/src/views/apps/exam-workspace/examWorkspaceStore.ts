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
  addExamWorkspaceChild,
  changeExamWorkspaceItemType,
  copyExamWorkspaceDocument,
  createExamWorkspaceParent,
  deleteExamWorkspaceChild,
  deleteExamWorkspaceParent,
  downloadExamWorkspaceExport,
  examWorkspaceAssetUrl,
  findExamWorkspaceAnswerKeySuggestions,
  getExamCourseCatalog,
  getExamCourseContent,
  getExamWorkspaceAnswerKeySuggestions,
  getExamWorkspaceContentSuggestions,
  getExamWorkspaceConversionStatus,
  getExamWorkspaceDocument,
  getExamWorkspaceExportChecklist,
  getExamWorkspaceHistory,
  getExamWorkspaceHistoryStep,
  importExamWorkspaceDigiExam,
  importExamWorkspaceDocument,
  listExamWorkspaceDocuments,
  reorderExamWorkspaceChildren,
  requestExamWorkspaceAnswerKeySuggestions,
  requestExamWorkspaceAnswerMisspellings,
  requestExamWorkspaceContentSuggestions,
  retryExamWorkspaceItem,
  saveExamWorkspaceDocument,
  saveExamWorkspaceExport,
  storeExamWorkspaceUndoStep,
  updateExamListOrdering,
} from "../../../api/examWorkspace";
import { renameVaultFile } from "../../../api/vault";

/** What every exam workspace mode can do, guest included. */
export type ExamWorkspaceSharedStore = {
  getExamWorkspaceDocument: typeof getExamWorkspaceDocument;
  saveExamWorkspaceDocument: typeof saveExamWorkspaceDocument;
  storeExamWorkspaceUndoStep: typeof storeExamWorkspaceUndoStep;
  getExamWorkspaceHistory: typeof getExamWorkspaceHistory;
  getExamWorkspaceHistoryStep: typeof getExamWorkspaceHistoryStep;
  createExamWorkspaceParent: typeof createExamWorkspaceParent;
  addExamWorkspaceChild: typeof addExamWorkspaceChild;
  deleteExamWorkspaceChild: typeof deleteExamWorkspaceChild;
  reorderExamWorkspaceChildren: typeof reorderExamWorkspaceChildren;
  deleteExamWorkspaceParent: typeof deleteExamWorkspaceParent;
  changeExamWorkspaceItemType: typeof changeExamWorkspaceItemType;
  downloadExamWorkspaceExport: typeof downloadExamWorkspaceExport;
  getExamWorkspaceExportChecklist: typeof getExamWorkspaceExportChecklist;
  requestExamWorkspaceAnswerMisspellings: typeof requestExamWorkspaceAnswerMisspellings;
  getExamCourseCatalog: typeof getExamCourseCatalog;
  examWorkspaceAssetUrl: typeof examWorkspaceAssetUrl;
};

/** The actions that need a signed-in teacher; null in guest mode. */
export type ExamWorkspaceTeacherServices = {
  listExamWorkspaceDocuments: typeof listExamWorkspaceDocuments;
  importExamWorkspaceDocument: typeof importExamWorkspaceDocument;
  getExamWorkspaceConversionStatus: typeof getExamWorkspaceConversionStatus;
  importExamWorkspaceDigiExam: typeof importExamWorkspaceDigiExam;
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
};

export type ExamWorkspaceStore = {
  shared: ExamWorkspaceSharedStore;
  teacher: ExamWorkspaceTeacherServices | null;
};

/** The signed-in workspace's store: a thin delegation to the transport modules. */
export const serverExamWorkspaceStore: ExamWorkspaceStore = {
  shared: {
    getExamWorkspaceDocument: (...args) => getExamWorkspaceDocument(...args),
    saveExamWorkspaceDocument: (...args) => saveExamWorkspaceDocument(...args),
    storeExamWorkspaceUndoStep: (...args) => storeExamWorkspaceUndoStep(...args),
    getExamWorkspaceHistory: (...args) => getExamWorkspaceHistory(...args),
    getExamWorkspaceHistoryStep: (...args) => getExamWorkspaceHistoryStep(...args),
    createExamWorkspaceParent: (...args) => createExamWorkspaceParent(...args),
    addExamWorkspaceChild: (...args) => addExamWorkspaceChild(...args),
    deleteExamWorkspaceChild: (...args) => deleteExamWorkspaceChild(...args),
    reorderExamWorkspaceChildren: (...args) => reorderExamWorkspaceChildren(...args),
    deleteExamWorkspaceParent: (...args) => deleteExamWorkspaceParent(...args),
    changeExamWorkspaceItemType: (...args) => changeExamWorkspaceItemType(...args),
    downloadExamWorkspaceExport: (...args) => downloadExamWorkspaceExport(...args),
    getExamWorkspaceExportChecklist: (...args) => getExamWorkspaceExportChecklist(...args),
    requestExamWorkspaceAnswerMisspellings: (...args) =>
      requestExamWorkspaceAnswerMisspellings(...args),
    getExamCourseCatalog: (...args) => getExamCourseCatalog(...args),
    examWorkspaceAssetUrl: (...args) => examWorkspaceAssetUrl(...args),
  },
  teacher: {
    listExamWorkspaceDocuments: (...args) => listExamWorkspaceDocuments(...args),
    importExamWorkspaceDocument: (...args) => importExamWorkspaceDocument(...args),
    getExamWorkspaceConversionStatus: (...args) => getExamWorkspaceConversionStatus(...args),
    importExamWorkspaceDigiExam: (...args) => importExamWorkspaceDigiExam(...args),
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
  },
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
