/**
 * Which arrivals run again after a save's outcome replaces the open copy
 * (TASK-SKRIPT-39-04-07, case space A rows A17-A20).
 *
 * Expected behavior:
 *   A save response replays only the arrivals numbered after its payload's
 *   mark, so an arrival a recursive save after a conversion merge already
 *   carried never runs twice. A conflict reload replays every arrival since
 *   the teacher's save began, first flight included, in order. The specs
 *   choose documents where running an arrival a second time, or skipping
 *   one, would leave a visible difference.
 */

import { ref, shallowRef } from "vue";
import { describe, expect, it, vi } from "vitest";

import type {
  NativeAnswerKeySuggestion,
  NativeExamDocument,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { pairs } from "./examWorkspaceKeyedItems.specSupport";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import { sameDocument } from "./examWorkspaceConversionMerge";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";
import { buildResponse } from "./useExamWorkspaceDocument.specSupport";
import { useExamWorkspaceSaveArrivals } from "./useExamWorkspaceSaveArrivals";

const P1: [string, string] = ["left_001", "right_001"];
const P2: [string, string] = ["left_002", "right_002"];
const P3: [string, string] = ["left_003", "right_003"];
// A key unequal, as a set, to [P1, P2, P3].
const CROSSED: Array<[string, string]> = [["left_001", "right_002"], ["left_002", "right_001"], P3];
const ROTATED: Array<[string, string]> = [["left_001", "right_003"], P2, ["left_003", "right_001"]];

function suggestion(entries: Array<[string, string]>): NativeAnswerKeySuggestion {
  return {
    correct_choice_ids: [],
    fingerprint: "a".repeat(64),
    gap_accepted_values: [],
    match_pairs: pairs(entries),
    model: "model",
    prompt_template_version: "v1",
    provider_profile_id: "profile",
  };
}

function documentWith(item: NativeExamItem): NativeExamDocument {
  return { ...buildResponse().document, items: [item] };
}

function unreviewedMachineItem(
  key: Array<[string, string]>,
  kept: NativeAnswerKeySuggestion,
): NativeExamItem {
  const item = buildMatchingItem({
    ai_suggestion: kept,
    answer_key: { correct_choice_ids: [], match_pairs: pairs(key), origin: "machine_proposed" },
  });
  return { ...item, review: { ...item.review, state: "review_required" } };
}

function setup(item: NativeExamItem) {
  const workspaceDocument = ref<NativeExamDocument | null>(documentWith(item));
  const serverDocument = ref<NativeExamDocument | null>(workspaceDocument.value);
  const convertingItemIds = ref<ReadonlySet<string>>(new Set());
  const opening: ExamWorkspaceOpening = { lineageId: "lineage-1" };
  const openExam = shallowRef<ExamWorkspaceOpening | null>(opening);
  const arrivals = useExamWorkspaceSaveArrivals({
    convertingItemIds,
    isOpen: (candidate) => openExam.value === candidate,
    noteArrival: vi.fn(),
    workspaceDocument,
  });
  function deliver(arriving: NativeAnswerKeySuggestion): void {
    arrivals.applyArrivingSuggestions(opening, [{ item_id: "item_001", suggestion: arriving }]);
  }
  /** A server document replaces the copy. */
  function replaceWith(document: NativeExamDocument | null): void {
    workspaceDocument.value = document;
    serverDocument.value = document;
  }
  function matchesServer(): boolean {
    return sameDocument(workspaceDocument.value, serverDocument.value);
  }
  function item0(): NativeExamItem {
    const current = workspaceDocument.value?.items[0];
    if (!current) {
      throw new Error("expected an item");
    }
    return current;
  }
  return { arrivals, deliver, item0, matchesServer, openExam, replaceWith, workspaceDocument };
}

describe("a save response replays only arrivals its payload was read without", () => {
  it("A18: an arrival the recursive save already carried does not run again", () => {
    // Running A1 again on its own effect would reorder the key to A1's order:
    // the key equals A1 as a set, and A1 is now the previous suggestion.
    const a1 = suggestion([P1, P2, P3]);
    const { arrivals, deliver, item0, matchesServer, replaceWith } = setup(
      unreviewedMachineItem([P2, P1, P3], suggestion(ROTATED)),
    );

    const opened = arrivals.beginHold();
    deliver(a1);
    expect(item0().answer_key.match_pairs).toEqual(pairs([P2, P1, P3]));
    // The conflict merge kept the copy; the recursive save reads it now.
    const recursiveMark = arrivals.payloadMark();
    expect(arrivals.beginHold()).toBe(false);
    replaceWith(documentWith(item0()));
    arrivals.replayAfterResponse(recursiveMark);
    arrivals.endHold(opened);

    expect(item0().answer_key.match_pairs).toEqual(pairs([P2, P1, P3]));
    expect(item0().ai_suggestion).toEqual(a1);
    expect(matchesServer()).toBe(true);
  });

  it("A17: an arrival after the recursive save's payload runs once on its response", () => {
    const a1 = suggestion([P1, P2, P3]);
    const a2 = suggestion(ROTATED);
    const { arrivals, deliver, item0, matchesServer, replaceWith } = setup(
      unreviewedMachineItem([P2, P1, P3], suggestion([P2, P1, P3])),
    );

    const opened = arrivals.beginHold();
    deliver(a1);
    const recursiveMark = arrivals.payloadMark();
    arrivals.beginHold();
    const recursivePayload = documentWith(item0());
    deliver(a2);
    replaceWith(recursivePayload);
    arrivals.replayAfterResponse(recursiveMark);
    arrivals.endHold(opened);

    expect(item0().ai_suggestion).toEqual(a2);
    expect(item0().answer_key.match_pairs).toEqual(a2.match_pairs);
    expect(matchesServer()).toBe(false);
  });
});

describe("a conflict reload replays every arrival since the teacher's save began", () => {
  it("A20: first-flight and recursive-flight arrivals run in order on the reloaded head", () => {
    // A1 fits and becomes the key; A2 pairs a left entry the question lacks,
    // so it is kept without becoming the key (P13). Skipping A1 would leave
    // the reloaded key in place.
    const s = suggestion(CROSSED);
    const a1 = suggestion([P1, P2, P3]);
    const a2 = suggestion([P1, P2, ["left_009", "right_003"]]);
    const reloaded = documentWith(unreviewedMachineItem(CROSSED, s));
    const { arrivals, deliver, item0, matchesServer, replaceWith } = setup(unreviewedMachineItem(CROSSED, s));

    const opened = arrivals.beginHold();
    deliver(a1);
    arrivals.beginHold();
    deliver(a2);
    replaceWith(reloaded);
    arrivals.replayAfterReload();
    arrivals.endHold(opened);

    expect(item0().ai_suggestion).toEqual(a2);
    expect(item0().answer_key).toEqual({
      correct_choice_ids: [],
      match_pairs: a1.match_pairs,
      origin: "machine_proposed",
    });
    expect(matchesServer()).toBe(false);
  });

  it("closes the list when the save that opened it ends", () => {
    const { arrivals, deliver, matchesServer, replaceWith, workspaceDocument } = setup(
      unreviewedMachineItem([P2, P1, P3], suggestion([P2, P1, P3])),
    );
    const reloaded = workspaceDocument.value;

    const opened = arrivals.beginHold();
    arrivals.endHold(opened);
    deliver(suggestion([P1, P2, P3]));
    replaceWith(reloaded);
    arrivals.replayAfterReload();

    expect(workspaceDocument.value).toBe(reloaded);
    expect(matchesServer()).toBe(true);
  });
});

describe("an arrival is written only into the exam opening that requested it", () => {
  it("writes nothing, first delivery or replay, once another opening is open", () => {
    const { arrivals, deliver, item0, openExam, replaceWith, workspaceDocument } = setup(
      unreviewedMachineItem([P2, P1, P3], suggestion([P2, P1, P3])),
    );
    const before = workspaceDocument.value;

    const opened = arrivals.beginHold();
    deliver(suggestion([P1, P2, P3]));
    expect(item0().ai_suggestion).toEqual(suggestion([P1, P2, P3]));
    openExam.value = { lineageId: "lineage-1" };
    replaceWith(before);
    arrivals.replayAfterReload();
    deliver(suggestion(ROTATED));
    arrivals.endHold(opened);

    expect(workspaceDocument.value).toBe(before);
  });
});
