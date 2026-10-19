/**
 * Exam workspace item edit commands: typing cadence and structural steps.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 Q2):
 *   Gap accepted answers and dropdown option text travel the typing path:
 *   they are stored as one undo step after the 900 ms typing pause, and the
 *   step holds the typed value. A structural option edit and adding a
 *   criterion travel the structural path: each is stored at once as its own
 *   step. Criterion text edits stay on the typing path.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NativeExamChoice, NativeExamItem } from "../../../api/examWorkspace";
import { buildGapItem } from "./ExamWorkspaceBodyEditor.specSupport";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { plainBody } from "./examWorkspaceRichText";
import {
  exam,
  openEditing,
  stopScopes,
  type EditingApiMocks,
} from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  requestExamWorkspaceAnswerMisspellings: vi.fn(),
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
  api.requestExamWorkspaceAnswerMisspellings.mockResolvedValue({ automatic_values: [] });
  vi.useFakeTimers();
});

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
});

async function elapse(ms: number): Promise<void> {
  await vi.advanceTimersByTimeAsync(ms);
  await flushPromises();
}

function dropdownItem(): NativeExamItem {
  const options: NativeExamChoice[] = [
    { body: plainBody("zebra"), choice_id: "choice_003" },
    { body: plainBody("apa"), choice_id: "choice_001" },
    { body: plainBody("groda"), choice_id: "choice_005" },
  ];
  return {
    ...buildGapItem(),
    body: [
      {
        heading_level: null,
        segments: [
          { kind: "text", marks: [], text: "Välj " },
          { gap_id: "gap_009", kind: "gap" },
          { kind: "text", marks: [], text: "." },
        ],
      },
    ],
    gaps: [buildGap("gap_009", [], { correct_option_id: "choice_001", options })],
    item_id: "item_002",
    kind: "inline_choice",
    sequence: 2,
  };
}

function baseline() {
  const document = exam("Original", 3);
  document.items[0] = buildGapItem();
  document.items[1] = dropdownItem();
  return document;
}

function storedDocument(server: { documents: Map<string, unknown>; state: { steps: string[] } }) {
  const stepId = server.state.steps.at(-1);
  if (!stepId) {
    throw new Error("expected a stored step");
  }
  return server.documents.get(stepId) as {
    items: NativeExamItem[];
  };
}

describe("useExamWorkspaceItemEdits history cadence", () => {
  it("stores typed gap answers as one step after the pause", async () => {
    const { editing, server } = await openEditing(api as unknown as EditingApiMocks, baseline());

    editing.updateItemGapValues("item_001", "gap_001", ["100a"]);
    // The typing pause has not passed: a microtask drain alone stores nothing.
    await flushPromises();
    expect(server.state.steps).toHaveLength(0);

    await elapse(1000);

    expect(server.state.steps).toHaveLength(1);
    expect(
      storedDocument(server).items.find((item) => item.item_id === "item_001")?.gaps,
    ).toEqual([expect.objectContaining({ accepted_values: ["100a"] }), expect.anything()]);
    expect(editing.history.pending.value).toBe(false);
  });

  it("stores typed option text as one step after the pause", async () => {
    const { editing, server } = await openEditing(api as unknown as EditingApiMocks, baseline());
    const before = editing.workspaceDocument.value?.items.find(
      (item) => item.item_id === "item_002",
    );
    const options = (before?.gaps.find((gap) => gap.gap_id === "gap_009")?.options ?? []).map(
      (option) =>
        option.choice_id === "choice_005"
          ? { ...option, body: plainBody("gorilla") }
          : option,
    );

    editing.updateItemGapOptions("item_002", "gap_009", options, "choice_001", false);
    // The typing pause has not passed: a microtask drain alone stores nothing.
    await flushPromises();
    expect(server.state.steps).toHaveLength(0);

    await elapse(1000);

    expect(server.state.steps).toHaveLength(1);
    const stored = storedDocument(server)
      .items.find((item) => item.item_id === "item_002")
      ?.gaps.find((gap) => gap.gap_id === "gap_009");
    expect(stored?.options.find((option) => option.choice_id === "choice_005")?.body).toEqual(
      plainBody("gorilla"),
    );
    expect(editing.history.pending.value).toBe(false);
  });

  it("stores a structural option edit at once", async () => {
    const { editing, server } = await openEditing(api as unknown as EditingApiMocks, baseline());
    const before = editing.workspaceDocument.value?.items.find(
      (item) => item.item_id === "item_002",
    );
    const options = before?.gaps.find((gap) => gap.gap_id === "gap_009")?.options ?? [];

    editing.updateItemGapOptions("item_002", "gap_009", options, "choice_005", true);
    await flushPromises();

    expect(server.state.steps).toHaveLength(1);
    expect(
      storedDocument(server)
        .items.find((item) => item.item_id === "item_002")
        ?.gaps.find((gap) => gap.gap_id === "gap_009")?.correct_option_id,
    ).toBe("choice_005");
    expect(editing.history.pending.value).toBe(false);
  });

  it("stores adding a criterion at once as its own step", async () => {
    const { editing, server } = await openEditing(api as unknown as EditingApiMocks, baseline());

    editing.updateItemCriteria("item_003", [{ points: 2, text: "Nämner orsaken" }], true);
    await flushPromises();

    expect(server.state.steps).toHaveLength(1);
    const stored = storedDocument(server).items.find((item) => item.item_id === "item_003");
    expect(stored?.criteria).toEqual([{ points: 2, text: "Nämner orsaken" }]);
    expect(stored?.points).toBe(2);
    expect(editing.history.pending.value).toBe(false);
  });

  it("stores a criterion text edit after the pause", async () => {
    const { editing, server } = await openEditing(api as unknown as EditingApiMocks, baseline());

    editing.updateItemCriteria("item_003", [{ points: 2, text: "Nämner orsaken" }], false);
    // The typing pause has not passed: a microtask drain alone stores nothing.
    await flushPromises();
    expect(server.state.steps).toHaveLength(0);

    await elapse(1000);

    expect(server.state.steps).toHaveLength(1);
    expect(
      storedDocument(server).items.find((item) => item.item_id === "item_003")?.criteria,
    ).toEqual([{ points: 2, text: "Nämner orsaken" }]);
    expect(editing.history.pending.value).toBe(false);
  });
});
