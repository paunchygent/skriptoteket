/**
 * Shared planner workspace layout contract.
 *
 * This module freezes the detached-toolbar shell classes and the PR-0226
 * grouping-height floors so guest and authenticated planner surfaces inherit
 * the same viewport-relative behavior and the same reviewable desktop layout
 * contract.
 */

export const PLANNER_WORKSPACE_MODE_SURFACE_CLASS = "flex flex-col gap-4 xl:min-h-0 xl:flex-1";
export const PLANNER_WORKSPACE_TOOLBAR_SHELL_CLASS = "sticky top-0 z-20";
export const PLANNER_WORKSPACE_PANE_SHELL_CLASS = "xl:min-h-0 xl:max-h-full xl:overflow-y-auto";

export const PLANNER_GROUPING_LAYOUT_ROW_CLASS = "flex flex-col gap-3 xl:min-h-[480px] xl:flex-row xl:items-stretch";
export const PLANNER_GROUPING_STUDENT_POOL_LANE_CLASS = "xl:flex xl:min-h-[480px] xl:w-[240px] xl:flex-none xl:self-stretch xl:[contain:size]";
export const PLANNER_GROUPING_BOARD_LANE_CLASS = "min-w-0 flex-1 xl:min-h-[480px]";
export const PLANNER_GROUP_BOARD_CLASS = "grid items-start content-start gap-3 md:grid-cols-2 xl:min-h-[480px] xl:auto-rows-[minmax(234px,auto)] xl:items-stretch 2xl:grid-cols-3";
