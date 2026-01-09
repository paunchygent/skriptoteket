<script setup lang="ts">
import { computed } from "vue";

import type { EditOpsPanelState } from "../../composables/editor/useEditorEditOps";
import { virtualFileLabel } from "../../composables/editor/virtualFiles";
import VirtualFileDiffViewer from "./diff/VirtualFileDiffViewer.vue";

const props = defineProps<{
  state: EditOpsPanelState;
}>();

const emit = defineEmits<{
  (event: "apply"): void;
  (event: "discard"): void;
  (event: "regenerate"): void;
  (event: "undo"): void;
}>();

const hasProposal = computed(() => Boolean(props.state.proposal));
const hasUndo = computed(() => props.state.hasUndoSnapshot && !props.state.proposal);
const summaryText = computed(
  () => props.state.proposal?.assistantMessage?.trim() || "AI-förslaget är redo att granskas.",
);
const staleLabel = computed(() => {
  if (!props.state.isStale || props.state.staleFiles.length === 0) return "";
  return props.state.staleFiles.map((fileId) => virtualFileLabel(fileId)).join(", ");
});
const showRegenerate = computed(() => props.state.isStale || Boolean(props.state.previewError));
const applyDisabledReason = computed(() => props.state.applyDisabledReason ?? "");
const undoDisabledReason = computed(() => props.state.undoDisabledReason ?? "");
</script>

<template>
  <section
    v-if="hasProposal || hasUndo"
    class="border border-navy/30 bg-canvas/40 px-3 py-3 space-y-3"
  >
    <div
      v-if="hasProposal"
      class="space-y-3"
    >
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0 space-y-1">
          <p class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
            AI-f&ouml;rslag
          </p>
          <p class="text-sm text-navy/80">
            {{ summaryText }}
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <button
            type="button"
            class="btn-cta h-[28px] px-3 py-1 text-[11px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)]"
            :disabled="!props.state.canApply"
            @click="emit('apply')"
          >
            Anv&auml;nd
          </button>
          <button
            type="button"
            class="btn-ghost h-[28px] px-3 py-1 text-[11px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas shadow-none"
            @click="emit('discard')"
          >
            Kasta
          </button>
          <button
            v-if="showRegenerate"
            type="button"
            class="btn-ghost h-[28px] px-3 py-1 text-[11px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas shadow-none"
            @click="emit('regenerate')"
          >
            Regenerera
          </button>
        </div>
      </div>

      <div
        v-if="props.state.previewError"
        class="p-3 border border-burgundy bg-white text-sm text-burgundy shadow-brutal-sm"
      >
        {{ props.state.previewError }}
      </div>

      <div
        v-if="props.state.applyError"
        class="p-3 border border-burgundy bg-white text-sm text-burgundy shadow-brutal-sm"
      >
        {{ props.state.applyError }}
      </div>

      <div
        v-if="props.state.isStale"
        class="p-3 border border-navy/30 bg-white text-sm text-navy/70 shadow-brutal-sm"
      >
        F&ouml;rslaget &auml;r utdaterat. F&ouml;ljande filer har &auml;ndrats:
        <span class="font-semibold text-navy">{{ staleLabel }}</span>. Regenerera f&ouml;r att forts&auml;tta.
      </div>

      <div
        v-if="applyDisabledReason && !props.state.canApply && !props.state.isStale && !props.state.previewError"
        class="text-xs text-navy/60"
      >
        {{ applyDisabledReason }}
      </div>

      <div
        v-if="props.state.diffItems.length > 0"
        class="border border-navy/20 bg-white shadow-brutal-sm h-[320px] min-h-[240px]"
      >
        <VirtualFileDiffViewer
          :items="props.state.diffItems"
          before-label="Nuvarande"
          after-label="F&ouml;rslag"
        />
      </div>
      <div
        v-else
        class="p-3 border border-navy/20 bg-white text-sm text-navy/70 shadow-brutal-sm"
      >
        Ingen diff att visa.
      </div>
    </div>

    <div
      v-else-if="hasUndo"
      class="space-y-2"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="min-w-0 space-y-1">
          <p class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
            AI-&auml;ndring
          </p>
          <p class="text-sm text-navy/80">
            Senaste AI-f&ouml;rslaget &auml;r till&auml;mpat.
          </p>
        </div>
        <button
          type="button"
          class="btn-ghost h-[28px] px-3 py-1 text-[11px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas shadow-none"
          :disabled="!props.state.canUndo"
          @click="emit('undo')"
        >
          &Aring;ngra
        </button>
      </div>

      <div
        v-if="props.state.undoError"
        class="p-3 border border-burgundy bg-white text-sm text-burgundy shadow-brutal-sm"
      >
        {{ props.state.undoError }}
      </div>

      <div
        v-if="undoDisabledReason && !props.state.canUndo"
        class="p-3 border border-navy/30 bg-white text-sm text-navy/70 shadow-brutal-sm"
      >
        {{ undoDisabledReason }}
      </div>
    </div>
  </section>
</template>
