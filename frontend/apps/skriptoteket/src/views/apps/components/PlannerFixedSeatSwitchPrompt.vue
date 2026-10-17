<script setup lang="ts">
/**
 * Fixed-seat classroom-view switch prompt.
 *
 * Purpose:
 *   Confirm the teacher wants to leave the abstract planning map before the
 *   fixed-seat tool activates in the physical classroom view.
 *
 * Relationships:
 *   - consumed by `PlannerRulesWorkspacePane.vue`
 *   - emits direct yes/no/close choices without owning map state
 */

import { UiDenseIconButton } from "../../../components/ui";
import { UiGlyph } from "../../../components/ui/shared";

const emit = defineEmits<{
  (e: "accept"): void;
  (e: "decline"): void;
  (e: "close"): void;
}>();
</script>

<template>
  <div
    class="relative border border-navy bg-canvas p-3"
    data-test="rules-fixed-seat-switch-prompt"
  >
    <UiDenseIconButton
      label="Stäng"
      class="absolute right-2 top-2"
      data-test="rules-fixed-seat-switch-close"
      @click="emit('close')"
    >
      <UiGlyph
        meaning="close"
        :size="14"
        :stroke-width="2.5"
      />
    </UiDenseIconButton>
    <p class="pr-6 text-sm font-semibold leading-relaxed text-navy">
      Fast plats kräver en fysisk plats. Vill du byta till klassrumsvyn?
    </p>
    <div class="mt-3 flex gap-2">
      <button
        type="button"
        class="btn-inline-primary"
        data-test="rules-fixed-seat-switch-yes"
        @click="emit('accept')"
      >
        Ja
      </button>
      <button
        type="button"
        class="btn-inline-cancel"
        data-test="rules-fixed-seat-switch-no"
        @click="emit('decline')"
      >
        Nej
      </button>
    </div>
  </div>
</template>
