/**
 * Exam workspace column layout wiring.
 *
 * Domain purpose:
 *   Own the view's desktop column wiring (TASK-SKRIPT-41-02-04): the
 *   remembered widths as the root's inline custom properties and the list
 *   state as `data-list`, carried only on desktop. A first width set on the
 *   collapsed list's draggable edge widens and expands it.
 *
 * Relationships:
 *   - Wraps `useExamWorkspaceColumnSizes` (stored widths and collapse flag);
 *     the view binds the returned style, list state and handlers.
 *   - Consumed by `ExamWorkspaceView` with the layout from
 *     `useExamWorkspaceLayout`.
 */

import { computed, type ComputedRef, type Ref } from "vue";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { useExamWorkspaceColumnSizes, type ExamWorkspaceColumn } from "./useExamWorkspaceColumnSizes";
import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";
import type { ExamWorkspaceSideDrawer } from "./useExamWorkspaceSideColumns";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";

export type ExamWorkspaceSideState = ExamWorkspaceSideDrawer | "preview" | "none";

export type ExamWorkspaceColumnSideDeps = {
  drawer: Ref<ExamWorkspaceSideDrawer | null>;
  previewOpen: Ref<boolean>;
  workspaceDocument: Ref<NativeExamDocument | null>;
  isPhone: Ref<boolean>;
  store: ExamWorkspaceStore;
};

export type ExamWorkspaceColumnLayoutState = {
  isDesktop: ComputedRef<boolean>;
  side: ComputedRef<ExamWorkspaceSideState>;
  rootColumnStyle: ComputedRef<Record<string, string> | undefined>;
  rootListState: ComputedRef<"collapsed" | "open" | undefined>;
  listRailCollapsed: ComputedRef<boolean>;
  setListWidth(px: number): void;
  setWidth(column: ExamWorkspaceColumn, px: number): void;
  resetWidth(column: ExamWorkspaceColumn): void;
  toggleListCollapsed(): void;
};

export function useExamWorkspaceColumnLayout(
  layout: Ref<ExamWorkspaceLayout>,
  sideDeps?: ExamWorkspaceColumnSideDeps,
): ExamWorkspaceColumnLayoutState {
  const columnSizes = useExamWorkspaceColumnSizes();
  const isDesktop = computed(() => layout.value === "desktop");
  /**
   * The width owner's side state (TASK-SKRIPT-41-02-04): the open drawer wins,
   * else the rendered print preview, else no side column. The `.ws__body` grid
   * keys one rule per state off `data-side`.
   */
  const side = computed<ExamWorkspaceSideState>(() => {
    if (!sideDeps) return "none";
    if (sideDeps.drawer.value !== null) {
      return sideDeps.drawer.value;
    }
    if (
      sideDeps.previewOpen.value &&
      sideDeps.workspaceDocument.value !== null &&
      !sideDeps.isPhone.value &&
      sideDeps.store.teacher !== null
    ) {
      return "preview";
    }
    return "none";
  });
  const rootColumnStyle = computed<Record<string, string> | undefined>(() =>
    isDesktop.value ? columnSizes.rootStyle.value : undefined,
  );
  const rootListState = computed<"collapsed" | "open" | undefined>(() => {
    if (!isDesktop.value) return undefined;
    return columnSizes.listCollapsed.value ? "collapsed" : "open";
  });
  const listRailCollapsed = computed(() => isDesktop.value && columnSizes.listCollapsed.value);

  function setListWidth(px: number): void {
    columnSizes.setWidth("list", px);
    if (columnSizes.listCollapsed.value) {
      columnSizes.toggleListCollapsed();
    }
  }

  function setWidth(column: ExamWorkspaceColumn, px: number): void {
    columnSizes.setWidth(column, px);
  }

  function resetWidth(column: ExamWorkspaceColumn): void {
    columnSizes.resetWidth(column);
  }

  function toggleListCollapsed(): void {
    columnSizes.toggleListCollapsed();
  }

  return {
    isDesktop,
    listRailCollapsed,
    resetWidth,
    rootColumnStyle,
    rootListState,
    setListWidth,
    setWidth,
    side,
    toggleListCollapsed,
  };
}
