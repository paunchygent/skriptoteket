/**
 * Exam workspace editing session: AI suggestions that arrive while a
 * replacing read runs (TASK-SKRIPT-40-04-03 review 2, R2-F3).
 *
 * Expected behavior:
 *   - An AI suggestion that arrives while undo, redo or a server command
 *     (Byt frågetyp) replaces the copy is written again onto the document
 *     the read installs, so a delivered suggestion is never overwritten.
 *   - A spelling reply that arrives during an undo is written onto the
 *     installed step when that step still holds the gap's keyed values.
 *
 * Transport is a named double of the server's step store; the composables
 * are the production ones.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { newTeacherItem } from "./examWorkspaceItemEdits";
import { gapItem, keyedSuggestion } from "./examWorkspaceKeyedItems.specSupport";
import type { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { exam, openEditing, response, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  requestExamWorkspaceAnswerMisspellings: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
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

describe("AI arrivals during a replacing read (R2-F3)", () => {
  const arriving = keyedSuggestion({});

  function deliver(editing: ReturnType<typeof useExamWorkspaceEditing>, itemId: string): void {
    editing.applyArrivingSuggestions(editing.openExam.value!, [{ item_id: itemId, suggestion: arriving }]);
  }

  it("a suggestion delivered while undo reads a step is kept on the step it installs", async () => {
    const { editing, server } = await openEditing(api);
    editing.setTitle("Steg ett");
    await editing.history.flush();
    let release!: () => void;
    api.moveExamWorkspaceHistoryPosition.mockImplementationOnce(
      (_l: string, request: { expectedCursor: string; stepId: string }) =>
        new Promise((resolve) => {
          release = () =>
            resolve({
              document: server.documents.get(request.stepId)!,
              export_blockers: [],
              history: {
                baseline_step_id: "step-0",
                cursor: server.state.cursor,
                position_step_id: request.stepId,
                step_ids: [...server.state.steps],
              },
            });
        }),
    );

    const moving = editing.history.undo();
    await flushPromises();
    expect(editing.isBusy.value).toBe(true);
    deliver(editing, "item_001");
    release();
    await moving;

    expect(editing.workspaceDocument.value!.title).toBe("Original");
    expect(editing.workspaceDocument.value!.items[0]!.ai_suggestion).toEqual(arriving);
  });

  it("a suggestion delivered while redo reads a step is kept on the step it installs", async () => {
    const { editing, server } = await openEditing(api);
    editing.setTitle("Steg ett");
    await editing.history.flush();
    await editing.history.undo();
    let release!: () => void;
    api.moveExamWorkspaceHistoryPosition.mockImplementationOnce(
      (_l: string, request: { expectedCursor: string; stepId: string }) =>
        new Promise((resolve) => {
          release = () =>
            resolve({
              document: server.documents.get(request.stepId)!,
              export_blockers: [],
              history: {
                baseline_step_id: "step-0",
                cursor: server.state.cursor,
                position_step_id: request.stepId,
                step_ids: [...server.state.steps],
              },
            });
        }),
    );

    const moving = editing.history.redo();
    await flushPromises();
    deliver(editing, "item_002");
    release();
    await moving;

    expect(editing.workspaceDocument.value!.title).toBe("Steg ett");
    expect(editing.workspaceDocument.value!.items[1]!.ai_suggestion).toEqual(arriving);
  });

  it("a suggestion delivered while Byt frågetyp runs is kept on the command's document", async () => {
    const { editing } = await openEditing(api);
    let release!: () => void;
    api.changeExamWorkspaceItemType.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          const changed = exam();
          changed.items[0] = { ...newTeacherItem("item_001", 1, "single_choice"), points: 2 };
          release = () => resolve({ ...response(changed, "command-1"), dropped_content: [] });
        }),
    );

    const changing = editing.structure.changeType("item_001", "single_choice");
    await flushPromises();
    expect(editing.isBusy.value).toBe(true);
    deliver(editing, "item_002");
    release();
    await changing;

    expect(editing.workspaceDocument.value!.items[0]!.kind).toBe("single_choice");
    expect(editing.workspaceDocument.value!.items[1]!.ai_suggestion).toEqual(arriving);
  });
});

describe("spelling replies during a replacing read (R2-F3)", () => {
  it("a misspelling reply that arrives while undo reads a step is written onto the step it installs", async () => {
    const baseline = exam();
    baseline.items[0] = { ...gapItem("teacher_authored", [["gap_001", ["Stockholm"]]], null), points: 2 };
    const { editing, server } = await openEditing(api, baseline);
    let reply!: (automatic: string[]) => void;
    api.requestExamWorkspaceAnswerMisspellings.mockReturnValueOnce(
      new Promise((resolve) => {
        reply = (automatic) => resolve({ automatic_values: automatic });
      }),
    );
    editing.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);
    await editing.history.flush();
    editing.setTitle("Steg två");
    await editing.history.flush();
    let release!: () => void;
    api.moveExamWorkspaceHistoryPosition.mockImplementationOnce(
      (_l: string, request: { expectedCursor: string; stepId: string }) =>
        new Promise((resolve) => {
          release = () =>
            resolve({
              document: server.documents.get(request.stepId)!,
              export_blockers: [],
              history: {
                baseline_step_id: "step-0",
                cursor: server.state.cursor,
                position_step_id: request.stepId,
                step_ids: [...server.state.steps],
              },
            });
        }),
    );

    const moving = editing.history.undo();
    await flushPromises();
    expect(editing.isBusy.value).toBe(true);
    reply(["Götebprg"]);
    await flushPromises();
    release();
    await moving;

    const installed = editing.workspaceDocument.value!;
    expect(installed.title).toBe("Original");
    expect(installed.items[0]!.gaps[0]!.accepted_values).toEqual(["Stockholm", "Göteborg"]);
    expect(installed.items[0]!.gaps[0]!.automatic_values).toEqual(["Götebprg"]);
  });
});
