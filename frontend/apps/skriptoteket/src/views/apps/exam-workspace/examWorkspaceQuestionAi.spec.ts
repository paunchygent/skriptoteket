/**
 * Exam workspace per-question AI controls: one state table for the toolbar group.
 *
 * Expected behavior (TASK-SKRIPT-40-04-26 D2-D6):
 *   Föreslå facit asks for this one question's key through the existing
 *   `item_id` request and is enabled only while the question has no key; after
 *   an undo it reads Föreslå igen once, a spent retry says the retry is used,
 *   the daily limit disables it with the door's own note, and a running
 *   suggestion says so. Undo is offered for the keyed kinds and for any AI
 *   key, and is enabled while an AI key can be undone (never for a dropdown,
 *   which has no valid keyless state). Gör om till [typ] is offered while the
 *   labeler suggests another type, or while the question is unbuilt. Guests
 *   see none of the three.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamItem, NativeExamItemKind } from "../../../api/examWorkspace";
import { AI_APP_LIMIT_NOTE } from "../../../composables/aiDailyLimit";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { questionAiControls } from "./examWorkspaceQuestionAi";
import type { QuestionAiContext } from "./examWorkspaceQuestionAi";

type Origin = NativeExamItem["answer_key"]["origin"];
type Retry = NativeExamItem["answer_key_retry"];

const HAS_FACIT_WITH_RETRY =
  "Föreslå facit · Frågan har redan facit. Ångra AI-tolkningen om du vill ha ett nytt förslag.";
const HAS_FACIT = "Föreslå facit · Frågan har redan facit.";
const RETRY_OFFERED = "Föreslå igen · Föreslå ett nytt facit för frågan. Du kan göra det en gång.";
const RETRY_USED = "Föreslå facit · Du har redan bett om ett nytt förslag för frågan.";
const NO_UNDO = "Ångra AI-tolkningen · Det finns ingen AI-tolkning att ångra";
const DROPDOWN_UNDO = "Ångra AI-tolkningen · En lucka med rullista måste ha ett rätt svar.";

function item(
  kind: NativeExamItemKind,
  origin: Origin = "absent",
  options: { retry?: Retry; suggested?: NativeExamItemKind | null; unbuilt?: boolean } = {},
): NativeExamItem {
  const base = newTeacherItem("item_001", 1, kind);
  return {
    ...base,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin },
    answer_key_retry: options.retry ?? "none",
    review: options.unbuilt
      ? { confidence: null, parse_origin: "source_fallback", reasons: [], state: "review_required" }
      : base.review,
    suggested_kind: options.suggested ?? null,
  };
}

function context(overrides: Partial<QuestionAiContext> = {}): QuestionAiContext {
  return {
    busy: false,
    guest: false,
    limitNote: null,
    locked: false,
    suggestAvailable: true,
    ...overrides,
  };
}

describe("questionAiControls suggest (Föreslå facit)", () => {
  it("offers an enabled Föreslå facit for a keyless question", () => {
    const suggest = questionAiControls(item("single_choice"), context()).suggest;

    expect(suggest).toEqual({
      busy: false,
      description: null,
      enabled: true,
      hint: null,
      label: "Föreslå facit",
      title: "Föreslå facit för frågan",
    });
  });

  it.each(["single_choice", "multiple_response", "gap_fill", "matching"] as const)(
    "offers it for the keyed kind %s",
    (kind) => {
      expect(questionAiControls(item(kind), context()).suggest).not.toBeNull();
    },
  );

  it.each(["free_text", "inline_choice", "ordering"] as const)(
    "offers nothing for the unkeyed kind %s",
    (kind) => {
      expect(questionAiControls(item(kind), context()).suggest).toBeNull();
    },
  );

  it("disables it on a question that already has an AI key and names the undo", () => {
    const suggest = questionAiControls(item("single_choice", "ai_interpreted"), context()).suggest;

    expect(suggest).toMatchObject({
      enabled: false,
      hint: "Har facit",
      label: "Föreslå facit",
      title: HAS_FACIT_WITH_RETRY,
    });
  });

  it("does not promise a retry once the question's retry is used", () => {
    const suggest = questionAiControls(
      item("single_choice", "machine_proposed", { retry: "used" }),
      context(),
    ).suggest;

    expect(suggest).toMatchObject({ enabled: false, hint: "Har facit", title: HAS_FACIT });
  });

  it("keeps it disabled for a source or teacher key", () => {
    const suggest = questionAiControls(item("gap_fill", "source_provided"), context()).suggest;

    expect(suggest).toMatchObject({ enabled: false, hint: "Har facit", title: HAS_FACIT });
  });

  it("offers Föreslå igen once after an undo", () => {
    const suggest = questionAiControls(
      item("single_choice", "absent", { retry: "offered" }),
      context(),
    ).suggest;

    expect(suggest).toMatchObject({
      busy: false,
      enabled: true,
      hint: null,
      label: "Föreslå igen",
      title: RETRY_OFFERED,
    });
  });

  it("says the retry is used after the one retry", () => {
    const suggest = questionAiControls(
      item("single_choice", "absent", { retry: "used" }),
      context(),
    ).suggest;

    expect(suggest).toMatchObject({
      enabled: false,
      hint: "Redan föreslaget igen",
      label: "Föreslå facit",
      title: RETRY_USED,
    });
  });

  it("says the suggestion is being made while busy", () => {
    const suggest = questionAiControls(item("matching"), context({ busy: true })).suggest;

    expect(suggest).toMatchObject({
      busy: true,
      enabled: false,
      label: "Föreslå facit",
      title: "Facitförslaget tas fram …",
    });
  });

  it("disables it with the door's note when the daily limit is reached", () => {
    const suggest = questionAiControls(
      item("single_choice"),
      context({ limitNote: AI_APP_LIMIT_NOTE }),
    ).suggest;

    expect(suggest).toMatchObject({
      description: AI_APP_LIMIT_NOTE,
      enabled: false,
      hint: "Dagens gräns nådd",
      title: AI_APP_LIMIT_NOTE,
    });
  });

  it("disables the offer while the question is locked", () => {
    expect(questionAiControls(item("single_choice"), context({ locked: true })).suggest?.enabled).toBe(
      false,
    );
    expect(
      questionAiControls(item("single_choice", "absent", { retry: "offered" }), context({ locked: true }))
        .suggest?.enabled,
    ).toBe(false);
  });

  it("shows no suggest control without an AI provider", () => {
    expect(
      questionAiControls(item("single_choice"), context({ suggestAvailable: false })).suggest,
    ).toBeNull();
  });
});

describe("questionAiControls undo (Ångra AI-tolkningen)", () => {
  it.each(["single_choice", "multiple_response", "gap_fill", "matching"] as const)(
    "offers it for the keyed kind %s, without one enabled on an absent key",
    (kind) => {
      const undo = questionAiControls(item(kind), context()).undo;

      expect(undo).toMatchObject({ enabled: false, hint: null, label: "Ångra AI-tolkningen", title: NO_UNDO });
    },
  );

  it.each(["ai_interpreted", "machine_proposed"] as const)(
    "enables it for the %s AI key",
    (origin) => {
      const undo = questionAiControls(item("single_choice", origin), context()).undo;

      expect(undo).toMatchObject({
        enabled: true,
        label: "Ångra AI-tolkningen",
        title: "Ångra AI-tolkningen och lämna frågan utan facit",
      });
    },
  );

  it("offers it for an AI key on a kind the suggest control skips", () => {
    expect(questionAiControls(item("free_text", "machine_proposed"), context()).undo).toMatchObject({
      enabled: true,
    });
    expect(questionAiControls(item("ordering", "ai_interpreted"), context()).undo).toMatchObject({
      enabled: true,
    });
  });

  it("shows it disabled on a dropdown AI key and names the reason", () => {
    const undo = questionAiControls(item("inline_choice", "ai_interpreted"), context()).undo;

    expect(undo).toMatchObject({ enabled: false, title: DROPDOWN_UNDO });
  });

  it("shows no undo for a question with neither a keyed kind nor an AI key", () => {
    expect(questionAiControls(item("free_text"), context()).undo).toBeNull();
    expect(questionAiControls(item("inline_choice", "teacher_authored"), context()).undo).toBeNull();
  });

  it("disables it while the question is locked", () => {
    expect(
      questionAiControls(item("single_choice", "machine_proposed"), context({ locked: true })).undo?.enabled,
    ).toBe(false);
  });
});

describe("questionAiControls convert (Gör om till [typ])", () => {
  it("offers the suggested type with its label and title", () => {
    const convert = questionAiControls(
      item("single_choice", "absent", { suggested: "multiple_response" }),
      context(),
    ).convert;

    expect(convert).toEqual({
      enabled: true,
      kind: "multiple_response",
      label: "Gör om till Flerval: flera val",
      title: "Gör om till Flerval: flera val",
      typeName: "Flerval: flera val",
    });
  });

  it("offers nothing without a suggestion, or when the suggestion is the current type", () => {
    expect(questionAiControls(item("single_choice"), context()).convert).toBeNull();
    expect(
      questionAiControls(item("single_choice", "absent", { suggested: "single_choice" }), context()).convert,
    ).toBeNull();
  });

  it("offers a suggestion equal to the current type while the question is unbuilt", () => {
    const convert = questionAiControls(
      item("single_choice", "absent", { suggested: "single_choice", unbuilt: true }),
      context(),
    ).convert;

    expect(convert).toMatchObject({ enabled: true, kind: "single_choice" });
  });

  it("disables it while a suggestion runs or the question is locked", () => {
    const suggested = item("single_choice", "absent", { suggested: "gap_fill" });

    expect(questionAiControls(suggested, context({ busy: true })).convert?.enabled).toBe(false);
    expect(questionAiControls(suggested, context({ locked: true })).convert?.enabled).toBe(false);
  });
});

describe("questionAiControls guests", () => {
  it("shows no control at all", () => {
    const controls = questionAiControls(
      item("single_choice", "machine_proposed", { suggested: "gap_fill" }),
      context({ guest: true }),
    );

    expect(controls).toEqual({ convert: null, suggest: null, undo: null });
  });
});
