/**
 * R9 intent-side fail-first spec: same-question conflict (TASK-SKRIPT-40-04-14,
 * ledger L14, design section 5 "Unknown-result lifetime").
 *
 * Row 3: this tab edits two fields of question q1 (points and body text) and
 * keeps the edit while its store is held; the other tab legitimately changes a
 * third field of q1 (writing lines) and q2, then releases. After recovery q1
 * is this tab's whole question (the other tab's field change is gone — no
 * field-by-field question merge), and the untouched q2 stays newest.
 *
 * Drives the production editing session; doubles cover only transport, clock,
 * lease responses and server persistence. The seam the design will change is
 * the kept merge-base selection: the merge input must be explicit per-question
 * ownership instead of the whole-document base comparison.
 */

import { afterEach, beforeEach, expect, it, vi } from "vitest";

import type {
  NativeExamDocument,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { nullRouteProjection } from "./examWorkspaceRouteProjection.specSupport";
import {
  exam,
  fakeServer,
  inScope,
  response,
  stopScopes,
  type EditingApiMocks,
} from "./useExamWorkspaceEditing.history.specSupport";
import { deferred } from "./useExamWorkspaceSyncGate.specSupport";
import {
  intentLeaseDouble,
  intentLeaseState,
  loseIntentLease,
  pointsOf,
  reacquireIntentLease,
  remoteIntentWrite,
  resetIntentMocks,
  settleIntent,
} from "./useExamWorkspaceEditing.R9Intent.specSupport";

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

function questionOf(document: NativeExamDocument | null, itemId: string): NativeExamItem {
  if (document === null) {
    throw new Error("expected an open document");
  }
  const found = document.items.find((item) => item.item_id === itemId);
  if (found === undefined) {
    throw new Error(`expected ${itemId}`);
  }
  return found;
}

function bodyTextOf(item: NativeExamItem): string {
  const paragraph = item.body[0];
  if (paragraph === undefined) {
    throw new Error("expected a body paragraph");
  }
  const segment = paragraph.segments[0];
  if (segment === undefined || segment.kind !== "text") {
    throw new Error("expected a text segment");
  }
  return segment.text;
}

beforeEach(() => {
  vi.useFakeTimers();
  resetIntentMocks(api);
  for (const mock of Object.values(toast)) {
    mock.mockReset();
  }
});

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
});

it("R9Intent row 3: an owned question wins whole over the other tab's field change", async () => {
  const baseline = exam();
  const server = fakeServer(api, baseline);
  const state = intentLeaseState();
  const editing = inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), {
      server: intentLeaseDouble(state),
      tabId: "A",
    }),
  );
  editing.applyCommandResponse(response(baseline, "step-0"));
  await settleIntent();
  const ownedLines = questionOf(editing.workspaceDocument.value, "item_001").writing_lines;

  // Two fields of q1, kept while the store is held (committed, unacknowledged).
  const persist = api.storeExamWorkspaceUndoStep.getMockImplementation();
  if (persist === undefined) {
    throw new Error("expected the step store double");
  }
  const ack = deferred<unknown>();
  let stored: unknown = null;
  api.storeExamWorkspaceUndoStep.mockImplementationOnce((lineageId: string, request: unknown) => {
    const saving = persist(lineageId, request);
    stored = saving;
    return ack.promise;
  });
  editing.updateItemPoints("item_001", 7);
  editing.updateItemBody(
    "item_001",
    [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "A text" }] }],
    false,
  );
  const saving = editing.save();
  await settleIntent();

  // The other tab legitimately changes q1's third field and q2, then releases.
  await loseIntentLease(editing, state);
  state.holder = "B";
  remoteIntentWrite(server, "step-B", (document) => ({
    ...document,
    items: document.items.map((item) => {
      if (item.item_id === "item_001") {
        return { ...item, writing_lines: 9 };
      }
      if (item.item_id === "item_002") {
        return { ...item, points: 9 };
      }
      return item;
    }),
  }));
  ack.resolve(stored);
  await saving;
  await settleIntent();
  await reacquireIntentLease(editing, state);

  await editing.save();
  await settleIntent();
  const visible = editing.workspaceDocument.value;
  const persisted = server.documents.get(server.state.position) ?? null;
  // This tab's whole q1 wins: the other tab's writing-lines change is gone.
  expect({
    q1Body: bodyTextOf(questionOf(visible, "item_001")),
    q1Lines: questionOf(visible, "item_001").writing_lines,
    q1PersistedBody: bodyTextOf(questionOf(persisted, "item_001")),
    q1PersistedLines: questionOf(persisted, "item_001").writing_lines,
    status: editing.history.saveStatus.value.state,
    visible: pointsOf(visible),
    persisted: pointsOf(persisted),
  }).toEqual({
    q1Body: "A text",
    q1Lines: ownedLines,
    q1PersistedBody: "A text",
    q1PersistedLines: ownedLines,
    status: "saved",
    visible: [7, 9],
    persisted: [7, 9],
  });
});
