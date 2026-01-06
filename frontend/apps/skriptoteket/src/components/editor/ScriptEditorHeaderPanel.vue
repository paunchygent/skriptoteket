<script setup lang="ts">
import InlineEditableText from "./InlineEditableText.vue";
import WorkflowContextButtons from "./WorkflowContextButtons.vue";
import type { SubmitReviewTooltip } from "../../composables/editor/useEditorWorkflowActions";

type WorkflowAction = "submit_review" | "publish" | "request_changes" | "rollback";

type ScriptEditorHeaderPanelProps = {
  metadataTitle: string;
  metadataSummary: string;
  toolSlug: string;
  statusLine: string;
  isTitleSaving: boolean;
  isSummarySaving: boolean;
  canSubmitReview: boolean;
  submitReviewTooltip: SubmitReviewTooltip | null;
  canPublish: boolean;
  canRequestChanges: boolean;
  canRollback: boolean;
  isWorkflowSubmitting: boolean;
};

const props = defineProps<ScriptEditorHeaderPanelProps>();

const emit = defineEmits<{
  (event: "update:metadataTitle", value: string): void;
  (event: "update:metadataSummary", value: string): void;
  (event: "commitTitle"): void;
  (event: "commitSummary"): void;
  (event: "action", action: WorkflowAction): void;
}>();
</script>

<template>
  <div class="border border-navy bg-white shadow-brutal-sm p-5 space-y-4">
    <!-- Title and summary section -->
    <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
      <div class="space-y-2 flex-1">
        <InlineEditableText
          :model-value="props.metadataTitle"
          tag="h1"
          display-class="text-2xl font-semibold text-navy"
          input-class="text-2xl font-semibold"
          placeholder="Verktygets titel"
          :saving="props.isTitleSaving"
          @update:model-value="emit('update:metadataTitle', $event)"
          @commit="emit('commitTitle')"
        />
        <p class="text-sm text-navy/70">
          URL-namn: <span class="font-mono">{{ props.toolSlug }}</span>
        </p>
        <InlineEditableText
          :model-value="props.metadataSummary"
          tag="p"
          display-class="text-sm text-navy/70"
          input-class="text-sm"
          placeholder="Lägg till en sammanfattning..."
          :saving="props.isSummarySaving"
          @update:model-value="emit('update:metadataSummary', $event)"
          @commit="emit('commitSummary')"
        />
      </div>

      <div class="text-sm font-medium text-navy/70 shrink-0">
        {{ props.statusLine }}
      </div>
    </div>

    <!-- Workflow context buttons -->
    <div class="border-t border-navy/20 pt-4">
      <WorkflowContextButtons
        :can-submit-review="props.canSubmitReview"
        :submit-review-tooltip="props.submitReviewTooltip"
        :can-publish="props.canPublish"
        :can-request-changes="props.canRequestChanges"
        :can-rollback="props.canRollback"
        :is-submitting="props.isWorkflowSubmitting"
        @action="emit('action', $event)"
      />
    </div>
  </div>
</template>
