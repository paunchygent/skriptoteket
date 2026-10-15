/**
 * Exam workspace shared rich-text target.
 *
 * Domain purpose:
 *   The one rich surface the formatting toolbar acts on. Every editable
 *   paragraph — a question paragraph, a choice option or a Kategorisera
 *   entry — becomes the active target when the teacher focuses it or
 *   selects inside it. The toolbar reads that target's pressed state and
 *   calls its mark and heading actions, so a glyph action edits the text the
 *   teacher is looking at and can never reach a stale selection in another
 *   surface. The previous target drops its saved selection when another one
 *   becomes active.
 *
 * Relationships:
 *   - Provided once per item editor (`ExamWorkspaceItemEditor`) and consumed
 *     by `ExamWorkspaceBodyParagraph` (registers) and
 *     `ExamWorkspaceBodyEditor` (dispatches the toolbar).
 *   - A component subtree mounted without a provider creates and provides
 *     its own registry, so a standalone paragraph keeps working.
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
