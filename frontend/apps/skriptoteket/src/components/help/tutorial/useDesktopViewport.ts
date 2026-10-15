/**
 * Desktop viewport detection for the tutorial first-use dialog.
 *
 * Purpose:
 *   Report whether the planner shows its desktop composition, the 1024px
 *   breakpoint in `klassrumskartan-responsive-workspace.css`, as a reactive
 *   boolean read from `window.matchMedia`.
 *
 * Relationships:
 *   - pattern copied from `views/apps/exam-workspace/useExamWorkspaceLayout.ts`
 *   - read by `useTutorialFirstUse.ts`
 */

import { onScopeDispose, ref } from "vue";
import type { Ref } from "vue";

const DESKTOP_VIEWPORT_QUERY = "(min-width: 1024px)";

export function useDesktopViewport(): Ref<boolean> {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return ref(false);
  }
  const query = window.matchMedia(DESKTOP_VIEWPORT_QUERY);
  const isDesktop = ref(query.matches);
  const update = (): void => {
    isDesktop.value = query.matches;
  };
  query.addEventListener("change", update);
  onScopeDispose(() => {
    query.removeEventListener("change", update);
  });
  return isDesktop;
}
