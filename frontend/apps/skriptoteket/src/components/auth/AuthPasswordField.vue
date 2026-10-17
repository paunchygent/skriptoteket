<script setup lang="ts">
/**
 * Reusable password field with inline visibility toggle.
 *
 * This component keeps auth-facing password inputs visually consistent while
 * exposing the classic eye toggle requested for registration flows.
 */

import { computed, ref } from "vue";

import { UiDenseIconButton, UiGlyph } from "../ui/shared";

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
      class="text-[length:var(--huleedu-type-field-label-size)] font-[var(--huleedu-type-field-label-weight)] text-navy"
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
        class="w-full rounded-[var(--huleedu-panel-radius)] border bg-panel px-3 py-2 pr-11 text-navy"
        :class="error ? 'border-critical' : 'border-[var(--huleedu-panel-border)]'"
        @input="onInput"
      >

      <div class="absolute inset-y-0 right-0 flex w-11 items-center justify-center">
        <UiDenseIconButton
          :label="visibilityLabel"
          :disabled="disabled"
          @click="isVisible = !isVisible"
        >
          <UiGlyph
            :meaning="isVisible ? 'hide-password' : 'show-password'"
            :size="16"
          />
        </UiDenseIconButton>
      </div>
    </div>

    <p
      v-if="hint || error"
      :id="descriptionId"
      class="text-xs"
      :class="error ? 'text-critical' : 'text-navy/60'"
    >
      {{ error ?? hint }}
    </p>
  </div>
</template>
