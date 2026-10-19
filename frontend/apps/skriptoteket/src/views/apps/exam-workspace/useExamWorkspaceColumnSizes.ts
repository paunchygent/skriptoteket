/**
 * Exam workspace column sizes state.
 *
 * Domain purpose:
 *   Hold the user's remembered column widths and list-collapsed state for
 *   this workspace visit. The composable reads storage once on setup and
 *   persists every change; it never clamps, because CSS clamps the tracks
 *   for the window and the resize handle passes already-bounded values.
 *
 * Relationships:
 *   - Storage shape and guarding live in `examWorkspaceColumnSizesStorage`;
 *     the later splitter wiring consumes `sizes`, `rootStyle` and the
 *     minimums to render and drag the handles.
 */

import { computed, readonly, ref, type ComputedRef, type DeepReadonly, type Ref } from "vue";

import {
  readExamWorkspaceColumnSizes,
  writeExamWorkspaceColumnSizes,
  type ExamWorkspaceColumnSizes,
} from "./examWorkspaceColumnSizesStorage";

export type ExamWorkspaceColumn = "list" | "drawer" | "preview";

const COLUMN_SIZE_PROPERTY: Record<ExamWorkspaceColumn, string> = {
  list: "--xw-list-size",
  drawer: "--xw-drawer-size",
  preview: "--xw-preview-size",
};

const COLUMNS: readonly ExamWorkspaceColumn[] = ["list", "drawer", "preview"];

export type ExamWorkspaceColumnSizesState = {
  sizes: DeepReadonly<Ref<ExamWorkspaceColumnSizes>>;
  setWidth(column: ExamWorkspaceColumn, px: number): void;
  resetWidth(column: ExamWorkspaceColumn): void;
  listCollapsed: ComputedRef<boolean>;
  toggleListCollapsed(): void;
  rootStyle: ComputedRef<Record<string, string>>;
};

export function useExamWorkspaceColumnSizes(): ExamWorkspaceColumnSizesState {
  const sizes = ref<ExamWorkspaceColumnSizes>(readExamWorkspaceColumnSizes());

  function persist(): void {
    writeExamWorkspaceColumnSizes(sizes.value);
  }

  function setWidth(column: ExamWorkspaceColumn, px: number): void {
    sizes.value = { ...sizes.value, [column]: Math.round(px) };
    persist();
  }

  function resetWidth(column: ExamWorkspaceColumn): void {
    const next: ExamWorkspaceColumnSizes = { ...sizes.value };
    delete next[column];
    sizes.value = next;
    persist();
  }

  const listCollapsed = computed<boolean>(() => sizes.value.listCollapsed ?? false);

  function toggleListCollapsed(): void {
    sizes.value = { ...sizes.value, listCollapsed: !listCollapsed.value };
    persist();
  }

  const rootStyle = computed<Record<string, string>>(() => {
    const style: Record<string, string> = {};
    for (const column of COLUMNS) {
      const width = sizes.value[column];
      if (width !== undefined) {
        style[COLUMN_SIZE_PROPERTY[column]] = `${width}px`;
      }
    }
    return style;
  });

  return {
    sizes: readonly(sizes),
    setWidth,
    resetWidth,
    listCollapsed,
    toggleListCollapsed,
    rootStyle,
  };
}
