/**
 * Exam workspace anchored floating position.
 *
 * Domain purpose:
 *   Keep one floating panel (the gap popover) fully visible next to its
 *   anchor chip: below the chip while there is room, flipped above it when
 *   the space below is smaller than its height, clamped to the viewport
 *   edges and capped to the available viewport height with its own scroll.
 *   The position follows window resizes and scrolls of any ancestor, like
 *   the `ExamWorkspaceMenu` surface, which this mirrors and extends with a
 *   capture-phase scroll listener.
 *
 * Relationships:
 *   - Called by `ExamWorkspaceGapPopover`, which supplies its anchor chip
 *     and its own root and styles itself from the returned position.
 *   - Registers one window `resize` listener and one capture-phase window
 *     `scroll` listener for the lifetime of the calling component; both
 *     are removed before unmount. No positioning library.
 */

import { nextTick, onBeforeUnmount, onMounted, readonly, ref } from "vue";
import type { DeepReadonly, Ref } from "vue";

export const ANCHORED_EDGE_PX = 8;
export const ANCHORED_GAP_PX = 4;

export interface AnchoredPosition {
  top: number;
  left: number;
  maxHeight: number;
  placement: "below" | "above";
}

export function useExamWorkspaceAnchoredPosition(
  anchor: Ref<HTMLElement | null>,
  floating: Ref<HTMLElement | null>,
): { position: DeepReadonly<Ref<AnchoredPosition>>; place: () => void } {
  const position = ref<AnchoredPosition>({ top: 0, left: 0, maxHeight: 0, placement: "below" });

  function place(): void {
    const target = anchor.value;
    const panel = floating.value;
    if (!target || !panel) {
      return;
    }
    const box = target.getBoundingClientRect();
    const height = panel.scrollHeight;
    const width = panel.offsetWidth;
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;
    const spaceBelow = viewportHeight - box.bottom - ANCHORED_GAP_PX - ANCHORED_EDGE_PX;
    const spaceAbove = box.top - ANCHORED_GAP_PX - ANCHORED_EDGE_PX;
    const placement: AnchoredPosition["placement"] =
      height <= spaceBelow || spaceBelow >= spaceAbove ? "below" : "above";
    const maxHeight = Math.max(0, placement === "below" ? spaceBelow : spaceAbove);
    const shown = Math.min(height, maxHeight);
    const top = placement === "below" ? box.bottom + ANCHORED_GAP_PX : box.top - ANCHORED_GAP_PX - shown;
    const maxLeft = viewportWidth - width - ANCHORED_EDGE_PX;
    const left = maxLeft < ANCHORED_EDGE_PX ? ANCHORED_EDGE_PX : Math.min(Math.max(box.left, ANCHORED_EDGE_PX), maxLeft);
    position.value = { top, left, maxHeight, placement };
  }

  onMounted(async () => {
    await nextTick();
    place();
    window.addEventListener("resize", place);
    // Capture phase: an ancestor's scroll reaches window even though the
    // event itself does not bubble.
    window.addEventListener("scroll", place, { capture: true, passive: true });
  });

  onBeforeUnmount(() => {
    window.removeEventListener("resize", place);
    window.removeEventListener("scroll", place, true);
  });

  return { position: readonly(position), place };
}
