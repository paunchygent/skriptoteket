/**
 * Exam workspace layout selection.
 *
 * Domain purpose:
 *   Choose the desktop, tablet, or phone composition of the exam workspace
 *   from the ADR-SKRIPT-0020 breakpoints (768px and 1024px), as data the
 *   view renders from, so tests select a layout without media queries.
 *
 * Relationships:
 *   - Consumed by `ExamWorkspaceView`.
 *   - Tests provide `EXAM_WORKSPACE_LAYOUT_KEY` to force a layout.
 */

import { inject, onScopeDispose, ref } from "vue";
import type { InjectionKey, Ref } from "vue";

export type ExamWorkspaceLayout = "desktop" | "tablet" | "phone";

export const EXAM_WORKSPACE_LAYOUT_KEY: InjectionKey<Ref<ExamWorkspaceLayout>> =
  Symbol("exam-workspace-layout");

const DESKTOP_QUERY = "(min-width: 1024px)";
const TABLET_QUERY = "(min-width: 768px)";

export function resolveExamWorkspaceLayout(
  matchesDesktop: boolean,
  matchesTablet: boolean,
): ExamWorkspaceLayout {
  if (matchesDesktop) {
    return "desktop";
  }
  return matchesTablet ? "tablet" : "phone";
}

export function useExamWorkspaceLayout(): Ref<ExamWorkspaceLayout> {
  const provided = inject(EXAM_WORKSPACE_LAYOUT_KEY, null);
  if (provided) {
    return provided;
  }
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return ref("desktop");
  }
  const desktop = window.matchMedia(DESKTOP_QUERY);
  const tablet = window.matchMedia(TABLET_QUERY);
  const layout = ref<ExamWorkspaceLayout>(
    resolveExamWorkspaceLayout(desktop.matches, tablet.matches),
  );
  const update = (): void => {
    layout.value = resolveExamWorkspaceLayout(desktop.matches, tablet.matches);
  };
  desktop.addEventListener("change", update);
  tablet.addEventListener("change", update);
  onScopeDispose(() => {
    desktop.removeEventListener("change", update);
    tablet.removeEventListener("change", update);
  });
  return layout;
}
