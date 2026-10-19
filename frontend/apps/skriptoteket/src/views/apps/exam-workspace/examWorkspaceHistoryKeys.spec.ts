/**
 * Exam workspace history keys: the provided Ångra and Gör om availability.
 *
 * Domain purpose:
 *   The question toolbar session places its own Ångra and Gör om pair, so
 *   the workspace provides the pair's availability next to the pair itself
 *   (TASK-SKRIPT-40-04-14 K1, D6): `canUndo` and `canRedo` are the same
 *   availability the top-bar pair disables on, so the toolbar pair can
 *   later disable on it without computing a second one.
 *
 * Relationships:
 *   - `ExamWorkspaceView` provides the keys from its workspace history;
 *     every exam text editor injects the pair for its undo and redo
 *     shortcuts, and the future question toolbar pair reads the
 *     availability.
 *
 * Transport is the named double of the server's step store from
 * `useExamWorkspaceEditing.history.specSupport`; the history is the
 * production `useExamWorkspaceEditing` session.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";

import { provideExamWorkspaceHistoryKeys, useExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import type { ExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import { openEditing, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../api/examWorkspaceStructureCommands", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspaceStructureCommands")>()),
  changeExamWorkspaceItemType: api.changeExamWorkspaceItemType,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(stopScopes);

const mounted: VueWrapper[] = [];

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  document.body.innerHTML = "";
});

/**
 * Mount a provider and a probe as the workspace wires them: the provider
 * hands the history's pair down, the probe reads the keys back. Mirrors
 * `ExamWorkspaceView`'s `provideExamWorkspaceHistoryKeys` call.
 */
async function mountKeys(
  editing: Awaited<ReturnType<typeof openEditing>>["editing"],
): Promise<ExamWorkspaceHistoryKeys> {
  let seen: ExamWorkspaceHistoryKeys | null = null;
  // eslint-disable-next-line vue/one-component-per-file
  const Probe = defineComponent({
    setup() {
      seen = useExamWorkspaceHistoryKeys();
      return () => h("div");
    },
  });
  // eslint-disable-next-line vue/one-component-per-file
  const Host = defineComponent({
    setup() {
      provideExamWorkspaceHistoryKeys({
        undo: () => void editing.history.undo(),
        redo: () => void editing.history.redo(),
        canUndo: editing.history.canUndo,
        canRedo: editing.history.canRedo,
      });
      return () => h(Probe);
    },
  });
  mounted.push(mount(Host, { attachTo: document.body }));
  await flushPromises();
  if (!seen) {
    throw new Error("the probe did not read the history keys");
  }
  return seen;
}

describe("examWorkspaceHistoryKeys availability (K1)", () => {
  it("starts with nothing to undo or redo at the baseline", async () => {
    const { editing } = await openEditing(api);
    const keys = await mountKeys(editing);

    expect(keys.canUndo).toBe(editing.history.canUndo);
    expect(keys.canRedo).toBe(editing.history.canRedo);
    expect(keys.canUndo.value).toBe(false);
    expect(keys.canRedo.value).toBe(false);
  });

  it("follows the history: undo after a stored step, redo after an undo", async () => {
    const { editing } = await openEditing(api);
    const keys = await mountKeys(editing);

    editing.setTitle("Lärarens rubrik");
    await editing.history.flush();
    expect(keys.canUndo.value).toBe(true);
    expect(keys.canRedo.value).toBe(false);

    keys.undo();
    await flushPromises();
    expect(editing.workspaceDocument.value!.title).toBe("Original");
    expect(keys.canUndo.value).toBe(false);
    expect(keys.canRedo.value).toBe(true);

    keys.redo();
    await flushPromises();
    expect(editing.workspaceDocument.value!.title).toBe("Lärarens rubrik");
    expect(keys.canUndo.value).toBe(true);
    expect(keys.canRedo.value).toBe(false);
  });
});
