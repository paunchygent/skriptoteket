<script setup lang="ts">
/**
 * Purpose:
 *     Render the sample share page section of the full theme sample page.
 *
 * Relationships:
 *     - Composed by ThemeSamplePage.vue after the workspace section.
 *     - Takes no props: the section shows one fixed example link and copies it
 *       through navigator.clipboard when the browser provides that API.
 *     - Takes colours, spacing, type, radii, the page grid and the panel
 *       shadow from shared tokens in scoped styles; the primary call to action
 *       uses the shared action-buttons.css class.
 */

import { computed, ref } from "vue";

const SHARE_LINK = "https://skriptoteket.hule.education/d/abc123";
const LINK_INPUT_ID = "theme-sample-share-link";

type CopyState = "idle" | "copied" | "failed";

const copyState = ref<CopyState>("idle");

const copyLabel = computed(() => {
  switch (copyState.value) {
    case "copied":
      return "Kopierad";
    case "failed":
      return "Kunde inte kopiera";
    default:
      return "";
  }
});

const copyFailed = computed(() => copyState.value === "failed");

async function copyLink(): Promise<void> {
  const clipboard = globalThis.navigator?.clipboard;
  if (clipboard === undefined) {
    copyState.value = "failed";
    return;
  }
  try {
    await clipboard.writeText(SHARE_LINK);
    copyState.value = "copied";
  } catch {
    copyState.value = "failed";
  }
}
</script>

<template>
  <section class="theme-sample-share">
    <h2 class="theme-sample-share__heading">Delningssida</h2>
    <div class="theme-sample-share__stage">
      <div class="theme-sample-share__panel">
        <h3 class="theme-sample-share__title">Delat verktyg</h3>
        <p class="theme-sample-share__text">Läraren har delat det här verktyget med dig.</p>
        <div class="theme-sample-share__field">
          <label
            class="theme-sample-share__label"
            :for="LINK_INPUT_ID"
          >
            Länk
          </label>
          <input
            :id="LINK_INPUT_ID"
            class="theme-sample-share__input"
            :value="SHARE_LINK"
            readonly
          />
        </div>
        <div class="theme-sample-share__actions">
          <button
            type="button"
            class="btn-primary"
            @click="copyLink"
          >
            Kopiera länk
          </button>
          <p
            class="theme-sample-share__status"
            :class="{ 'theme-sample-share__status--failed': copyFailed }"
            role="status"
          >
            {{ copyLabel }}
          </p>
        </div>
        <p class="theme-sample-share__footer">Länken slutar fungera när läraren tar bort delningen.</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.theme-sample-share {
  display: grid;
  gap: var(--huleedu-space-3);
}

.theme-sample-share__heading {
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-type-section-title-size);
  font-weight: var(--huleedu-type-section-title-weight);
  line-height: var(--huleedu-type-title-leading);
  margin: 0;
}

/* The page grid: one hairline per grid step on each axis, in the shared
   navy tone at the shared grid-line opacity, over the paper canvas. */
.theme-sample-share__stage {
  --theme-sample-grid-line: color-mix(
    in srgb,
    var(--huleedu-navy) calc(var(--huleedu-grid-line-opacity) * 100%),
    transparent
  );

  background-color: var(--huleedu-paper);
  background-image:
    repeating-linear-gradient(
      to right,
      var(--theme-sample-grid-line) 0 var(--huleedu-border-width),
      transparent var(--huleedu-border-width) var(--huleedu-grid-size)
    ),
    repeating-linear-gradient(
      to bottom,
      var(--theme-sample-grid-line) 0 var(--huleedu-border-width),
      transparent var(--huleedu-border-width) var(--huleedu-grid-size)
    );
  border: var(--huleedu-border-width) solid var(--huleedu-panel-border);
  border-radius: var(--huleedu-panel-radius);
  box-sizing: border-box;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  padding: var(--huleedu-space-12) var(--huleedu-space-4);
}

.theme-sample-share__panel {
  background-color: var(--huleedu-panel);
  border: var(--huleedu-border-width) solid var(--huleedu-panel-border);
  border-radius: var(--huleedu-panel-radius);
  box-shadow: var(--huleedu-shadow-md);
  box-sizing: border-box;
  display: grid;
  gap: var(--huleedu-space-4);
  grid-template-columns: minmax(0, 1fr);
  justify-self: center;
  max-width: var(--huleedu-max-width-md);
  padding: var(--huleedu-space-6);
  width: 100%;
}

.theme-sample-share__title {
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-page-title);
  font-size: var(--huleedu-type-page-title-size);
  font-weight: var(--huleedu-type-page-title-weight);
  line-height: var(--huleedu-type-title-leading);
  margin: 0;
}

.theme-sample-share__text {
  color: var(--huleedu-navy-70);
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-type-supporting-size);
  font-weight: var(--huleedu-type-supporting-weight);
  line-height: var(--huleedu-type-body-leading);
  margin: 0;
}

.theme-sample-share__field {
  display: grid;
  gap: var(--huleedu-space-2);
}

.theme-sample-share__label {
  color: var(--huleedu-navy-70);
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-type-field-label-size);
  font-weight: var(--huleedu-type-field-label-weight);
  line-height: var(--huleedu-type-body-leading);
}

.theme-sample-share__input {
  background-color: var(--huleedu-surface-content);
  border: var(--huleedu-border-width) solid var(--huleedu-navy-30);
  border-radius: var(--huleedu-radius-sm);
  box-sizing: border-box;
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-mono);
  font-size: var(--huleedu-type-control-value-size);
  font-weight: var(--huleedu-type-control-value-weight);
  height: var(--huleedu-action-control-height);
  padding-inline: var(--huleedu-space-3);
  width: 100%;
}

.theme-sample-share__actions {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: var(--huleedu-space-3);
}

.theme-sample-share__status {
  color: var(--huleedu-success);
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-type-helper-size);
  font-weight: var(--huleedu-type-helper-weight);
  line-height: var(--huleedu-type-body-leading);
  margin: 0;
}

.theme-sample-share__status--failed {
  color: var(--huleedu-error);
}

.theme-sample-share__footer {
  color: var(--huleedu-navy-60);
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-type-helper-size);
  font-weight: var(--huleedu-type-helper-weight);
  line-height: var(--huleedu-type-body-leading);
  margin: 0;
}

/* Touch devices keep at least the base text size in the link field so focusing
   it does not zoom the page; the desktop control role stays above. */
@media (pointer: coarse), (hover: none) {
  .theme-sample-share__input {
    font-size: var(--huleedu-text-base);
  }
}
</style>
