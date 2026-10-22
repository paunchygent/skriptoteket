/**
 * Exam workspace shared rich-text target.
 *
 * Domain purpose:
 *   The one rich surface the formatting toolbar acts on. Every exam text
 *   editor (the question text, a choice option, a Kategorisera entry, an
 *   ordering step or an instruction) becomes the active target when the
 *   teacher focuses it. The toolbar reads that target's pressed state and
 *   calls its mark and heading actions, so a glyph action edits the text the
 *   teacher is looking at and never another surface.
 *
 * Relationships:
 *   - Provided once per item editor (`ExamWorkspaceQuestionEditor`) and per
 *     instruction editor; `ExamWorkspaceRichTextEditor` registers on focus and
 *     the toolbars dispatch to the active target.
 *   - A component subtree mounted without a provider creates and provides
 *     its own registry, so a standalone editor keeps working.
 *   - A target that accepts pictures is also the surface the picture service
 *     places a chosen, dropped or pasted file on, and it reports whether the
 *     selection is a whole picture so the toolbar offers "Byt bild".
 */

import { inject, provide, shallowRef } from "vue";
import type { InjectionKey, Ref } from "vue";

import type { BodyMark } from "./examWorkspaceBodyMarks";

/** The three heading levels the native document keeps. */
export type RichTextHeadingLevel = 1 | 2 | 3;

/** One editable rich surface: the toolbar calls exactly one of these. */
export type RichTextTarget = {
  /** The marks at this target's current selection, for the toolbar's pressed state. */
  marks: Ref<BodyMark[]>;
  /** This target's paragraph heading level, or null. */
  headingLevel(): RichTextHeadingLevel | null;
  toggleMark(mark: BodyMark): void;
  toggleHeading(level: RichTextHeadingLevel): void;
  /**
   * Turn the selection, or the word at the caret, into a new gap with
   * `gapId`, or insert an empty gap at the caret. The editor emits the
   * change as one `createGap` event, never as an `update`.
   */
  makeGap(gapId: string): void;
  /** True while this surface takes pictures: its `pictures` prop. */
  acceptsPictures: boolean;
  /** The selected `examPicture`'s `assetId`, or null, so the toolbar offers "Byt bild". */
  selectedPictureId: Ref<string | null>;
  /**
   * Place the picture `assetId` alone in its own paragraph at the caret, or
   * replace the picture the selection covers in place. One toolbar edit, so
   * one undo step.
   */
  placePicture(assetId: string): void;
  /** True while the target's editor exists and is not destroyed: a retired surface takes no intake. */
  isLive(): boolean;
  /** Drop the target's saved selection; the registry calls it when another surface takes over. */
  release(): void;
};

export type RichTextTargetRegistry = {
  /** The surface that owns the live or last selected text, or null. */
  active: Ref<RichTextTarget | null>;
  activate(target: RichTextTarget): void;
  deactivate(target: RichTextTarget): void;
};

const RICH_TEXT_TARGET_KEY: InjectionKey<RichTextTargetRegistry> = Symbol(
  "exam-workspace-rich-text-target",
);

export function createRichTextTargetRegistry(): RichTextTargetRegistry {
  const active = shallowRef<RichTextTarget | null>(null);
  return {
    active,
    activate(target: RichTextTarget): void {
      if (active.value === target) {
        return;
      }
      active.value?.release();
      active.value = target;
    },
    deactivate(target: RichTextTarget): void {
      if (active.value === target) {
        active.value = null;
      }
    },
  };
}

/** Create the registry one item editor's rich surfaces share and provide it to them. */
export function provideRichTextTargetRegistry(): RichTextTargetRegistry {
  const registry = createRichTextTargetRegistry();
  provide(RICH_TEXT_TARGET_KEY, registry);
  return registry;
}

/** Inject the item editor's registry; a subtree without one creates and provides its own. */
export function useRichTextTargetRegistry(): RichTextTargetRegistry {
  const injected = inject(RICH_TEXT_TARGET_KEY, null);
  if (injected !== null) {
    return injected;
  }
  return provideRichTextTargetRegistry();
}
