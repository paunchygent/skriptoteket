<script setup lang="ts">
/**
 * Purpose:
 *     Draw the sample dialog of the full theme sample page open in place, so
 *     the shared dialog surface is visible without clicking a trigger.
 *
 * Relationships:
 *     - Composed by ThemeSampleControls.vue under its "Dialog" subheading.
 *     - Takes no props: the component shows one fixed delete confirmation.
 *     - Draws the dialog inside a relative frame, so it never leaves the page
 *       flow or covers the viewport. The backdrop layer is aria-hidden, and the
 *       role="dialog" box is aria-modal="false" for the same in-place reason.
 *     - Takes colours, spacing, type, radii, borders and the panel shadow from
 *       shared tokens in scoped styles. action-buttons.css defines no critical
 *       CTA class, so the destructive action repeats the shared CTA geometry
 *       and takes --huleedu-critical and --huleedu-critical-text.
 */

import { useId } from "vue";

const dialogTitleId = useId();
</script>

<template>
  <div
    class="theme-sample-dialog"
    data-ui="theme-sample-dialog"
  >
    <div
      class="theme-sample-dialog__backdrop"
      aria-hidden="true"
    ></div>
    <div
      class="theme-sample-dialog__panel"
      role="dialog"
      aria-modal="false"
      :aria-labelledby="dialogTitleId"
    >
      <h3
        :id="dialogTitleId"
        class="theme-sample-dialog__title"
      >
        Ta bort bilden?
      </h3>
      <p class="theme-sample-dialog__text">
        Bilden tas bort från biblioteket. Det går inte att ångra.
      </p>
      <div class="theme-sample-dialog__actions">
        <button
          type="button"
          class="btn-ghost"
        >
          Avbryt
        </button>
        <button
          type="button"
          class="theme-sample-dialog__critical"
        >
          Ta bort
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.theme-sample-dialog {
  background-color: var(--huleedu-paper);
  border: var(--huleedu-border-width) solid var(--huleedu-panel-border);
  border-radius: var(--huleedu-panel-radius);
  box-sizing: border-box;
  display: grid;
  isolation: isolate;
  justify-items: center;
  max-width: var(--huleedu-max-width-2xl);
  overflow: hidden;
  padding: var(--huleedu-space-6);
  position: relative;
}

.theme-sample-dialog__backdrop {
  background-color: var(--huleedu-overlay);
  inset: 0;
  position: absolute;
}

.theme-sample-dialog__panel {
  background-color: var(--huleedu-modal);
  border: var(--huleedu-border-width) solid var(--huleedu-panel-border);
  border-radius: var(--huleedu-panel-radius);
  box-shadow: var(--huleedu-shadow-md);
  box-sizing: border-box;
  display: grid;
  gap: var(--huleedu-space-3);
  max-width: var(--huleedu-max-width-lg);
  padding: var(--huleedu-space-5);
  position: relative;
  width: 100%;
}

.theme-sample-dialog__title {
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-type-nested-title-size);
  font-weight: var(--huleedu-type-nested-title-weight);
  line-height: var(--huleedu-type-title-leading);
  margin: 0;
}

.theme-sample-dialog__text {
  color: var(--huleedu-navy-70);
  font-family: var(--huleedu-font-interface);
  font-size: var(--huleedu-type-supporting-size);
  font-weight: var(--huleedu-type-supporting-weight);
  line-height: var(--huleedu-type-body-leading);
  margin: 0;
}

.theme-sample-dialog__actions {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: var(--huleedu-space-2);
  justify-content: flex-end;
}

/* The shared CTA geometry, filled with the critical decision roles. */
.theme-sample-dialog__critical {
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
  .theme-sample-dialog__critical:hover:not(:disabled) {
    opacity: 0.88;
  }
}

.theme-sample-dialog__critical:active:not(:disabled) {
  opacity: 0.76;
}

.theme-sample-dialog__critical:focus-visible {
  outline: var(--huleedu-border-width-2) solid var(--huleedu-action);
  outline-offset: var(--huleedu-space-1);
}
</style>
