<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();

const requiredRole = computed(() => {
  const value = route.query.required;
  return typeof value === "string" ? value : null;
});

const fromPath = computed(() => {
  const value = route.query.from;
  if (typeof value !== "string") {
    return null;
  }
  return value.startsWith("/") ? value : null;
});
</script>

<template>
  <div class="font-sans text-navy">
    <h2>Forbidden</h2>
    <p class="text-navy/70">You do not have permission to view this page.</p>
    <p
      v-if="requiredRole"
      class="text-navy/70"
    >
      Required role: {{ requiredRole }}
    </p>
    <p
      v-if="fromPath"
      class="text-navy/70"
    >
      Attempted path: {{ fromPath }}
    </p>
  </div>
</template>
