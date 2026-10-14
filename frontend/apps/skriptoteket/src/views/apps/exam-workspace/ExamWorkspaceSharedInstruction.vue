<script setup lang="ts">
/**
 * Read-only shared instruction.
 *
 * Domain purpose:
 *   Show a shared instruction exactly as its native body paragraphs read:
 *   text and pictures in order, with a known picture rendered from its
 *   protected document URL and an unknown one as the "Bild" placeholder.
 *   Nothing here is editable and no markup is interpreted, so the exam-wide
 *   instructions and a parent's shared stem cannot become question atoms or
 *   inject content into the list.
 *
 * Relationships:
 *   - Receives paragraphs resolved by `examWorkspaceSharedParagraphs` through
 *     `examWorkspaceParents` and `examWorkspaceRows`.
 *   - Rendered by `ExamWorkspaceItemTable` in the once-only parent header.
 */

import type { ExamWorkspaceSharedParagraph } from "./examWorkspaceSharedInstruction";

defineProps<{
  paragraphs: ExamWorkspaceSharedParagraph[];
}>();

/** Visible label of a picture whose protected URL is not loaded. */
const PICTURE_PLACEHOLDER_LABEL = "Bild";
</script>

<template>
  <div
    class="grid gap-1"
    data-test="exam-workspace-shared-instruction"
  >
    <p
      v-for="(paragraph, paragraphIndex) in paragraphs"
      :key="paragraphIndex"
      class="m-0 whitespace-pre-wrap"
      data-test="exam-workspace-shared-instruction-paragraph"
    >
      <template
        v-for="(part, partIndex) in paragraph.parts"
        :key="partIndex"
      >
        <span v-if="part.kind === 'text'">{{ part.text }}</span>
        <img
          v-else-if="part.url"
          alt=""
          :data-asset-id="part.assetId"
          :src="part.url"
          class="my-1 inline-block h-auto max-w-full align-middle"
          data-test="exam-workspace-shared-instruction-image"
        >
        <span
          v-else
          :data-asset-id="part.assetId"
          class="inline-block border border-navy/35 bg-panel-muted px-2 align-baseline text-sm text-navy"
          data-test="exam-workspace-shared-instruction-placeholder"
        >{{ PICTURE_PLACEHOLDER_LABEL }}</span>
      </template>
    </p>
  </div>
</template>
