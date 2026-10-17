/**
 * Purpose:
 *     Export shared Vue design-system primitives for integrated repos.
 *
 * Relationships:
 *     - Barrel export listed in the resource manifest.
 *     - Consumer repos may import this module or sync individual manifest files.
 */

export { default as SystemMessage } from "./components/SystemMessage.vue";
export type { SystemMessageTone } from "./components/SystemMessage.vue";
export { default as ToastHost } from "./components/ToastHost.vue";
export type { ToastItem, ToastPlacement, ToastVariant } from "./components/ToastHost.vue";
export { default as UiDenseActionButton } from "./components/UiDenseActionButton.vue";
export { default as UiDenseIconButton } from "./components/UiDenseIconButton.vue";
export { default as UiDenseSpinner } from "./components/UiDenseSpinner.vue";
export { default as UiDenseStatusPill } from "./components/UiDenseStatusPill.vue";
export { default as UiSegmentedToggle } from "./components/UiSegmentedToggle.vue";
export { default as UiGlyph } from "./components/UiGlyph.vue";
export { default as UiSymbol } from "./components/UiSymbol.vue";
export { UI_GLYPHS } from "./uiGlyphs";
export type {
  UiGlyphActionMeaning,
  UiGlyphEditorToolbarMeaning,
  UiGlyphMeaning,
  UiGlyphNavigationMeaning,
  UiGlyphSource,
  UiGlyphUtilityMeaning,
} from "./uiGlyphs";
export type { UiSegmentedToggleOption } from "./components/UiSegmentedToggle.vue";
export type {
  DenseActionGroupPosition,
  DenseActionSize,
  DenseActionTone,
  DenseStatusTone,
} from "./denseToolPrimitives";
export {
  DENSE_ACTION_RADIUS_CLASS,
  DENSE_COMPACT_SEGMENT_HEIGHT_CLASS,
  DENSE_FORM_INPUT_CLASS,
  DENSE_ICON_SIZE_CLASS,
  DENSE_MENU_PANEL_CLASS,
  DENSE_MENU_SECTION_LABEL_CLASS,
  DENSE_MODAL_SURFACE_CLASS,
  DENSE_PANEL_MUTED_SURFACE_CLASS,
  DENSE_PANEL_SURFACE_CLASS,
  DENSE_SEGMENTED_SHELL_CLASS,
  DENSE_TEXT_HEIGHT_CLASS,
  denseActionButtonClass,
  denseActionValueClass,
  denseMenuItemClass,
  denseStatusPillClass,
} from "./denseToolPrimitives";
