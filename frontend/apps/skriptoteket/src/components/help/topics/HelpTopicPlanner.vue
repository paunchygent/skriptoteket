<script setup lang="ts">
import { computed } from "vue";

import HelpTopicLayout from "../HelpTopicLayout.vue";
import { plannerHelpSections, plannerHelpTitles } from "../plannerHelpSections.generated";
import { useHelp } from "../useHelp";

const props = defineProps<{ section: string }>();
const { showIndex } = useHelp();

const title = computed(() => plannerHelpTitles[props.section] ?? "Klassrumskartan");
const html = computed(() => plannerHelpSections[props.section] ?? "");
</script>

<template>
  <HelpTopicLayout
    :title="title"
    @back="showIndex"
  >
    <!-- eslint-disable vue/no-v-html -->
    <div
      class="help-planner-content space-y-3 text-sm text-navy"
      v-html="html"
    />
    <!-- eslint-enable vue/no-v-html -->
    <template #footer>
      <p class="text-xs text-navy/50">
        Innehållet genereras från kom igång-guiden.
      </p>
    </template>
  </HelpTopicLayout>
</template>

<style scoped>
.help-planner-content :deep(h3) {
  font-size: 0.9375rem;
  font-weight: 600;
  margin-top: 1rem;
}

.help-planner-content :deep(h4) {
  font-size: 0.8125rem;
  font-weight: 600;
  margin-top: 0.75rem;
}

.help-planner-content :deep(ul),
.help-planner-content :deep(ol) {
  padding-left: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.help-planner-content :deep(ul) {
  list-style-type: disc;
}

.help-planner-content :deep(ol) {
  list-style-type: decimal;
}

.help-planner-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.help-planner-content :deep(th),
.help-planner-content :deep(td) {
  border: 1px solid var(--huleedu-color-navy-20, rgba(26, 26, 64, 0.2));
  padding: 0.375rem 0.5rem;
  text-align: left;
}

.help-planner-content :deep(th) {
  font-weight: 600;
  background: var(--huleedu-color-canvas, #f5f5f0);
}

.help-planner-content :deep(p) {
  line-height: 1.5;
}
</style>
