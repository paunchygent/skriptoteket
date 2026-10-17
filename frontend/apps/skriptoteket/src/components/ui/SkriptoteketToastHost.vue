<script setup lang="ts">
import { computed } from "vue";

import { useToastStore } from "../../stores/toast";
import { ToastHost } from "./shared";

const toast = useToastStore();
const newestFirst = computed(() => [...toast.toasts].reverse());
</script>

<template>
  <Teleport to="body">
    <ToastHost
      class="skriptoteket-toast-host"
      :toasts="newestFirst"
      placement="bottom"
      @dismiss="toast.dismiss"
    />
  </Teleport>
</template>

<style scoped>
.skriptoteket-toast-host {
  --huleedu-toast-bottom: calc(var(--huleedu-space-4) + env(safe-area-inset-bottom));
  --huleedu-toast-width: min(var(--huleedu-max-width-md), calc(100vw - 2 * var(--huleedu-space-4)));
  --huleedu-toast-inline-end: calc((100vw - min(var(--huleedu-max-width-md), calc(100vw - 2 * var(--huleedu-space-4)))) / 2);
}

@media (min-width: 768px) {
  .skriptoteket-toast-host {
    --huleedu-toast-bottom: var(--huleedu-space-6);
    --huleedu-toast-inline-end: var(--huleedu-space-6);
    --huleedu-toast-width: var(--huleedu-max-width-md);
  }
}
</style>
