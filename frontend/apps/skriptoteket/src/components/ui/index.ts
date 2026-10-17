/**
 * UI barrel for the Skriptoteket SPA.
 *
 * Relationships:
 * - re-exports the synced huleedu-integrated Vue runtime from `./shared`
 * - adds the Skriptoteket-only components that the shared package does not ship
 */

export * from "./shared";

export { default as ToggleSwitch } from "./ToggleSwitch.vue";
export { default as UiCollapse } from "./UiCollapse.vue";
export { default as UiDenseCompoundToggle } from "./UiDenseCompoundToggle.vue";
export { default as UiDenseMenuButton } from "./UiDenseMenuButton.vue";
export { default as UiDenseSplitButton } from "./UiDenseSplitButton.vue";
export { default as UiDenseToggle } from "./UiDenseToggle.vue";
export { default as UiMarkdown } from "./UiMarkdown.vue";
export { default as UiSearchBar } from "./UiSearchBar.vue";
export { default as UiSegmentedTileToggle } from "./UiSegmentedTileToggle.vue";
export { default as SkriptoteketToastHost } from "./SkriptoteketToastHost.vue";

export type { UiDenseSplitButtonItem } from "./UiDenseSplitButton.vue";
export type { UiSegmentedTileToggleOption } from "./UiSegmentedTileToggle.vue";
