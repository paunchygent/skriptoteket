<script setup lang="ts">
/**
 * Compound dense toggle for feature-on/off plus deep configuration.
 *
 * Relationships:
 * - composes `UiDenseToggle` with a configure-context child action
 * - canonical proving-ground pattern for `Smart` + `Regler`
 */

import { IconAdjustments } from "../icons";
import UiDenseActionButton from "./UiDenseActionButton.vue";
import UiDenseToggle from "./UiDenseToggle.vue";

withDefaults(
  defineProps<{
    modelValue: boolean;
    label: string;
    disabled?: boolean;
    actionLabel: string;
    actionTitle?: string;
    actionDisabled?: boolean;
    rootTestId?: string;
    actionTestId?: string;
  }>(),
  {
    disabled: false,
    actionTitle: undefined,
    actionDisabled: false,
    rootTestId: undefined,
    actionTestId: undefined,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  action: [];
}>();
</script>

<template>
  <div
    class="inline-flex items-stretch"
    data-ui="dense-compound-toggle"
    :data-test="rootTestId"
  >
    <UiDenseToggle
      :model-value="modelValue"
      :label="label"
      :disabled="disabled"
      group-position="start"
      @update:model-value="emit('update:modelValue', $event)"
    />
    <UiDenseActionButton
      :label="actionLabel"
      :title="actionTitle"
      :disabled="actionDisabled"
      group-position="end"
      :data-test="actionTestId"
      @click="emit('action')"
    >
      <template #leading>
        <IconAdjustments :size="14" />
      </template>
    </UiDenseActionButton>
  </div>
</template>
