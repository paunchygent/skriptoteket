<script setup lang="ts">
/**
 * Shared planner workspace mode surface.
 *
 * This component wraps the detached sticky toolbar and scrollable pane used by
 * both grouping and seating so authenticated and guest shells inherit one
 * viewport-relative layout contract.
 */

import {
  PLANNER_WORKSPACE_MODE_SURFACE_CLASS,
  PLANNER_WORKSPACE_PANE_SHELL_CLASS,
  PLANNER_WORKSPACE_TOOLBAR_SHELL_CLASS,
} from "../plannerWorkspaceLayout";

defineProps<{
  view: "groups" | "seats";
}>();
</script>

<template>
  <div :class="PLANNER_WORKSPACE_MODE_SURFACE_CLASS">
    <div
      :class="PLANNER_WORKSPACE_TOOLBAR_SHELL_CLASS"
      data-ui="planner-workspace-toolbar-shell"
      :data-view="view"
    >
      <slot name="toolbar" />
    </div>

    <slot name="after-toolbar" />

    <div
      :class="PLANNER_WORKSPACE_PANE_SHELL_CLASS"
      data-ui="planner-workspace-pane-shell"
      :data-view="view"
    >
      <slot />
    </div>
  </div>
</template>
