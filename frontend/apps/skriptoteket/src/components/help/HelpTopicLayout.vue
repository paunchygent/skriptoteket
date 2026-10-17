<script setup lang="ts">
const emit = defineEmits<{ (event: "back"): void }>();

defineProps<{ title: string }>();
</script>

<template>
  <section class="space-y-3">
    <a
      href="#help-index"
      class="text-sm font-medium text-action underline underline-offset-2 hover:text-action/80"
      @click.prevent="emit('back')"
    >
      ← Till hjälpindex
    </a>
    <h3 class="text-lg font-semibold text-navy">{{ title }}</h3>
    <slot />
    <slot name="footer" />
  </section>
</template>
