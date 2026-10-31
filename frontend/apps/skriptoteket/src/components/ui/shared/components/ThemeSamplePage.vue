<script setup lang="ts">
/**
 * Purpose:
 *     Render the full cross-site theme sample page.
 *
 * Relationships:
 *     - Composes the four sample sections: both top bars with the live theme
 *       selector, the component controls, the workspace surfaces and the share
 *       page.
 *     - Takes the same required ThemePreferenceStore prop as UiThemeSelector
 *       plus the raw Skriptoteket logo markup that the top bars inline, so a
 *       consumer builds both from its own theme module and `?raw` import.
 *     - Wraps the store it passes down around one page-level choice ref:
 *       read() returns that ref, store() refreshes it after the underlying
 *       store succeeds, and the status line shows the same ref. Both mounted
 *       selectors and the status line therefore display one choice.
 *     - Copies the task 1 companion-link rule: the page links to the other
 *       site's /theme-sample, using the primary hostname from any other host.
 *     - Sets the page shell from tokens in scoped styles. The unscoped
 *       document rule matches only while the page root is mounted, so
 *       importing the page through the shared barrel cannot restyle an
 *       ordinary consumer document.
 */

import { computed, ref } from "vue";

import type {
  ThemeChoice,
  ThemePreferenceStore,
} from "./UiThemeSelector.vue";
import ThemeSampleControls from "./ThemeSampleControls.vue";
import ThemeSampleShare from "./ThemeSampleShare.vue";
import ThemeSampleTopBars from "./ThemeSampleTopBars.vue";
import ThemeSampleWorkspaces from "./ThemeSampleWorkspaces.vue";

const PRIMARY_HOSTNAME = "hule.education";
const COMPANION_HOSTNAME = "skriptoteket.hule.education";
const THEME_SAMPLE_PATH = "/theme-sample";

const THEME_LABELS: readonly { choice: ThemeChoice; label: string }[] = [
  { choice: "light", label: "Ljust" },
  { choice: "midnight", label: "Midnatt" },
  { choice: "dark", label: "Bläck" },
  { choice: "system", label: "Följ enheten" },
];

const props = defineProps<{
  themePreference: ThemePreferenceStore;
  /** Raw SVG markup of the package's `./skriptoteket-logo-horizontal.svg`. */
  skriptoteketLogoSvg: string;
}>();

const storedChoice = ref<ThemeChoice>(props.themePreference.read());

const wrappedThemePreference: ThemePreferenceStore = {
  read: () => storedChoice.value,
  apply: (choice) => {
    props.themePreference.apply(choice);
  },
  store: (choice) => {
    props.themePreference.store(choice);
    storedChoice.value = choice;
  },
};

const storedLabel = computed(
  () =>
    THEME_LABELS.find((option) => option.choice === storedChoice.value)?.label ?? "Följ enheten",
);

const hostname = window.location.hostname;

const companionSampleUrl = computed(() => {
  const host = hostname === PRIMARY_HOSTNAME ? COMPANION_HOSTNAME : PRIMARY_HOSTNAME;
  return `https://${host}${THEME_SAMPLE_PATH}`;
});
</script>

<template>
  <div
    class="theme-sample-page"
    data-ui="theme-sample-page"
  >
    <div class="theme-sample-page__inner">
      <header class="theme-sample-page__header">
        <h1 class="theme-sample-page__title">
          Tema
        </h1>
        <p class="theme-sample-page__status">
          Lagrat val: {{ storedLabel }}. Värd: {{ hostname }}
        </p>
        <a
          class="theme-sample-page__link"
          :href="companionSampleUrl"
        >Öppna {{ companionSampleUrl }}</a>
      </header>

      <ThemeSampleTopBars
        :theme-preference="wrappedThemePreference"
        :skriptoteket-logo-svg="skriptoteketLogoSvg"
      />
      <ThemeSampleControls />
      <ThemeSampleWorkspaces />
      <ThemeSampleShare />
    </div>
  </div>
</template>

<style scoped>
.theme-sample-page {
  box-sizing: border-box;
  min-height: 100vh;
  padding: var(--huleedu-space-6);
  background: var(--huleedu-paper);
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-sans);
  line-height: var(--huleedu-type-body-leading);
}

.theme-sample-page__inner {
  display: grid;
  gap: var(--huleedu-space-8);
  max-width: var(--huleedu-max-width-6xl);
  margin-inline: auto;
  min-width: 0;
}

.theme-sample-page__header {
  display: grid;
  gap: var(--huleedu-space-2);
  min-width: 0;
}

.theme-sample-page__title {
  margin: 0;
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-page-title);
  font-size: var(--huleedu-type-page-title-size);
  font-weight: var(--huleedu-type-page-title-weight);
  line-height: var(--huleedu-type-title-leading);
}

.theme-sample-page__status {
  margin: 0;
  color: var(--huleedu-navy-70);
  font-family: var(--huleedu-font-sans);
  font-size: var(--huleedu-type-helper-size);
  font-weight: var(--huleedu-type-helper-weight);
  line-height: var(--huleedu-type-body-leading);
}

.theme-sample-page__link {
  justify-self: start;
  color: var(--huleedu-link-color);
  font-family: var(--huleedu-font-sans);
  font-weight: var(--huleedu-link-weight);
  text-underline-offset: var(--huleedu-link-underline-offset);
}
</style>

<!-- Unscoped on purpose, because the page fills the document box: both rules
     match only while the page root carries data-ui="theme-sample-page", so
     the shared barrel's import of this file restyles no other document. -->
<style>
html:has([data-ui="theme-sample-page"]),
body:has([data-ui="theme-sample-page"]) {
  margin: 0;
  background: var(--huleedu-paper);
  color: var(--huleedu-navy);
}
</style>
