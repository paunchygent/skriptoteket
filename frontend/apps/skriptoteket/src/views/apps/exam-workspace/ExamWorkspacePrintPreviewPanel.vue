<script setup lang="ts">
/**
 * Exam workspace Förhandsgranska panel.
 *
 * Domain purpose:
 *   Show the saved student print copy beside the editor as one image per
 *   printed page (W5). The last ready pages stay visible while a new render
 *   runs or the exam cannot be rendered, and the panel scrolls to the
 *   selected question's first page. It holds no render state; the view owns
 *   that through `useExamWorkspacePrintPreview`.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` inside `.ws__body`, after the editor
 *     pane; state and transport come from `useExamWorkspacePrintPreview`.
 */

import { computed, nextTick, ref, watch } from "vue";

import { UiGlyph } from "../../../components/ui";

const props = defineProps<{
  pages: string[];
  /** Question item id -> 0-based page its first printed page sits on. */
  questionPages: Record<string, number>;
  loading: boolean;
  blocked: boolean;
  message: string | null;
  selectedItemId: string | null;
}>();

const emit = defineEmits<{ close: [] }>();

const scrollArea = ref<HTMLElement | null>(null);

/** The one status line under the panel's head, or null when the pages speak for themselves. */
const status = computed(() => {
  if (props.loading) {
    return props.pages.length > 0 ? "Uppdaterar …" : "Skapar förhandsgranskning …";
  }
  if (props.blocked) {
    return props.pages.length > 0
      ? "Förhandsgranskningen visar den senaste utskriften."
      : "Förhandsgranskningen visas när provet går att skriva ut.";
  }
  return null;
});

function scrollToSelectedPage(): void {
  if (props.selectedItemId === null) return;
  const page = props.questionPages[props.selectedItemId];
  if (page === undefined) return;
  const target = scrollArea.value?.querySelector<HTMLElement>(`[data-page-index="${page}"]`);
  target?.scrollIntoView({ block: "start" });
}

// The selected question's page, or a new render, moves the preview to it.
watch(
  () => [props.selectedItemId, props.pages] as const,
  async () => {
    await nextTick();
    scrollToSelectedPage();
  },
  { immediate: true },
);
</script>

<template>
  <aside
    class="pp"
    role="complementary"
    aria-label="Förhandsgranska"
    data-test="exam-workspace-print-preview"
  >
    <div class="pp__head">
      <h2 class="pp__title">
        Förhandsgranska
      </h2>
      <button
        type="button"
        class="xw-btn xw-btn--icon xw-btn--ghost"
        aria-label="Stäng förhandsgranskningen"
        title="Stäng"
        data-test="exam-workspace-print-preview-close"
        @click="emit('close')"
      >
        <UiGlyph
          meaning="close"
          :size="20"
        />
      </button>
    </div>
    <div
      ref="scrollArea"
      class="pp__body"
    >
      <p
        v-if="status"
        class="pp__status"
        role="status"
        data-test="exam-workspace-print-preview-status"
      >
        {{ status }}
      </p>
      <p
        v-if="message"
        class="pp__detail"
        data-test="exam-workspace-print-preview-message"
      >
        {{ message }}
      </p>
      <img
        v-for="(page, index) in pages"
        :key="index"
        class="pp__page"
        :src="page"
        :alt="`Sida ${index + 1}`"
        :data-page-index="index"
      >
    </div>
  </aside>
</template>

<style scoped>
.pp {
  display: flex; flex-direction: column; min-height: 0;
  border-left: 1px solid var(--huleedu-surface-divider); background: var(--huleedu-canvas);
}
.pp__head {
  display: flex; align-items: center; gap: var(--huleedu-space-3); flex: none; height: 52px;
  padding: 0 var(--huleedu-space-3) 0 var(--huleedu-space-5); border-bottom: 1px solid var(--huleedu-surface-divider);
}
.pp__title { flex: 1; margin: 0; font-size: var(--huleedu-text-base); font-weight: var(--huleedu-font-semibold); }
.pp__body {
  display: grid; align-content: start; gap: var(--huleedu-space-4); flex: 1; min-height: 0; overflow-y: auto;
  padding: var(--huleedu-space-5);
}
.pp__status { margin: 0; font-size: var(--huleedu-text-sm); color: var(--huleedu-navy-60); }
.pp__detail { margin: 0; font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-60); }
.pp__page {
  display: block; width: 100%; height: auto; border: 1px solid var(--huleedu-panel-border);
  border-radius: var(--huleedu-radius-md); background: var(--huleedu-surface-content);
}
/* Tablets have no room for a third column, so the panel floats over the editor like the drawer. */
@media (max-width: 1279px) {
  .pp {
    position: absolute; top: 12px; right: 12px; bottom: 12px; z-index: 12; overflow: hidden;
    width: min(var(--xw-drawer, 380px), calc(100% - 24px));
    border: 1px solid var(--huleedu-panel-border); border-radius: var(--huleedu-radius-xl);
    background: var(--huleedu-modal); box-shadow: var(--huleedu-shadow-md);
  }
}
</style>
