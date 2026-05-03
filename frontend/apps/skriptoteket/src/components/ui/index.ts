/**
 * Shared UI primitive barrel for the Skriptoteket SPA.
 *
 * Relationships:
 * - first shared primitive home for PR-0157
 * - allows planner/editor surfaces to consume the same dense-tool contract
 */

export { default as ToggleSwitch } from "./ToggleSwitch.vue";
export { default as UiCollapse } from "./UiCollapse.vue";
export { default as UiDenseActionButton } from "./UiDenseActionButton.vue";
export { default as UiDenseCompoundToggle } from "./UiDenseCompoundToggle.vue";
export { default as UiDenseIconButton } from "./UiDenseIconButton.vue";
export { default as UiDenseMenuButton } from "./UiDenseMenuButton.vue";
export { default as UiDenseSplitButton } from "./UiDenseSplitButton.vue";
export { default as UiDenseStatusPill } from "./UiDenseStatusPill.vue";
export { default as UiDenseSpinner } from "./UiDenseSpinner.vue";
export { default as UiDenseToggle } from "./UiDenseToggle.vue";
export { default as UiMarkdown } from "./UiMarkdown.vue";
export { default as UiSearchBar } from "./UiSearchBar.vue";
export { default as UiSegmentedToggle } from "./UiSegmentedToggle.vue";
export { default as ToastHost } from "./ToastHost.vue";
export { default as SystemMessage } from "./SystemMessage.vue";

export type { UiDenseSplitButtonItem } from "./UiDenseSplitButton.vue";
export type {
  DenseActionGroupPosition,
  DenseActionSize,
  DenseStatusTone,
  DenseActionTone,
} from "./denseToolPrimitives";
export {
  DENSE_ACTION_RADIUS_CLASS,
  DENSE_FORM_INPUT_CLASS,
  DENSE_MENU_PANEL_CLASS,
  DENSE_MENU_SECTION_LABEL_CLASS,
  DENSE_SEGMENTED_SHELL_CLASS,
  denseActionButtonClass,
  denseActionValueClass,
  denseMenuItemClass,
  denseStatusPillClass,
} from "./denseToolPrimitives";
