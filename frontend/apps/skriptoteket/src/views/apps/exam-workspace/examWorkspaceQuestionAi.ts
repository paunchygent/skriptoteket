/**
 * Exam workspace per-question AI controls.
 *
 * Domain purpose:
 *   Decide which of the three per-question AI controls the question-text
 *   toolbar's AI group shows and in what state (TASK-SKRIPT-40-04-26 D2-D6):
 *   Föreslå facit for this question through the existing `item_id` request,
 *   undo the AI key, and Gör om till [typ] when the labeler suggested another
 *   type. The rule lives here once, apart from the component, so the same
 *   question state reads the same way in the toolbar and in the phone menu
 *   row that reuses these controls.
 *
 *   Föreslå facit is offered only where an answer key of that family exists
 *   (`answer_key_view.py`'s `_VIEW_KIND_BY_ITEM_KIND`: choice, multi,
 *   gap-fill and matching), is enabled only while the question has no key,
 *   reads Föreslå igen for the one retry an undo opens (D4), and says the
 *   retry is used once it is spent. Undo is offered for those same kinds and
 *   for any AI key, and is enabled while an AI key exists that can be undone:
 *   `ai_interpreted` or `machine_proposed`, never a dropdown, which has no
 *   valid keyless state (D5). Gör om till [typ] keeps the head's old rule:
 *   offered while the labeler suggests another type, or while the question
 *   was never converted.
 *
 * Relationships:
 *   - Read by `useExamWorkspaceQuestionAiControls`, which adds the
 *     workspace's AI keys, the guest mode and the daily limit note to the
 *     item state for the toolbar group and the ⋮ rows.
 *   - `canUndoAiKey` in `examWorkspaceItemEdits` owns undo eligibility, so the
 *     toolbar and the shared item-edit rules cannot disagree.
 *   - `examWorkspaceItemReadiness` owns "unbuilt", `examWorkspaceRows` the
 *     type names.
 */

import type { NativeExamItem, NativeExamItemKind } from "../../../api/examWorkspace";
import { canUndoAiKey } from "./examWorkspaceItemEdits";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { EXAM_WORKSPACE_TYPE_LABELS } from "./examWorkspaceRows";

/**
 * The glyph of the toolbar's undo control. `discard-ai-key` is the shared
 * catalogue's Eraser meaning, and this constant is the only place the toolbar
 * names it.
 */
export const AI_KEY_UNDO_GLYPH = "discard-ai-key";

/**
 * The question kinds that carry an answer key, mirroring
 * `_VIEW_KIND_BY_ITEM_KIND` in
 * `domain/curated_apps/exam_workspace/answer_key_view.py`: a suggestion is
 * only asked for where a key can land.
 */
const SUGGESTIBLE_KINDS: ReadonlySet<NativeExamItemKind> = new Set<NativeExamItemKind>([
  "single_choice",
  "multiple_response",
  "gap_fill",
  "matching",
]);

/** The item state and workspace state one toolbar AI group decides from. */
export type QuestionAiContext = {
  /** A guest workspace shows no AI control at all. */
  guest: boolean;
  /** An answer-key suggestion is being requested or runs. */
  busy: boolean;
  /** The question cannot change: disabled, or still converting. */
  locked: boolean;
  /** The door's daily-limit note, or null while AI is available. */
  limitNote: string | null;
  /** Whether the workspace can ask for one question's suggestion. */
  suggestAvailable: boolean;
};

/** Föreslå facit: glyph-only in the toolbar, `hint` for the menu row. */
export type QuestionAiSuggestControl = {
  enabled: boolean;
  busy: boolean;
  /** The accessible name and the menu row's word. */
  label: string;
  title: string;
  /** A short menu hint, or null. */
  hint: string | null;
  /** The door's own sentence for `aria-description`, or null. */
  description: string | null;
};

/** Ångra AI-tolkningen: glyph-only, its meaning in `title`. */
export type QuestionAiUndoControl = {
  enabled: boolean;
  label: string;
  title: string;
  hint: null;
};

/** Gör om till [typ]: glyph and the type name. */
export type QuestionAiConvertControl = {
  kind: NativeExamItemKind;
  typeName: string;
  /** The accessible name and menu word: "Gör om till [typ]". */
  label: string;
  title: string;
  enabled: boolean;
};

export type QuestionAiControls = {
  suggest: QuestionAiSuggestControl | null;
  undo: QuestionAiUndoControl | null;
  convert: QuestionAiConvertControl | null;
};

function suggestControl(
  item: NativeExamItem,
  context: QuestionAiContext,
): QuestionAiSuggestControl | null {
  if (!context.suggestAvailable || !SUGGESTIBLE_KINDS.has(item.kind)) {
    return null;
  }
  const label = "Föreslå facit";
  if (context.busy) {
    return { busy: true, description: null, enabled: false, hint: null, label, title: "Facitförslaget tas fram …" };
  }
  if (context.limitNote !== null) {
    return {
      busy: false,
      description: context.limitNote,
      enabled: false,
      hint: "Dagens gräns nådd",
      label,
      title: context.limitNote,
    };
  }
  if (item.answer_key.origin !== "absent") {
    return {
      busy: false,
      description: null,
      enabled: false,
      hint: "Har facit",
      label,
      title:
        canUndoAiKey(item) && item.answer_key_retry !== "used"
          ? "Föreslå facit · Frågan har redan facit. Ångra AI-tolkningen om du vill ha ett nytt förslag."
          : "Föreslå facit · Frågan har redan facit.",
    };
  }
  if (item.answer_key_retry === "offered") {
    return {
      busy: false,
      description: null,
      enabled: !context.locked,
      hint: null,
      label: "Föreslå igen",
      title: "Föreslå igen · Föreslå ett nytt facit för frågan. Du kan göra det en gång.",
    };
  }
  if (item.answer_key_retry === "used") {
    return {
      busy: false,
      description: null,
      enabled: false,
      hint: "Redan föreslaget igen",
      label,
      title: "Föreslå facit · Du har redan bett om ett nytt förslag för frågan.",
    };
  }
  return { busy: false, description: null, enabled: !context.locked, hint: null, label, title: "Föreslå facit för frågan" };
}

function undoControl(item: NativeExamItem, context: QuestionAiContext): QuestionAiUndoControl | null {
  const origin = item.answer_key.origin;
  const aiKey = origin === "ai_interpreted" || origin === "machine_proposed";
  if (!SUGGESTIBLE_KINDS.has(item.kind) && !aiKey) {
    return null;
  }
  const enabled = canUndoAiKey(item) && !context.locked;
  let title = "Ångra AI-tolkningen · Det finns ingen AI-tolkning att ångra";
  if (enabled) {
    title = "Ångra AI-tolkningen och lämna frågan utan facit";
  } else if (item.kind === "inline_choice" && aiKey) {
    title = "Ångra AI-tolkningen · En lucka med rullista måste ha ett rätt svar.";
  }
  return { enabled, hint: null, label: "Ångra AI-tolkningen", title };
}

function convertControl(
  item: NativeExamItem,
  context: QuestionAiContext,
): QuestionAiConvertControl | null {
  const suggested = item.suggested_kind;
  if (suggested === null) {
    return null;
  }
  const unbuilt = examWorkspaceItemReadiness(item).includes("unbuilt_question");
  if (suggested === item.kind && !unbuilt) {
    return null;
  }
  const typeName = EXAM_WORKSPACE_TYPE_LABELS[suggested];
  const label = `Gör om till ${typeName}`;
  return { enabled: !context.busy && !context.locked, kind: suggested, label, title: label, typeName };
}

/** The three controls the question-text toolbar shows for this question, each null when not shown. */
export function questionAiControls(
  item: NativeExamItem,
  context: QuestionAiContext,
): QuestionAiControls {
  if (context.guest) {
    return { convert: null, suggest: null, undo: null };
  }
  return {
    convert: convertControl(item, context),
    suggest: suggestControl(item, context),
    undo: undoControl(item, context),
  };
}
