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

import { IconX } from "../../../components/icons";

const emit = defineEmits<{
  (e: "accept"): void;
  (e: "decline"): void;
  (e: "close"): void;
}>();
</script>

<template>
  <div
    class="relative border border-navy bg-canvas p-3 shadow-brutal-sm"
    data-test="rules-fixed-seat-switch-prompt"
  >
    <button
      type="button"
      class="planner-row-remove-button absolute right-2 top-2"
      aria-label="Stäng"
      data-test="rules-fixed-seat-switch-close"
      @click="emit('close')"
    >
      <IconX :size="14" />
    </button>
    <p class="pr-6 text-sm font-semibold leading-relaxed text-navy">
      Fast plats kräver en fysisk plats. Vill du byta till klassrumsvyn?
    </p>
    <div class="mt-3 flex gap-2">
      <button
        type="button"
        class="btn-primary planner-btn-primary-sm"
        data-test="rules-fixed-seat-switch-yes"
        @click="emit('accept')"
      >
        Ja
      </button>
      <button
        type="button"
        class="btn-ghost planner-btn-ghost planner-btn-ghost-sm"
        data-test="rules-fixed-seat-switch-no"
        @click="emit('decline')"
      >
        Nej
      </button>
    </div>
  </div>
</template>
