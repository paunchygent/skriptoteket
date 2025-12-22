<script setup lang="ts">
defineProps<{
  modelValue: boolean
  disabled?: boolean
}>()

defineEmits<{
  "update:modelValue": [value: boolean]
}>()
</script>

<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :disabled="disabled"
    class="group relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-sm border-2 border-navy bg-canvas transition-colors btn-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
    :class="{ 'bg-success/20': modelValue }"
    @click="$emit('update:modelValue', !modelValue)"
  >
    <span
      class="pointer-events-none inline-block h-4 w-4 transform rounded-sm shadow-brutal-sm transition-transform mt-0.5 ml-0.5"
      :class="[
        modelValue ? 'translate-x-5 bg-success' : 'translate-x-0 bg-navy/30',
      ]"
    />
  </button>
</template>
