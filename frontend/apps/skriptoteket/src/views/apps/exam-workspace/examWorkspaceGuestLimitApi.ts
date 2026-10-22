/**
 * Guest exam workspace limit-reporting public API wrapper.
 *
 * Domain purpose:
 *   Every public call the guest store makes goes through this wrapper once,
 *   so a 429 from the hourly guest limiter reports `onLimit` before the same
 *   error reaches the caller and the view shows the sign-in prompt.
 *
 * Relationships:
 *   - Wraps the stateless public routes of `api/publicExamWorkspace.ts`;
 *     the 429 predicate comes from `examWorkspaceGuestStoreErrors.ts`.
 *   - Consumed by `examWorkspaceGuestStore.ts`, which injects the raw API so
 *     specs supply a fake; no storage or draft knowledge here.
 */

import { isGuestLimitError } from "./examWorkspaceGuestStoreErrors";

/** The stateless public routes the guest store calls; specs supply a fake. */
export type GuestPublicApi = typeof import("../../../api/publicExamWorkspace");

/**
 * Wrap every public call once so a rejection that is the guest limit reports
 * `onLimit` first; the original error still reaches the caller unchanged.
 */
export function wrapGuestPublicApiForLimit(
  raw: GuestPublicApi,
  onLimit: () => void,
): GuestPublicApi {
  function guardLimit<TArgs extends unknown[], TResult>(
    call: (...args: TArgs) => Promise<TResult>,
  ): (...args: TArgs) => Promise<TResult> {
    return async (...args: TArgs): Promise<TResult> => {
      try {
        return await call(...args);
      } catch (error: unknown) {
        if (isGuestLimitError(error)) {
          onLimit();
        }
        throw error;
      }
    };
  }

  return {
    createPublicExamWorkspaceBlank: guardLimit((...args) =>
      raw.createPublicExamWorkspaceBlank(...args),
    ),
    createPublicExamWorkspaceParent: guardLimit((...args) =>
      raw.createPublicExamWorkspaceParent(...args),
    ),
    addPublicExamWorkspaceChild: guardLimit((...args) =>
      raw.addPublicExamWorkspaceChild(...args),
    ),
    deletePublicExamWorkspaceChild: guardLimit((...args) =>
      raw.deletePublicExamWorkspaceChild(...args),
    ),
    reorderPublicExamWorkspaceChildren: guardLimit((...args) =>
      raw.reorderPublicExamWorkspaceChildren(...args),
    ),
    deletePublicExamWorkspaceParent: guardLimit((...args) =>
      raw.deletePublicExamWorkspaceParent(...args),
    ),
    groupPublicExamWorkspaceItems: guardLimit((...args) =>
      raw.groupPublicExamWorkspaceItems(...args),
    ),
    createEmptyPublicExamWorkspacePart: guardLimit((...args) =>
      raw.createEmptyPublicExamWorkspacePart(...args),
    ),
    movePublicExamWorkspaceItem: guardLimit((...args) =>
      raw.movePublicExamWorkspaceItem(...args),
    ),
    changePublicExamWorkspaceItemType: guardLimit((...args) =>
      raw.changePublicExamWorkspaceItemType(...args),
    ),
    requestPublicExamWorkspaceAnswerMisspellings: guardLimit((...args) =>
      raw.requestPublicExamWorkspaceAnswerMisspellings(...args),
    ),
    getPublicExamCourseCatalog: guardLimit((...args) => raw.getPublicExamCourseCatalog(...args)),
    getExamWorkspaceLimits: guardLimit((...args) => raw.getExamWorkspaceLimits(...args)),
    downloadPublicExamWorkspaceExport: guardLimit((...args) =>
      raw.downloadPublicExamWorkspaceExport(...args),
    ),
    getPublicExamWorkspaceExportChecklist: guardLimit((...args) =>
      raw.getPublicExamWorkspaceExportChecklist(...args),
    ),
    importPublicExamWorkspaceQti: guardLimit((...args) =>
      raw.importPublicExamWorkspaceQti(...args),
    ),
  };
}
