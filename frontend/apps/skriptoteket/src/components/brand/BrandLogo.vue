<script setup lang="ts">
/**
 * The shared Skriptoteket wordmark, drawn inline so the wordmark tokens colour it.
 *
 * Relationships:
 * - `public/logo-horizontal.svg` is the one synced logo file (the
 *   huleedu-integrated `skriptoteket-logo-horizontal` export); it arrives here
 *   as text, so the artwork's paths never live in this component
 * - the SVG fills read `--huleedu-wordmark-primary` and
 *   `--huleedu-wordmark-accent`, so a surface recolours the logo by overriding
 *   those two tokens
 * - `AuthTopBar` wraps it in the home link and `AuthLoginView` shows it
 *   unlinked, so the artwork sets no cursor of its own
 */

import logoArtwork from "/logo-horizontal.svg?raw";

const props = withDefaults(
  defineProps<{
    /** Visible height, normally a spacing token such as `var(--huleedu-space-10)`. */
    height?: string;
  }>(),
  { height: "32px" },
);

/** The wrapper owns the accessible name, so the artwork itself stays decorative. */
const logoMarkup = logoArtwork.replace("<svg", '<svg aria-hidden="true" focusable="false"');
</script>

<template>
  <!-- eslint-disable vue/no-v-html -- the markup is the build-time synced asset, not user input -->
  <span
    class="brand-logo"
    role="img"
    aria-label="Skriptoteket"
    :style="{ height: props.height }"
    v-html="logoMarkup"
  />
  <!-- eslint-enable vue/no-v-html -->
</template>

<style scoped>
.brand-logo {
  display: block;
  flex: none;
}

.brand-logo :deep(svg) {
  display: block;
  width: auto;
  height: 100%;
}
</style>
