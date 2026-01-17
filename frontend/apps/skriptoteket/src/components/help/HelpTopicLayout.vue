<script setup lang="ts">
const emit = defineEmits<{ (event: "back"): void }>();

defineProps<{ title: string }>();
</script>

<template>
  <section class="space-y-3">
    <button
      type="button"
      class="text-sm text-navy/70 underline hover:text-burgundy"
      @click="emit('back')"
    >
      ← Till hjälpindex
    </button>
    <h3 class="text-lg font-semibold text-navy">{{ title }}</h3>
    <slot />
    <slot name="footer">
      <p class="text-sm text-navy/60">Mer hjälp kommer snart.</p>
    </slot>
  </section>
</template>
