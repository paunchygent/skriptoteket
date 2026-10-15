/**
 * Exam workspace rich-text target host.
 *
 * Domain purpose:
 *   The paragraph-side half of the shared formatting target: decide whether
 *   the live browser selection sits in this paragraph or in another rich
 *   surface, remember this paragraph's own range across a mark rebuild,
 *   publish the marks at that range for the toolbar's pressed state, and
 *   make this paragraph the registry's active target. A saved range binds to
 *   the semantic owner — item, surface, entry and paragraph — and to the
 *   content revision it was taken from, so replacing the native item or its
 *   text releases the range instead of formatting whatever now occupies the
 *   old offsets. A paragraph action never falls back to a stale saved range,
 *   and the saved range is dropped as soon as another target takes over.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceBodyParagraph`; the registry and target shape
 *     live in `examWorkspaceRichTextTarget`.
 *   - Reads offsets and ranges from `examWorkspaceBodySelection`, parts from
 *     `examWorkspaceBodySegments` and marks from `examWorkspaceBodyMarks`.
 */

import { onBeforeUnmount, onMounted, ref, watch } from "vue";
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

/** The item surface a paragraph belongs to: the question text, a choice option or a matching row/column. */
export type RichTextSurface = "question" | "choice" | "match-left" | "match-right";

/** The semantic owner of one paragraph: the item, its surface and the entry inside it. */
export type RichTextSurfaceOwner = {
  itemId: string;
  surface: RichTextSurface;
  /** The choice or matching entry id; null on the question text. */
  entryId: string | null;
};

/** The identity a saved selection binds to: the owner plus one paragraph and its content revision. */
export function richTextOwnerKey(owner: RichTextSurfaceOwner, paragraphIndex: number): string {
  return [owner.itemId, owner.surface, owner.entryId ?? "", paragraphIndex].join("\u0000");
}

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
  /** Whether this paragraph is still the surface the toolbar may act on: no other rich surface owns it. */
  isCurrentTarget(): boolean;
  /** Drop this paragraph's saved range and active state because its owner or content was replaced. */
  invalidate(): void;
};

/** A remembered range together with the paragraph identity and content it was taken from. */
type SavedSelection = {
  offsets: ParagraphSelection;
  ownerKey: string;
  revision: string | undefined;
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
  /** The paragraph's semantic owner and index; a changed key drops its saved range. */
  ownerKey: () => string;
  /** The rendered content revision; replaced content drops a range taken from other text. */
  contentRevision: () => string | undefined;
  /** This paragraph's stored heading level. */
  headingLevel: () => RichTextHeadingLevel | null;
  toggleMark: (mark: BodyMark) => void;
  toggleHeading: (level: RichTextHeadingLevel) => void;
}): RichTextTargetHost {
  const registry = useRichTextTargetRegistry();
  const marks = ref<BodyMark[]>([]);
  let saved: SavedSelection | null = null;

  /** Drop the saved range and pressed state; the registry calls it when another surface takes over. */
  function release(): void {
    saved = null;
    marks.value = [];
  }

  function savedMatchesCurrent(): boolean {
    return (
      saved !== null &&
      saved.ownerKey === options.ownerKey() &&
      saved.revision === options.contentRevision()
    );
  }

  /** Release the saved range and the active target because the owner or its content was replaced. */
  function invalidate(): void {
    release();
    registry.deactivate(target);
  }

  const target: RichTextTarget = {
    marks,
    headingLevel: options.headingLevel,
    toggleMark: options.toggleMark,
    toggleHeading: options.toggleHeading,
    release,
  };

  function savedFrom(offsets: ParagraphSelection): SavedSelection {
    return { offsets, ownerKey: options.ownerKey(), revision: options.contentRevision() };
  }

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
        invalidate();
      }
      return;
    }
    saved = savedFrom(offsets);
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
    saved = savedFrom(offsets);
    activate();
    publishMarks(offsets);
  }

  function isCurrentTarget(): boolean {
    const element = options.element.value;
    if (!element) {
      return false;
    }
    if (liveSelectionOutside(element)) {
      return false;
    }
    return registry.active.value === target;
  }

  function resolveOffsets(): ParagraphSelection | null {
    const element = options.element.value;
    if (!element) {
      return null;
    }
    const live = selectionOffsets(element);
    if (live) {
      saved = savedFrom(live);
      return live;
    }
    if (liveSelectionOutside(element) || registry.active.value !== target) {
      // The selection belongs to another rich surface (or to nothing this
      // paragraph owns): never apply a stale saved range here.
      return null;
    }
    if (!savedMatchesCurrent()) {
      // The item, entry or text was replaced: the old offsets point at
      // content this paragraph never showed.
      invalidate();
      return null;
    }
    return saved?.offsets ?? null;
  }

  watch(options.ownerKey, () => {
    // The owner changed (another item, entry or paragraph): any saved range
    // belongs to a different surface's text.
    invalidate();
  });

  onMounted(() => {
    document.addEventListener("selectionchange", rememberSelection);
  });

  onBeforeUnmount(() => {
    document.removeEventListener("selectionchange", rememberSelection);
    registry.deactivate(target);
  });

  return {
    resolveOffsets,
    publishMarks,
    restoreSelection,
    activate,
    rememberSelection,
    isCurrentTarget,
    invalidate,
  };
}
