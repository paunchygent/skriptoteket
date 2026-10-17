<script setup lang="ts">
/**
 * Purpose:
 *     Keep the legacy UiSymbol names working as a thin delegate to UiGlyph.
 *
 * Relationships:
 *     - Maps each legacy name to one UiGlyph meaning; UiGlyph owns all geometry.
 *     - Decorative; controls own their accessible names and behavior.
 */

import UiGlyph from "./UiGlyph.vue";
import type { UiGlyphMeaning } from "../uiGlyphs";

type UiSymbolName =
  | "exit"
  | "language"
  | "menu"
  | "back"
  | "close"
  | "previous"
  | "next"
  | "remove"
  | "edit";

defineProps<{ name: UiSymbolName }>();

const meaningBySymbol: Record<UiSymbolName, UiGlyphMeaning> = {
  exit: "log-out",
  language: "interface-language",
  menu: "account-menu",
  back: "back",
  close: "close",
  previous: "previous",
  next: "next",
  remove: "remove-rater",
  edit: "edit",
};
</script>

<template>
  <UiGlyph :meaning="meaningBySymbol[name]" />
</template>
