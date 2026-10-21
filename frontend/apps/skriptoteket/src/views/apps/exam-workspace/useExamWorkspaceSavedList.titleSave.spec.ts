/**
 * Prov list follows a title save (TASK-SKRIPT-40-04-21, W3).
 *
 * Expected behavior:
 *   A signed-in teacher renames the exam title and the save succeeds; the
 *   Prov list entry for that exam shows the new title at once, with no
 *   reload. The step store answers with the saved document but no summary,
 *   so the confirmed store carries the saved title onto the open summary and
 *   its list entry. The renamed file name arrives with the next list load.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  exam,
  LINEAGE,
  openEditing,
  stopScopes,
  type EditingApiMocks,
} from "./useExamWorkspaceEditing.history.specSupport";

const api: EditingApiMocks = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));
vi.mock("../../../composables/useAiAccess", () => ({ useAiAccess: () => ({ canUseAi: { value: true } }) }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(stopScopes);

function listTitle(editing: Awaited<ReturnType<typeof openEditing>>["editing"]): string | undefined {
  return editing.savedDocuments.value.find((entry) => entry.lineage_id === LINEAGE)?.title;
}

describe("Prov list after a title save (W3)", () => {
  it("shows the renamed title at once, with no reload", async () => {
    const { editing } = await openEditing(api);
    expect(listTitle(editing)).toBe("Original");

    editing.setTitle("Vattnets kretslopp: prov 1");
    expect(await editing.history.flush()).toBe(true);
    expect(listTitle(editing)).toBe("Vattnets kretslopp: prov 1");
    expect(editing.summary.value?.title).toBe("Vattnets kretslopp: prov 1");
    expect(api.getExamWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("shows the new title for an exam renamed from an empty title", async () => {
    const { editing } = await openEditing(api, exam(""));
    expect(listTitle(editing)).toBe("");

    editing.setTitle("Vattnets kretslopp: prov 1");
    expect(await editing.history.flush()).toBe(true);
    expect(listTitle(editing)).toBe("Vattnets kretslopp: prov 1");
    expect(api.getExamWorkspaceDocument).not.toHaveBeenCalled();
  });
});
