<script setup lang="ts">
import { computed } from "vue";

export type SystemMessageVariant = "info" | "success" | "warning" | "error";

const props = withDefaults(
  defineProps<{
    modelValue: string | null;
    variant: SystemMessageVariant;
    id?: string;
    dismissLabel?: string;
    dismissible?: boolean;
  }>(),
  { id: undefined, dismissLabel: "Stäng", dismissible: true },
);

const emit = defineEmits<{
  "update:modelValue": [value: string | null];
  dismiss: [];
}>();

const role = computed(() => (props.variant === "error" ? "alert" : "status"));
const ariaLive = computed(() => (props.variant === "error" ? "assertive" : "polite"));

function dismiss(): void {
  emit("update:modelValue", null);
  emit("dismiss");
}
</script>

<template>
  <div
    v-if="modelValue"
    :id="id"
    class="system-message"
    :class="`system-message-${variant}`"
    :role="role"
    :aria-live="ariaLive"
    aria-atomic="true"
  >
    <p class="system-message-content">
      <slot>{{ modelValue }}</slot>
    </p>

    <button
      v-if="dismissible"
      type="button"
      class="system-message-close"
      :aria-label="dismissLabel"
      @click="dismiss"
    >
      &times;
    </button>
  </div>
</template>
