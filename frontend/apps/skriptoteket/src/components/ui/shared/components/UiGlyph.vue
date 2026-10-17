<script setup lang="ts">
/**
 * Purpose:
 *     Render one shared semantic glyph for a closed set of meanings.
 *
 * Relationships:
 *     - Resolves meanings through uiGlyphs.ts; each meaning has exactly one glyph.
 *     - Decorative by default; the owning control provides the accessible name.
 *       Pass `label` only when the glyph itself is the accessible content.
 *     - UiSymbol delegates here for its legacy names.
 */

import { computed } from "vue";

import { UI_GLYPHS } from "../uiGlyphs";
import type { UiGlyphMeaning } from "../uiGlyphs";

const props = withDefaults(
  defineProps<{
    meaning: UiGlyphMeaning;
    size?: number;
    strokeWidth?: number | string;
    label?: string;
  }>(),
  {
    size: 24,
    strokeWidth: 2,
    label: undefined,
  },
);

const source = computed(() => UI_GLYPHS[props.meaning]);
const accessibility = computed(() =>
  props.label
    ? { role: "img", "aria-label": props.label, "aria-hidden": undefined }
    : { role: undefined, "aria-label": undefined, "aria-hidden": "true" as const },
);
</script>

<template>
  <component
    :is="source.icon"
    v-if="source.kind === 'lucide'"
    :size="size"
    :stroke-width="strokeWidth"
    focusable="false"
    v-bind="accessibility"
  />
  <svg
    v-else
    xmlns="http://www.w3.org/2000/svg"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    focusable="false"
    v-bind="accessibility"
  >
    <rect
      v-for="rect in source.geometry.rects"
      :key="`${rect.x}-${rect.y}-${rect.width}-${rect.height}`"
      :x="rect.x"
      :y="rect.y"
      :width="rect.width"
      :height="rect.height"
      :rx="rect.rx"
    />
    <path v-for="path in source.geometry.paths" :key="path" :d="path" />
  </svg>
</template>
