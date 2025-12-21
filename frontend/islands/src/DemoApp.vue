<template>
  <div class="huleedu-card huleedu-mt-4">
    <h2>SPA island (demo)</h2>
    <p class="huleedu-muted">{{ message }}</p>
    <div class="huleedu-flex-center huleedu-gap-2 huleedu-mt-2">
      <button
        type="button"
        class="huleedu-btn huleedu-btn-navy huleedu-btn-sm"
        @click="count += 1"
      >
        Öka
      </button>
      <code>count={{ count }}</code>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

defineProps<{ message: string }>();

const count = ref(0);
</script>
