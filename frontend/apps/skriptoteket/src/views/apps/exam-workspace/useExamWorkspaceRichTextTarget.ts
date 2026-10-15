/**
 * Exam workspace rich-text target host.
 *
 * Domain purpose:
 *   The paragraph-side half of the shared formatting target: decide whether
 *   the live browser selection sits in this paragraph or in another rich
 *   surface, remember this paragraph's own range across a mark rebuild,
 *   publish the marks at that range for the toolbar's pressed state, and
 *   make this paragraph the registry's active target. A paragraph action
 *   never falls back to a saved range when another surface owns the
 *   selection, and the saved range is dropped as soon as another target
 *   takes over.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceBodyParagraph`; the registry and target shape
 *     live in `examWorkspaceRichTextTarget`.
 *   - Reads offsets and ranges from `examWorkspaceBodySelection`, parts from
 *     `examWorkspaceBodySegments` and marks from `examWorkspaceBodyMarks`.
 */

import { onBeforeUnmount, onMounted, ref } from "vue";
import type { Ref } from "vue";

import { marksForOffsets } from "./examWorkspaceBodyMarks";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import { partsFromParagraphElement } from "./examWorkspaceBodySegments";
import {
  rangeFromOffsets,
  selectionOffsets,
  type ParagraphSelection,
} from "./examWorkspaceBodySelection";
import { useRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { RichTextHeadingLevel, RichTextTarget } from "./examWorkspaceRichTextTarget";

export type RichTextTargetHost = {
  /** The offsets a paragraph action may use, or null when another surface owns the selection. */
  resolveOffsets(): ParagraphSelection | null;
  /** Publish the marks at `offsets` for the toolbar's pressed state. */
  publishMarks(offsets: ParagraphSelection): void;
  /** Put the selection back over `offsets` after the paragraph DOM was rebuilt. */
  restoreSelection(offsets: ParagraphSelection): void;
  /** Make this paragraph the target the toolbar acts on. */
  activate(): void;
  /** Take the live selection's offsets and marks if it sits in this paragraph. */
  rememberSelection(): void;
};

function partMarks(element: HTMLElement, offsets: ParagraphSelection): BodyMark[] {
  return marksForOffsets(partsFromParagraphElement(element), offsets.start, offsets.end);
}

/** The rich surface that owns a selection boundary, if it sits in one. */
function richSurfaceOf(node: Node): HTMLElement | null {
  const element = node instanceof Element ? node : node.parentElement;
  return element?.closest<HTMLElement>('[contenteditable="true"]') ?? null;
}

/**
 * Whether the live selection belongs to a different rich surface. A
 * selection that touches no rich surface at all (for example while the
 * toolbar itself holds focus) is not another surface, so a paragraph may
 * keep its saved range for its own toolbar.
 */
function liveSelectionOutside(element: HTMLElement): boolean {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) {
    return false;
  }
  const range = selection.getRangeAt(0);
  if (element.contains(range.commonAncestorContainer)) {
    return false;
  }
  if (element.contains(range.startContainer) || element.contains(range.endContainer)) {
    return true;
  }
  return richSurfaceOf(range.startContainer) !== null || richSurfaceOf(range.endContainer) !== null;
}

export function useExamWorkspaceRichTextTarget(options: {
  element: Ref<HTMLElement | null>;
  /** This paragraph's stored heading level. */
  headingLevel: () => RichTextHeadingLevel | null;
  toggleMark: (mark: BodyMark) => void;
  toggleHeading: (level: RichTextHeadingLevel) => void;
}): RichTextTargetHost {
  const registry = useRichTextTargetRegistry();
  const marks = ref<BodyMark[]>([]);
  let savedOffsets: ParagraphSelection | null = null;

  const target: RichTextTarget = {
    marks,
    headingLevel: options.headingLevel,
    toggleMark: options.toggleMark,
    toggleHeading: options.toggleHeading,
    release: () => {
      savedOffsets = null;
    },
  };

  function publishMarks(offsets: ParagraphSelection): void {
    const element = options.element.value;
    if (element) {
      marks.value = partMarks(element, offsets);
    }
  }

  function activate(): void {
    registry.activate(target);
  }

  function rememberSelection(): void {
    const element = options.element.value;
    if (!element) {
      return;
    }
    const offsets = selectionOffsets(element);
    if (!offsets) {
      if (liveSelectionOutside(element)) {
        savedOffsets = null;
      }
      return;
    }
    savedOffsets = offsets;
    activate();
    publishMarks(offsets);
  }

  function restoreSelection(offsets: ParagraphSelection): void {
    const element = options.element.value;
    if (!element) {
      return;
    }
    const range = rangeFromOffsets(element, offsets);
    if (!range) {
      return;
    }
    element.focus({ preventScroll: true });
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(range);
    savedOffsets = offsets;
    activate();
    publishMarks(offsets);
  }

  function resolveOffsets(): ParagraphSelection | null {
    const element = options.element.value;
    if (!element) {
      return null;
    }
    const live = selectionOffsets(element);
    if (live) {
      savedOffsets = live;
      return live;
    }
    if (liveSelectionOutside(element) || registry.active.value !== target) {
      // The selection belongs to another rich surface (or to nothing this
      // paragraph owns): never apply a stale saved range here.
      return null;
    }
    return savedOffsets;
  }

  onMounted(() => {
    document.addEventListener("selectionchange", rememberSelection);
  });

  onBeforeUnmount(() => {
    document.removeEventListener("selectionchange", rememberSelection);
    registry.deactivate(target);
  });

  return { resolveOffsets, publishMarks, restoreSelection, activate, rememberSelection };
}
