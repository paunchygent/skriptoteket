/**
 * Shared planner workspace layout contract.
 *
 * This module names the shared planner-shell primitives while CSS remains the
 * single source of truth for their geometry. Guest and authenticated planner
 * surfaces both consume these classes so the workspace frame, rail, and lane
 * contracts are defined once in the shared shell seam.
 */

export const PLANNER_WORKSPACE_SHELL_CLASS = "planner-workspace-shell";
export const PLANNER_WORKSPACE_MODE_SURFACE_CLASS = "planner-workspace-mode-surface";
export const PLANNER_WORKSPACE_TOOLBAR_SHELL_CLASS = "planner-workspace-toolbar-shell";
export const PLANNER_WORKSPACE_PANE_SHELL_CLASS = "planner-workspace-pane-shell";

export const PLANNER_WORKSPACE_SPLIT_ROW_CLASS = "planner-workspace-split-row";
export const PLANNER_STUDENT_POOL_LANE_CLASS = "planner-workspace-pool-lane";
export const PLANNER_WORKSPACE_PRIMARY_LANE_CLASS = "planner-workspace-primary-lane";

export const PLANNER_GROUPING_LAYOUT_ROW_CLASS = "planner-grouping-layout-row";
export const PLANNER_GROUPING_STUDENT_POOL_LANE_CLASS = "planner-workspace-pool-lane planner-grouping-pool-lane";
export const PLANNER_GROUPING_BOARD_LANE_CLASS = "planner-workspace-primary-lane planner-grouping-board-lane";
export const PLANNER_SEATING_LAYOUT_ROW_CLASS = "planner-workspace-split-row planner-seating-layout-row";
export const PLANNER_SEATING_STUDENT_POOL_LANE_CLASS = "planner-workspace-pool-lane planner-seating-pool-lane";
export const PLANNER_SEATING_WORKSPACE_LANE_CLASS = "planner-seating-workspace-lane";
export const PLANNER_STUDENT_POOL_SURFACE_CLASS = "planner-student-pool-surface";
export const PLANNER_GROUP_BOARD_CLASS = "planner-group-board";
export const PLANNER_GROUP_CARD_CLASS = "planner-group-card";
