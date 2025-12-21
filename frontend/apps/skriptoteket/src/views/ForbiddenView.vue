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
  <div>
    <h2>Forbidden</h2>
    <p>You do not have permission to view this page.</p>
    <p v-if="requiredRole">Required role: {{ requiredRole }}</p>
    <p v-if="fromPath">Attempted path: {{ fromPath }}</p>
  </div>
</template>

