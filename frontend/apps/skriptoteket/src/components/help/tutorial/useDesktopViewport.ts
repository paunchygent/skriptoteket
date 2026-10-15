/**
 * Desktop viewport detection for the tutorial first-use dialog.
 *
 * Purpose:
 *   Report whether the planner shows its desktop composition, the 1024px
 *   breakpoint in `klassrumskartan-responsive-workspace.css`, as a reactive
 *   boolean. Tests provide `DESKTOP_VIEWPORT_KEY` to force a value.
 *
 * Relationships:
 *   - pattern copied from `views/apps/exam-workspace/useExamWorkspaceLayout.ts`
 *   - read by `useTutorialFirstUse.ts`
 */

import { inject, onScopeDispose, ref } from "vue";
import type { InjectionKey, Ref } from "vue";

export const DESKTOP_VIEWPORT_QUERY = "(min-width: 1024px)";

export const DESKTOP_VIEWPORT_KEY: InjectionKey<Ref<boolean>> = Symbol("desktop-viewport");

export function useDesktopViewport(): Ref<boolean> {
  const provided = inject(DESKTOP_VIEWPORT_KEY, null);
  if (provided) {
    return provided;
  }
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
