<script setup lang="ts">
/**
 * Reusable password field with inline visibility toggle.
 *
 * This component keeps auth-facing password inputs visually consistent while
 * exposing the classic eye toggle requested for registration flows.
 */

import { Eye, EyeOff } from "lucide-vue-next";
import { computed, ref } from "vue";

const props = withDefaults(
  defineProps<{
    id: string;
    label: string;
    modelValue: string;
    autocomplete?: string;
    hint?: string | null;
    error?: string | null;
    disabled?: boolean;
    required?: boolean;
  }>(),
  {
    autocomplete: "current-password",
    hint: null,
    error: null,
    disabled: false,
    required: false,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const isVisible = ref(false);

const inputType = computed(() => (isVisible.value ? "text" : "password"));
const descriptionId = computed(() => `${props.id}-description`);
const visibilityLabel = computed(() =>
  isVisible.value ? "Dölj lösenord" : "Visa lösenord",
);

function onInput(event: Event): void {
  emit("update:modelValue", (event.target as HTMLInputElement).value);
}
</script>

<template>
  <div class="space-y-2">
    <label
      :for="id"
      class="text-sm font-semibold text-navy"
    >{{ label }}</label>

    <div class="relative">
      <input
        :id="id"
        :value="modelValue"
        :type="inputType"
        :required="required"
        :autocomplete="autocomplete"
        :disabled="disabled"
        :aria-invalid="error ? 'true' : 'false'"
        :aria-describedby="hint || error ? descriptionId : undefined"
        class="w-full border bg-white px-3 py-2 pr-11 shadow-brutal-sm text-navy"
        :class="error ? 'border-burgundy' : 'border-navy'"
        @input="onInput"
      >

      <button
        type="button"
        class="absolute inset-y-0 right-0 flex items-center justify-center px-3 text-navy/60 hover:text-navy"
        :aria-label="visibilityLabel"
        :disabled="disabled"
        @click="isVisible = !isVisible"
      >
        <component
          :is="isVisible ? EyeOff : Eye"
          :size="16"
          aria-hidden="true"
        />
      </button>
    </div>

    <p
      v-if="hint || error"
      :id="descriptionId"
      class="text-xs"
      :class="error ? 'text-burgundy' : 'text-navy/60'"
    >
      {{ error ?? hint }}
    </p>
  </div>
</template>
