<template>
  <div class="huleedu-card huleedu-mt-4">
    <h2 class="text-lg font-semibold">SPA island (demo)</h2>
    <p class="huleedu-muted">{{ message }}</p>
    <div class="mt-3 flex items-center gap-2">
      <button
        type="button"
        class="huleedu-btn huleedu-btn-navy huleedu-btn-sm"
        @click="count += 1"
      >
        Öka
      </button>
      <span class="font-mono">count={{ count }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

defineProps<{ message: string }>();

const count = ref(0);
</script>

