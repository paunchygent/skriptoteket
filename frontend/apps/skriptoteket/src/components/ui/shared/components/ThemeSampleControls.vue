<script setup lang="ts">
/**
 * Purpose:
 *     Render the controls section of the full theme sample page: the shared
 *     calls to action, panels, form fields, status feedback and an open dialog.
 *
 * Relationships:
 *     - Composed by ThemeSamplePage.vue between the top-bar and workspace
 *       sections.
 *     - Takes no props: every control is a fixed specimen of a shared surface.
 *     - Uses the shared CTA classes from action-buttons.css. That file defines
 *       no critical CTA class, so the critical specimen repeats the same
 *       geometry and takes --huleedu-critical and --huleedu-critical-text.
 *     - Wraps UiDenseActionButton, UiDenseIconButton, UiDenseStatusPill,
 *       UiSegmentedToggle and SystemMessage; their own Tailwind utilities stay
 *       inside those components.
 *     - Composes ThemeSampleDialog.vue under the "Dialog" subheading; that
 *       component owns the frame, the backdrop and the dialog specimen.
 *     - Takes colours, spacing, type, radii, borders and geometry from shared
 *       tokens in scoped styles, and raises the field text to 16px on touch
 *       devices so focusing a field never zooms the page.
 */

import { ref } from "vue";

import SystemMessage from "./SystemMessage.vue";
import ThemeSampleDialog from "./ThemeSampleDialog.vue";
import UiDenseActionButton from "./UiDenseActionButton.vue";
import UiDenseIconButton from "./UiDenseIconButton.vue";
import UiDenseStatusPill from "./UiDenseStatusPill.vue";
import UiGlyph from "./UiGlyph.vue";
import UiSegmentedToggle from "./UiSegmentedToggle.vue";

const name = ref("");
const selectedRole = ref("larare");
const showArchived = ref(false);
const viewMode = ref("lista");

const viewOptions = [
  { value: "lista", label: "Lista" },
  { value: "rutnat", label: "Rutnät" },
  { value: "tidslinje", label: "Tidslinje" },
];
</script>

<template>
  <section
    class="theme-sample-controls"
    data-ui="theme-sample-controls"
  >
    <h2 class="theme-sample-controls__heading">Komponenter</h2>

    <div class="theme-sample-controls__group">
      <h3 class="theme-sample-controls__group-title">Knappar</h3>
      <div class="theme-sample-controls__row">
        <button
          type="button"
          class="btn-primary"
        >
          Spara
        </button>
        <button
          type="button"
          class="btn-ghost"
        >
          Avbryt
        </button>
        <button
          type="button"
          class="theme-sample-controls__critical"
        >
          Ta bort
        </button>
      </div>
      <div class="theme-sample-controls__row">
        <UiDenseActionButton
          label="Spara"
          tone="primary"
        >
          <template #leading>
            <span class="theme-sample-controls__glyph">
              <UiGlyph meaning="save" />
            </span>
          </template>
        </UiDenseActionButton>
        <UiDenseIconButton
          label="Ta bort"
          tone="danger"
        >
          <span class="theme-sample-controls__glyph">
            <UiGlyph meaning="delete" />
          </span>
        </UiDenseIconButton>
      </div>
    </div>

    <div class="theme-sample-controls__group">
      <h3 class="theme-sample-controls__group-title">Paneler</h3>
      <div class="theme-sample-controls__panels">
        <div class="theme-sample-controls__panel">
          <h4 class="theme-sample-controls__panel-title">Utkast</h4>
          <p class="theme-sample-controls__panel-text">
            Ett utkast sparas automatiskt och syns bara för dig.
          </p>
        </div>
        <div class="theme-sample-controls__panel theme-sample-controls__panel--muted">
          <h4 class="theme-sample-controls__panel-title">Arkiv</h4>
          <p class="theme-sample-controls__panel-text">
            Arkiverade bedömningar finns kvar i sex månader.
          </p>
        </div>
      </div>
    </div>

    <div class="theme-sample-controls__group">
      <h3 class="theme-sample-controls__group-title">Fält</h3>
      <div class="theme-sample-controls__fields">
        <div class="theme-sample-controls__field">
          <label
            class="theme-sample-controls__label"
            for="theme-sample-controls-name"
          >
            Namn
          </label>
          <input
            id="theme-sample-controls-name"
            v-model="name"
            class="theme-sample-controls__input"
            type="text"
            placeholder="Förnamn Efternamn"
          />
        </div>
        <div class="theme-sample-controls__field">
          <label
            class="theme-sample-controls__label"
            for="theme-sample-controls-role"
          >
            Roll
          </label>
          <select
            id="theme-sample-controls-role"
            v-model="selectedRole"
            class="theme-sample-controls__select"
          >
            <option value="larare">Lärare</option>
            <option value="granskare">Granskare</option>
            <option value="administrator">Administratör</option>
          </select>
        </div>
        <label class="theme-sample-controls__check">
          <input
            v-model="showArchived"
            class="theme-sample-controls__checkbox"
            type="checkbox"
          />
          <span class="theme-sample-controls__check-text">Visa arkiverade</span>
        </label>
        <div class="theme-sample-controls__field theme-sample-controls__field--wide">
          <UiSegmentedToggle
            v-model="viewMode"
            :options="viewOptions"
            aria-label="Vy"
          />
        </div>
      </div>
    </div>

    <div class="theme-sample-controls__group">
      <h3 class="theme-sample-controls__group-title">Status</h3>
      <div class="theme-sample-controls__pills">
        <UiDenseStatusPill
          label="Utkast"
          tone="neutral"
        />
        <UiDenseStatusPill
          label="Klar"
          tone="success"
        />
        <UiDenseStatusPill
          label="Väntar"
          tone="warning"
        />
        <UiDenseStatusPill
          label="Fel"
          tone="error"
        />
      </div>
      <div class="theme-sample-controls__messages">
        <SystemMessage tone="info">Information: utkastet sparas automatiskt.</SystemMessage>
        <SystemMessage tone="success">Klart: bedömningen är inskickad.</SystemMessage>
        <SystemMessage tone="warning">Varning: två svar saknas.</SystemMessage>
        <SystemMessage tone="failure">Fel: filen kunde inte laddas upp.</SystemMessage>
      </div>
    </div>

    <div class="theme-sample-controls__group">
      <h3 class="theme-sample-controls__group-title">Dialog</h3>
      <ThemeSampleDialog />
    </div>
  </section>
</template>

<style scoped>
.theme-sample-controls {
  display: grid;
  gap: var(--huleedu-space-6);
}

.theme-sample-controls__heading {
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-type-section-title-size);
  font-weight: var(--huleedu-type-section-title-weight);
  line-height: var(--huleedu-type-title-leading);
  margin: 0;
}

.theme-sample-controls__group {
  display: grid;
  gap: var(--huleedu-space-3);
}

.theme-sample-controls__group-title {
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-type-nested-title-size);
  font-weight: var(--huleedu-type-nested-title-weight);
  line-height: var(--huleedu-type-title-leading);
  margin: 0;
}

.theme-sample-controls__row {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: var(--huleedu-space-3);
}

/* The shared CTA geometry, filled with the critical decision roles. */
.theme-sample-controls__critical {
  align-items: center;
  background-color: var(--huleedu-critical);
  border: var(--huleedu-border-width) solid var(--huleedu-critical);
  border-radius: var(--huleedu-radius-md);
  box-sizing: border-box;
  color: var(--huleedu-critical-text);
  cursor: pointer;
  display: inline-flex;
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-text-sm);
  font-weight: var(--huleedu-font-semibold);
  gap: var(--huleedu-space-2);
  justify-content: center;
  letter-spacing: var(--huleedu-tracking-normal);
  line-height: var(--huleedu-leading-none);
  min-height: var(--huleedu-action-control-height);
  padding-inline: var(--huleedu-space-6);
  text-decoration: none;
  transition: opacity var(--huleedu-duration-default) var(--huleedu-ease-default);
}

@media (hover: hover) and (pointer: fine) {
  .theme-sample-controls__critical:hover:not(:disabled) {
    opacity: 0.88;
  }
}

.theme-sample-controls__critical:active:not(:disabled) {
  opacity: 0.76;
}

.theme-sample-controls__critical:focus-visible {
  outline: var(--huleedu-border-width-2) solid var(--huleedu-action);
  outline-offset: var(--huleedu-space-1);
}

/* UiGlyph takes a numeric size only; the shared icon role sizes its svg. */
.theme-sample-controls__glyph {
  display: inline-flex;
}

.theme-sample-controls__glyph :deep(svg) {
  height: var(--huleedu-workbench-icon-size);
  width: var(--huleedu-workbench-icon-size);
}

.theme-sample-controls__panels {
  display: flex;
  flex-wrap: wrap;
  gap: var(--huleedu-space-4);
}

.theme-sample-controls__panel {
  background-color: var(--huleedu-panel);
  border: var(--huleedu-border-width) solid var(--huleedu-panel-border);
  border-radius: var(--huleedu-panel-radius);
  box-sizing: border-box;
  display: grid;
  flex: 1 1 calc(var(--huleedu-space-20) * 4);
  gap: var(--huleedu-space-2);
  padding: var(--huleedu-space-4);
}

.theme-sample-controls__panel--muted {
  background-color: var(--huleedu-panel-muted);
}

.theme-sample-controls__panel-title {
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-type-field-label-size);
  font-weight: var(--huleedu-type-field-label-weight);
  line-height: var(--huleedu-type-title-leading);
  margin: 0;
}

.theme-sample-controls__panel-text {
  color: var(--huleedu-navy-70);
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-type-supporting-size);
  font-weight: var(--huleedu-type-supporting-weight);
  line-height: var(--huleedu-type-body-leading);
  margin: 0;
}

.theme-sample-controls__fields {
  display: grid;
  gap: var(--huleedu-space-4);
  grid-template-columns: repeat(
    auto-fit,
    minmax(min(100%, calc(var(--huleedu-space-20) * 4)), 1fr)
  );
}

.theme-sample-controls__field {
  display: grid;
  gap: var(--huleedu-space-2);
  min-width: 0;
}

.theme-sample-controls__field--wide {
  grid-column: 1 / -1;
}

.theme-sample-controls__label {
  color: var(--huleedu-navy-70);
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-type-field-label-size);
  font-weight: var(--huleedu-type-field-label-weight);
  line-height: var(--huleedu-type-body-leading);
}

.theme-sample-controls__input,
.theme-sample-controls__select {
  background-color: var(--huleedu-surface-content);
  border: var(--huleedu-border-width) solid var(--huleedu-navy-30);
  border-radius: var(--huleedu-radius-sm);
  box-sizing: border-box;
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-type-control-value-size);
  font-weight: var(--huleedu-type-control-value-weight);
  min-height: var(--huleedu-action-control-height);
  padding-inline: var(--huleedu-space-3);
  width: 100%;
}

/* Touch devices raise the field text to 16px so focusing a field never zooms
   the page; the desktop control-value role above stays in force for fine
   pointers. */
@media (pointer: coarse), (hover: none) {
  .theme-sample-controls__input,
  .theme-sample-controls__select {
    font-size: var(--huleedu-text-base);
  }
}

.theme-sample-controls__input::placeholder {
  color: var(--huleedu-navy-50);
}

.theme-sample-controls__input:focus-visible,
.theme-sample-controls__select:focus-visible,
.theme-sample-controls__checkbox:focus-visible {
  outline: var(--huleedu-border-width-2) solid var(--huleedu-action);
  outline-offset: var(--huleedu-space-1);
}

.theme-sample-controls__check {
  align-items: center;
  cursor: pointer;
  display: flex;
  gap: var(--huleedu-space-2);
  grid-column: 1 / -1;
  min-height: var(--huleedu-action-control-height);
}

.theme-sample-controls__checkbox {
  accent-color: var(--huleedu-action);
  height: var(--huleedu-space-4);
  margin: 0;
  width: var(--huleedu-space-4);
}

.theme-sample-controls__check-text {
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-type-field-label-size);
  font-weight: var(--huleedu-type-field-label-weight);
  line-height: var(--huleedu-type-body-leading);
}

.theme-sample-controls__pills {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: var(--huleedu-space-2);
}

.theme-sample-controls__messages {
  display: grid;
  gap: var(--huleedu-space-2);
}
</style>
