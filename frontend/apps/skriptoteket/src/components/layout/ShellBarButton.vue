<script setup lang="ts">
/**
 * Ghost button of the shell top bars.
 *
 * Relationships:
 * - used by `AuthTopBar` and `LandingLayout` for the shell actions (sidebar
 *   toggle, Fokusläge, Hjälp, Logga ut, Meny, Logga in)
 * - renders a link when `href` is given and a button otherwise; extra ARIA
 *   attributes fall through to the rendered element
 * - `glyph` is optional only for a word-only action such as Logga in, which has
 *   no catalogue meaning; such a button keeps its word at every width
 * - `word` is the visible word next to the glyph; `wordFrom="desktop"` hides it
 *   below 1280 px, `wordFrom="never"` makes the button glyph-only at every width.
 *   The accessible name and tooltip are always `label`.
 */

import { UiGlyph, type UiGlyphMeaning } from "../ui";

withDefaults(
  defineProps<{
    glyph?: UiGlyphMeaning;
    label: string;
    word?: string;
    wordFrom?: "always" | "desktop" | "never";
    href?: string;
    pressed?: boolean;
    disabled?: boolean;
  }>(),
  {
    glyph: undefined,
    word: undefined,
    wordFrom: "desktop",
    href: undefined,
    pressed: undefined,
    disabled: false,
  },
);

defineEmits<{
  click: [event: MouseEvent];
}>();
</script>

<template>
  <a
    v-if="href"
    :href="href"
    class="shell-bar-button"
    :class="`shell-bar-button--word-${word ? wordFrom : 'never'}`"
    :aria-label="label"
    :title="label"
  >
    <UiGlyph
      v-if="glyph"
      :meaning="glyph"
      :size="20"
    />
    <span
      v-if="word"
      class="shell-bar-button__word"
    >{{ word }}</span>
  </a>
  <button
    v-else
    type="button"
    class="shell-bar-button"
    :class="`shell-bar-button--word-${word ? wordFrom : 'never'}`"
    :aria-label="label"
    :title="label"
    :aria-pressed="pressed"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <UiGlyph
      v-if="glyph"
      :meaning="glyph"
      :size="20"
    />
    <span
      v-if="word"
      class="shell-bar-button__word"
    >{{ word }}</span>
  </button>
</template>

<style scoped>
/* Touch size (44 px) below 768 px and on coarse pointers; fine size (36 px)
   on fine pointers from 768 px. */
.shell-bar-button {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  gap: var(--huleedu-space-2);
  height: 44px;
  min-width: 44px;
  padding: 0 var(--huleedu-space-3);
  border: 1px solid transparent;
  border-radius: var(--huleedu-radius-md);
  background: transparent;
  color: inherit;
  font-family: var(--huleedu-font-sans);
  font-size: var(--huleedu-text-sm);
  font-weight: var(--huleedu-font-medium);
  line-height: 1;
  white-space: nowrap;
  text-decoration: none;
  cursor: pointer;
  transition:
    background-color var(--huleedu-duration-fast) var(--huleedu-ease-default),
    border-color var(--huleedu-duration-fast) var(--huleedu-ease-default),
    color var(--huleedu-duration-fast) var(--huleedu-ease-default);
}

.shell-bar-button--word-never {
  width: 44px;
  padding: 0;
}

@media (min-width: 768px) and (pointer: fine) {
  .shell-bar-button {
    height: 36px;
    min-width: 36px;
  }

  .shell-bar-button--word-never {
    width: 36px;
  }
}

@media (max-width: 1279px) {
  .shell-bar-button--word-desktop {
    width: 44px;
    padding: 0;
  }

  .shell-bar-button--word-desktop .shell-bar-button__word {
    display: none;
  }
}

@media (min-width: 768px) and (max-width: 1279px) and (pointer: fine) {
  .shell-bar-button--word-desktop {
    width: 36px;
  }
}

.shell-bar-button:focus-visible {
  outline: 2px solid var(--huleedu-action-40);
  outline-offset: 2px;
}

.shell-bar-button[aria-pressed="true"],
.shell-bar-button[aria-expanded="true"] {
  border-color: var(--huleedu-action);
  background: var(--huleedu-action-10);
  color: var(--huleedu-action);
}

.shell-bar-button:disabled {
  color: var(--huleedu-navy-40);
  cursor: not-allowed;
}

@media (hover: hover) {
  .shell-bar-button:not(:disabled):hover {
    background: var(--huleedu-action-05);
  }

  .shell-bar-button[aria-pressed="true"]:not(:disabled):hover,
  .shell-bar-button[aria-expanded="true"]:not(:disabled):hover {
    background: var(--huleedu-action-10);
  }
}
</style>
