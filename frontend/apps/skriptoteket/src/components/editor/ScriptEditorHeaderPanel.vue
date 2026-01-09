<script setup lang="ts">
import { computed, withDefaults } from "vue";
import InlineEditableText from "./InlineEditableText.vue";

type ScriptEditorHeaderPanelProps = {
  section?: "title" | "summary" | "full";
  metadataTitle: string;
  metadataSummary: string;
  toolSlug: string;
  isTitleSaving: boolean;
  isSummarySaving: boolean;
};

const props = withDefaults(defineProps<ScriptEditorHeaderPanelProps>(), {
  section: "full",
});

const showTitle = computed(() => props.section !== "summary");
const showSummary = computed(() => props.section !== "title");

const emit = defineEmits<{
  (event: "update:metadataTitle", value: string): void;
  (event: "update:metadataSummary", value: string): void;
  (event: "commitTitle"): void;
  (event: "commitSummary"): void;
}>();
</script>

<template>
  <div :class="showTitle && showSummary ? 'space-y-2' : ''">
    <div
      v-if="showTitle"
      class="flex flex-wrap items-start gap-2"
    >
      <div class="flex-1 min-w-[200px]">
        <InlineEditableText
          :model-value="props.metadataTitle"
          tag="h1"
          display-class="text-base font-semibold text-navy"
          input-class="text-base font-semibold"
          placeholder="Verktygets titel"
          :saving="props.isTitleSaving"
          @update:model-value="emit('update:metadataTitle', $event)"
          @commit="emit('commitTitle')"
        />
      </div>
    </div>

    <div
      v-if="showSummary"
      class="flex flex-wrap items-center gap-3"
    >
      <div class="flex-1 min-w-[220px] space-y-1">
        <InlineEditableText
          :model-value="props.metadataSummary"
          tag="p"
          display-class="text-xs text-navy/70"
          input-class="text-xs"
          placeholder="Kort sammanfattning..."
          :saving="props.isSummarySaving"
          @update:model-value="emit('update:metadataSummary', $event)"
          @commit="emit('commitSummary')"
        />
        <div class="flex flex-wrap items-center gap-2 text-xs text-navy/70">
          <span class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
            URL-namn
          </span>
          <span class="text-xs font-mono text-navy">
            {{ props.toolSlug }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
