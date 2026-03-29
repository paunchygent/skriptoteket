<script setup lang="ts">
/**
 * Canonical configure-context symbol.
 *
 * Relationships:
 * - replaces ambiguous gear-as-rules usage in shared dense-tool contracts
 * - exported through `src/components/icons/index.ts`
 */

defineProps<{
  size?: number;
}>();
</script>

<template>
  <svg
    :width="size ?? 24"
    :height="size ?? 24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2.5"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path d="M4 7h16" />
    <path d="M4 12h16" />
    <path d="M4 17h16" />
    <circle
      cx="8"
      cy="7"
      r="1.75"
      fill="currentColor"
      stroke="none"
    />
    <circle
      cx="15"
      cy="12"
      r="1.75"
      fill="currentColor"
      stroke="none"
    />
    <circle
      cx="11"
      cy="17"
      r="1.75"
      fill="currentColor"
      stroke="none"
    />
  </svg>
</template>
