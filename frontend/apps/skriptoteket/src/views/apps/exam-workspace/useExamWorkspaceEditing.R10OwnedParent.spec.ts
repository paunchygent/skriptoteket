/**
 * R10-2 fail-first: recovery restores a missing part only when this tab
 * owns it (TASK-SKRIPT-40-04-14, rereview 10 R10-2).
 *
 * This tab owns only the title while its store is held; the other tab then
 * legitimately deletes the part with keep-questions semantics once this
 * tab's lease has expired, and releases. After recovery the title edit is
 * stored but the deleted instruction stays deleted, through the
 * production editing session, gate, history and merger with the
 * cursor-aware fake step store. Ported from the reviewer's
 * intent-neighbours probe, same scenario, name and assertions.
 */

import { afterEach, beforeEach, expect, it, vi } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
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
  reacquireIntentLease,
  remoteIntentWrite,
  resetIntentMocks,
  settleIntent,
  type IntentServer,
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

function baseWithParent(): NativeExamDocument {
  return {
    ...exam(),
    parents: [
      {
        instruction: [
          {
            heading_level: null,
            segments: [{ kind: "text", marks: [], text: "Besvara bara den första frågan." }],
          },
        ],
        item_ids: ["item_001", "item_002"],
        parent_id: "parent_001",
        place: 0,
      },
    ],
  };
}

function currentDocument(server: IntentServer): NativeExamDocument {
  const current = server.documents.get(server.state.position);
  if (current === undefined) {
    throw new Error("expected the served document");
  }
  return current;
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

it("recovery must persist the local title without restoring the other tabs deleted instructions", async () => {
  const base = baseWithParent();
  const server = fakeServer(api, base);
  const state = intentLeaseState();
  const editing = inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), {
      server: intentLeaseDouble(state),
      tabId: "A",
    }),
  );
  editing.applyCommandResponse(response(base, "step-0"));
  await settleIntent();

  const persist = api.storeExamWorkspaceUndoStep.getMockImplementation();
  if (persist === undefined) {
    throw new Error("expected the step store double");
  }
  const ack = deferred<unknown>();
  let stored: unknown = null;
  api.storeExamWorkspaceUndoStep.mockImplementationOnce(
    (lineageId: string, request: unknown) => {
      const saving = persist(lineageId, request);
      stored = saving;
      return ack.promise;
    },
  );
  editing.setTitle("Local title");
  const saving = editing.save();
  await settleIntent();

  await loseIntentLease(editing, state);
  state.holder = "B";
  remoteIntentWrite(server, "step-B", (document) => ({ ...document, parents: [] }));
  expect(currentDocument(server).parents).toEqual([]);

  ack.resolve(stored);
  await saving;
  await settleIntent();
  await reacquireIntentLease(editing, state);

  await editing.save();
  await settleIntent();
  const visible = editing.workspaceDocument.value;
  if (visible === null) {
    throw new Error("expected an open document");
  }
  const first = {
    visible: visible.parents,
    persisted: currentDocument(server).parents,
    title: currentDocument(server).title,
    status: editing.history.saveStatus.value.state,
  };
  await editing.reloadDocument();
  await settleIntent();

  const afterReload = editing.workspaceDocument.value;
  if (afterReload === null) {
    throw new Error("expected an open document");
  }
  expect({ first, afterReload: afterReload.parents }).toEqual({
    first: { visible: [], persisted: [], title: "Local title", status: "saved" },
    afterReload: [],
  });
});
