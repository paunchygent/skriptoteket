/**
 * Guest exam workspace store: structural commands.
 *
 * Expected behavior:
 *   A structural command sends the editor's document to the public route,
 *   stores exactly one undo step and reports the public route's export
 *   blockers; a stale cursor refuses with the server's 409 before any call
 *   and without persisting; a 422 from a part route keeps the draft while a
 *   429 reports the guest limit.
 */

import { describe, expect, it } from "vitest";

import { ApiError } from "../../../api/client";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { isGuestLimitError } from "./examWorkspaceGuestStore";
import {
  DOCUMENT_ID,
  exam,
  installGuestStoreObjectUrls,
  setupGuestStore,
  startBlank,
  STALE_CURSOR,
  type GuestStoreSetup,
} from "./examWorkspaceGuestStore.specSupport";

installGuestStoreObjectUrls();

async function startBlankSetup(): Promise<GuestStoreSetup> {
  const context = setupGuestStore();
  await startBlank(context);
  return context;
}

describe("examWorkspaceGuestStore structural commands", () => {
  it("sends the editor's document with a parent command, stores one step and reports the blockers", async () => {
    const context = await startBlankSetup();
    const lineageId = DOCUMENT_ID;
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    const blocker = { item_id: null, reason: "title_without_text" as const };
    context.mocks.createParent.mockResolvedValue({
      document: exam("Med instruktion"),
      export_blockers: [blocker],
    });
    const child = newTeacherItem("item_002", 2, "free_text");
    const instruction = [
      { heading_level: null, segments: [{ kind: "text" as const, marks: [], text: "Läs." }] },
    ];

    const response = await context.store.store.shared.createExamWorkspaceParent(lineageId, {
      child,
      expected_cursor: opened.history_cursor,
      instruction,
      position: 0,
    });

    expect(context.mocks.createParent).toHaveBeenCalledWith({
      child,
      document: opened.document,
      instruction,
      position: 0,
    });
    expect(response.export_blockers).toEqual([blocker]);
    expect(response.document.title).toBe("Med instruktion");
    expect(response.history_cursor).not.toBe(opened.history_cursor);
    const history = await context.store.store.shared.getExamWorkspaceHistory(lineageId);
    expect(history.step_ids).toHaveLength(1);
    expect(history.step_ids[0]).toBe(history.position_step_id);
    expect(history.position_step_id).toBe(response.history_cursor);
  });

  it("runs group, empty part and move as one public call and one undo step each", async () => {
    const context = await startBlankSetup();
    const lineageId = DOCUMENT_ID;
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    context.mocks.groupItems.mockResolvedValue({
      created_parent_id: "parent_002",
      document: exam("Grupperad"),
      export_blockers: [],
    });
    context.mocks.createEmptyPart.mockResolvedValue({
      created_parent_id: "parent_003",
      document: exam("Ny del"),
      export_blockers: [],
    });
    context.mocks.moveItem.mockResolvedValue({ document: exam("Flyttad"), export_blockers: [] });

    const grouped = await context.store.store.shared.groupExamWorkspaceItems(lineageId, [
      "item_004",
    ], opened.history_cursor);
    expect(context.mocks.groupItems).toHaveBeenCalledTimes(1);
    expect(context.mocks.groupItems.mock.calls[0]![0]).toEqual(opened.document);
    expect(context.mocks.groupItems).toHaveBeenCalledWith(expect.anything(), ["item_004"]);
    expect(grouped.created_parent_id).toBe("parent_002");
    expect(grouped.document.title).toBe("Grupperad");
    expect(grouped.export_blockers).toEqual([]);
    let history = await context.store.store.shared.getExamWorkspaceHistory(lineageId);
    expect(history.step_ids).toHaveLength(1);
    expect(history.step_ids[0]).toBe(history.position_step_id);
    expect(history.position_step_id).toBe(grouped.history_cursor);
    expect((await context.storage.load())?.draft.cursor).toBe(grouped.history_cursor);

    const emptied = await context.store.store.shared.createEmptyExamWorkspacePart(
      lineageId,
      2,
      grouped.history_cursor,
    );
    expect(context.mocks.createEmptyPart).toHaveBeenCalledTimes(1);
    expect(context.mocks.createEmptyPart.mock.calls[0]![0]).toEqual(grouped.document);
    expect(context.mocks.createEmptyPart).toHaveBeenCalledWith(expect.anything(), 2);
    expect(emptied.created_parent_id).toBe("parent_003");
    expect(emptied.document.title).toBe("Ny del");
    history = await context.store.store.shared.getExamWorkspaceHistory(lineageId);
    expect(history.step_ids).toHaveLength(2);
    expect(history.position_step_id).toBe(emptied.history_cursor);
    expect((await context.storage.load())?.draft.cursor).toBe(emptied.history_cursor);

    const moved = await context.store.store.shared.moveExamWorkspaceItem(
      lineageId,
      "item_004",
      "parent_002",
      emptied.history_cursor,
    );
    expect(context.mocks.moveItem).toHaveBeenCalledTimes(1);
    expect(context.mocks.moveItem.mock.calls[0]![0]).toEqual(emptied.document);
    expect(context.mocks.moveItem).toHaveBeenCalledWith(expect.anything(), "item_004", "parent_002");
    expect(moved.document.title).toBe("Flyttad");
    history = await context.store.store.shared.getExamWorkspaceHistory(lineageId);
    expect(history.step_ids).toHaveLength(3);
    expect(history.position_step_id).toBe(moved.history_cursor);
    expect((await context.storage.load())?.draft.cursor).toBe(moved.history_cursor);
  });

  it("refuses a stale cursor on the part commands without calling or persisting", async () => {
    const context = await startBlankSetup();
    const lineageId = DOCUMENT_ID;
    const persisted = await context.storage.load();

    const attempts = [
      () =>
        context.store.store.shared.groupExamWorkspaceItems(lineageId, ["item_004"], STALE_CURSOR),
      () => context.store.store.shared.createEmptyExamWorkspacePart(lineageId, 0, STALE_CURSOR),
      () =>
        context.store.store.shared.moveExamWorkspaceItem(lineageId, "item_004", null, STALE_CURSOR),
    ];
    for (const attempt of attempts) {
      const error = await attempt().catch((caught: unknown) => caught);
      expect(error).toBeInstanceOf(ApiError);
      expect(error).toMatchObject({ code: "CONFLICT", status: 409 });
    }

    expect(context.mocks.groupItems).not.toHaveBeenCalled();
    expect(context.mocks.createEmptyPart).not.toHaveBeenCalled();
    expect(context.mocks.moveItem).not.toHaveBeenCalled();
    expect(await context.storage.load()).toEqual(persisted);
  });

  it("keeps the draft on a 422 from a part route and reports a 429 as the guest limit", async () => {
    const context = await startBlankSetup();
    const lineageId = DOCUMENT_ID;
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    const persisted = await context.storage.load();

    const refusal = new ApiError({
      code: "VALIDATION_ERROR",
      message: "Provet måste ha minst en fråga.",
      status: 422,
    });
    context.mocks.moveItem.mockRejectedValue(refusal);
    const refused = await context.store.store.shared
      .moveExamWorkspaceItem(lineageId, "item_004", null, opened.history_cursor)
      .catch((caught: unknown) => caught);
    expect(refused).toBe(refusal);
    expect(await context.storage.load()).toEqual(persisted);

    const limit = new ApiError({
      code: "TOO_MANY_REQUESTS",
      details: { bucket: "guest_edit", reason: "caller_limit" },
      message: "Gränsen för gäster är nådd. Logga in för att fortsätta.",
      status: 429,
    });
    context.mocks.groupItems.mockRejectedValue(limit);
    const limited = await context.store.store.shared
      .groupExamWorkspaceItems(lineageId, ["item_004"], opened.history_cursor)
      .catch((caught: unknown) => caught);
    expect(limited).toBe(limit);
    expect(isGuestLimitError(limited)).toBe(true);
    expect(await context.storage.load()).toEqual(persisted);
  });
});
