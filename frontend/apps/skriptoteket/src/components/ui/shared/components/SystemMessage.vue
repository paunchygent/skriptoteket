<script setup lang="ts">
/**
 * Purpose:
 *     Render shared inline system feedback without app-specific store coupling.
 *
 * Relationships:
 *     - Uses HuleEdu token utilities from the shared Tailwind bridge.
 *     - Complements ToastHost for persistent inline feedback.
 *     - The parent owns visibility: an omitted modelValue renders the slot
 *       unconditionally, null or empty text hides the message, and dismissal
 *       only emits update:modelValue(null) followed by dismiss.
 *     - Announcement semantics default to role="status"; consumers pass
 *       role, aria-live, aria-atomic, id and class through to the root.
 */

import { computed } from "vue";

export type SystemMessageTone = "info" | "success" | "warning" | "failure";

const props = withDefaults(
  defineProps<{
    tone?: SystemMessageTone;
    modelValue?: string | null;
    dismissible?: boolean;
    dismissLabel?: string;
  }>(),
  {
    tone: "info",
    modelValue: undefined,
    dismissible: false,
    dismissLabel: "Stäng",
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string | null];
  dismiss: [];
}>();

const visible = computed(
  () => props.modelValue === undefined || (props.modelValue !== null && props.modelValue !== ""),
);

function dismissMessage(): void {
  emit("update:modelValue", null);
  emit("dismiss");
}
</script>

<template>
  <div
    v-if="visible"
    :class="[
      'min-w-0 break-words rounded-[var(--huleedu-panel-radius)] border px-3 py-2 font-sans text-sm font-normal leading-snug shadow-none',
      tone === 'success' && 'border-success/45 bg-success/10 text-success',
      tone === 'warning' && 'border-warning/50 bg-warning/15 text-navy',
      tone === 'failure' && 'border-error/40 bg-error/10 text-error',
      tone === 'info' && 'border-navy/20 bg-canvas/60 text-navy',
      dismissible && 'flex items-start gap-2',
    ]"
    role="status"
    data-ui="system-message"
  >
    <template v-if="dismissible">
      <div class="min-w-0 flex-1">
        <slot>{{ modelValue }}</slot>
      </div>
      <button
        type="button"
        class="-my-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-[4px] text-base leading-none text-current opacity-70 transition-opacity hover:opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-current"
        :aria-label="dismissLabel"
        data-ui="system-message-dismiss"
        @click="dismissMessage"
      >
        <span aria-hidden="true">&times;</span>
      </button>
    </template>
    <slot v-else>{{ modelValue }}</slot>
  </div>
</template>
