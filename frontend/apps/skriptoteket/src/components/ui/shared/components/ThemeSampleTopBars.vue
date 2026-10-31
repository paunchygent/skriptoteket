<script setup lang="ts">
/**
 * Purpose:
 *     Show the HuleEdu and Skriptoteket top bars with the live theme selector.
 *
 * Relationships:
 *     - Composed by ThemeSamplePage as the first of its four sample sections.
 *     - Takes the same ThemePreferenceStore prop as UiThemeSelector, so a
 *       choice made in either bar applies at once through the shared store.
 *     - Draws no copy of the selector's menu. The live popup is the section's
 *       only menu: a static picture of it under the live control read as a
 *       menu that did nothing when the real one opened over it. The section
 *       keeps shared-token space below the bars instead, because the popup
 *       opens downward over the following sample section.
 *     - Renders the HuleEdu wordmark with the brand.css class and the real
 *       Skriptoteket logo inlined from `skriptoteketLogoSvg`, the raw markup of
 *       the package's `./skriptoteket-logo-horizontal.svg`. Consumers import
 *       that asset with `?raw`, so the logo's wordmark tokens recolour it in
 *       each theme, as BrandLogo.vue does in the app. The logo sits at the
 *       app's own top-bar size (`--huleedu-space-10`) inside its 44 px brand
 *       slot. Skriptoteket's design-system map does not adopt brand.css, so
 *       the HuleEdu wordmark role is restated from the same tokens in scoped
 *       styles; every other colour, space, type role and radius is a shared
 *       token too.
 *     - Draws no app label; the real bar adds one only for its exam-workspace
 *       route.
 *     - The phone band keeps each identity and its selector and drops the nav
 *       items, so both bars fit 375 px without horizontal scroll.
 */

import { computed } from "vue";

import UiThemeSelector, { type ThemePreferenceStore } from "./UiThemeSelector.vue";

const props = defineProps<{
  themePreference: ThemePreferenceStore;
  /** Raw SVG markup of the package's `./skriptoteket-logo-horizontal.svg`. */
  skriptoteketLogoSvg: string;
}>();

/** The wrapper owns the accessible name, so the artwork stays decorative. */
const skriptoteketLogoMarkup = computed(() =>
  props.skriptoteketLogoSvg.replace("<svg", '<svg aria-hidden="true" focusable="false"'),
);
</script>

<template>
  <section
    class="theme-sample-top-bars"
    aria-labelledby="theme-sample-top-bars-heading"
  >
    <div class="theme-sample-top-bars__heading">
      <h2
        id="theme-sample-top-bars-heading"
        class="theme-sample-top-bars__title"
      >
        Toppfält
      </h2>
      <span class="theme-sample-top-bars__proposal">Förslag</span>
    </div>

    <div class="theme-sample-top-bars__bars">
      <div
        class="theme-sample-top-bars__bar theme-sample-top-bars__bar--huleedu"
        role="group"
        aria-label="HuleEdu toppfält"
      >
        <span class="huleedu-wordmark theme-sample-top-bars__wordmark">HuleEdu.</span>
        <div class="theme-sample-top-bars__nav">
          <span>Översikt</span>
          <span>Klasser</span>
        </div>
        <div class="theme-sample-top-bars__selector">
          <UiThemeSelector :theme-preference="themePreference" />
        </div>
      </div>

      <div
        class="theme-sample-top-bars__bar theme-sample-top-bars__bar--skriptoteket"
        role="group"
        aria-label="Skriptoteket toppfält"
      >
        <span class="theme-sample-top-bars__skriptoteket-brand">
          <!-- eslint-disable vue/no-v-html -- the markup is the build-time synced asset, not user input -->
          <span
            class="theme-sample-top-bars__skriptoteket-logo"
            role="img"
            aria-label="Skriptoteket"
            v-html="skriptoteketLogoMarkup"
          />
          <!-- eslint-enable vue/no-v-html -->
        </span>
        <div class="theme-sample-top-bars__nav">
          <span>Katalog</span>
          <span>Mina filer</span>
        </div>
        <div class="theme-sample-top-bars__selector">
          <UiThemeSelector :theme-preference="themePreference" />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.theme-sample-top-bars {
  display: grid;
  gap: var(--huleedu-space-3);
  min-width: 0;
  /* The live selector's popup opens downward out of either bar: four choice
     rows at --huleedu-action-control-height plus its panel padding, row gaps
     and offset. The section keeps that room below the bars from the spacing
     tokens, not as an empty reserved block, so an open popup ends above the
     next section's heading instead of covering it. */
  margin-block-end: calc(4 * var(--huleedu-action-control-height) + var(--huleedu-space-6));
}

.theme-sample-top-bars__heading {
  display: flex;
  align-items: center;
  gap: var(--huleedu-space-2);
  min-width: 0;
}

.theme-sample-top-bars__title {
  margin: 0;
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-sans);
  font-size: var(--huleedu-type-section-title-size);
  font-weight: var(--huleedu-type-section-title-weight);
  line-height: var(--huleedu-type-title-leading);
}

/* The approved preview marks a proposed element with the terracotta tag. */
.theme-sample-top-bars__proposal {
  padding: 0 var(--huleedu-space-2);
  border: var(--huleedu-border-width) solid var(--huleedu-terracotta);
  border-radius: var(--huleedu-radius-full);
  background: var(--huleedu-terracotta-10);
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-sans);
  font-size: var(--huleedu-type-helper-size);
  font-weight: var(--huleedu-font-medium);
  line-height: var(--huleedu-leading-snug);
  white-space: nowrap;
}

.theme-sample-top-bars__bars {
  display: grid;
  gap: var(--huleedu-space-4);
  min-width: 0;
}

.theme-sample-top-bars__bar {
  display: flex;
  align-items: center;
  gap: var(--huleedu-space-6);
  min-width: 0;
  height: var(--huleedu-header-height);
  padding: 0 var(--huleedu-space-4);
  background: var(--huleedu-canvas);
  color: var(--huleedu-navy);
}

/* The preview draws the HuleEdu bar with the navy chrome border and the
   Skriptoteket bar with the shared surface-divider hairline. */
.theme-sample-top-bars__bar--huleedu {
  border: var(--huleedu-border-width) solid var(--huleedu-navy);
}

.theme-sample-top-bars__bar--skriptoteket {
  border: var(--huleedu-border-width) solid var(--huleedu-surface-divider);
}

/* Restates brand.css's .huleedu-wordmark from the same tokens, because
   Skriptoteket does not adopt brand.css and the sample page also serves its
   `/theme-sample` route. The class stays on the element for HuleEdu. */
.theme-sample-top-bars__wordmark {
  flex: none;
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-serif);
  font-size: var(--huleedu-text-2xl);
  font-weight: var(--huleedu-font-bold);
  letter-spacing: var(--huleedu-tracking-normal);
  line-height: var(--huleedu-leading-none);
  white-space: nowrap;
}

/* Mirrors the Skriptoteket app's brand link: a 40 px logo in a 44 px slot. */
.theme-sample-top-bars__skriptoteket-brand {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: var(--huleedu-space-1-5);
  min-height: var(--huleedu-action-control-height);
  white-space: nowrap;
}

/* Mirrors BrandLogo.vue at the top bar's 40 px logo height; the inlined
   artwork's wordmark tokens recolour it in each theme. */
.theme-sample-top-bars__skriptoteket-logo {
  display: block;
  flex: none;
  height: var(--huleedu-space-10);
}

.theme-sample-top-bars__skriptoteket-logo :deep(svg) {
  display: block;
  width: auto;
  height: 100%;
}

.theme-sample-top-bars__nav {
  display: flex;
  align-items: center;
  gap: var(--huleedu-space-4);
  min-width: 0;
  color: var(--huleedu-navy-70);
  font-family: var(--huleedu-font-sans);
  font-size: var(--huleedu-type-control-value-size);
  font-weight: var(--huleedu-type-control-value-weight);
  line-height: var(--huleedu-leading-snug);
  white-space: nowrap;
}

.theme-sample-top-bars__selector {
  display: inline-flex;
  flex: none;
  margin-inline-start: auto;
}

@media (max-width: 767px) {
  .theme-sample-top-bars__bar {
    gap: var(--huleedu-space-2);
    padding: 0 var(--huleedu-space-2);
  }

  .theme-sample-top-bars__nav {
    display: none;
  }
}
</style>
