<script setup lang="ts">
import type { components } from "../../api/openapi";

type SchemaValidationIssue = components["schemas"]["SchemaValidationIssue"];

type EditorSchemaIssuesListProps = {
  issues: SchemaValidationIssue[];
};

const props = defineProps<EditorSchemaIssuesListProps>();
</script>

<template>
  <div
    v-if="props.issues.length > 0"
    class="space-y-1"
  >
    <p class="text-xs font-semibold text-burgundy">
      Valideringsfel:
    </p>
    <ul class="space-y-1">
      <li
        v-for="(issue, index) in props.issues"
        :key="index"
        class="text-xs text-burgundy"
      >
        <span
          v-if="issue.path"
          class="font-mono"
        >{{ issue.path }}</span>
        <span
          v-if="issue.path"
          class="mx-1"
        >·</span>
        <span>{{ issue.message }}</span>
      </li>
    </ul>
  </div>
</template>
