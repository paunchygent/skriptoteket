<script setup lang="ts">
import { computed, ref } from "vue";

import type { EditOpsPanelState } from "../../composables/editor/useEditorEditOps";
import AiVirtualFileDiffViewer from "./diff/AiVirtualFileDiffViewer.vue";

const props = defineProps<{
  state: EditOpsPanelState;
}>();

const emit = defineEmits<{
  (event: "apply"): void;
  (event: "discard"): void;
  (event: "regenerate"): void;
  (event: "setConfirmationAccepted", value: boolean): void;
}>();

const hasProposal = computed(() => Boolean(props.state.proposal));
const summaryText = computed(
  () => props.state.proposal?.assistantMessage?.trim() || "AI-förslaget är redo att granskas.",
);
const showRegenerate = computed(() => Boolean(props.state.previewError) || Boolean(props.state.applyError));
const applyDisabledReason = computed(() => props.state.applyDisabledReason ?? "");
const requiresConfirmation = computed(() => props.state.requiresConfirmation);
const fuzzLevel = computed(() => props.state.previewMeta?.fuzz_level_used ?? 0);
const maxOffset = computed(() => props.state.previewMeta?.max_offset ?? 0);
const normalizations = computed(() => props.state.previewMeta?.normalizations_applied ?? []);

function updateConfirmationAccepted(event: Event): void {
  emit("setConfirmationAccepted", (event.target as HTMLInputElement).checked);
}

const showDebug = ref(false);

async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
    return;
  } catch {
    // fall back to legacy clipboard API (best effort)
  }

  try {
    const element = document.createElement("textarea");
    element.value = text;
    element.setAttribute("readonly", "true");
    element.style.position = "absolute";
    element.style.left = "-9999px";
    document.body.appendChild(element);
    element.select();
    document.execCommand("copy");
    document.body.removeChild(element);
  } catch {
    // ignore clipboard failures
  }
}
</script>

<template>
  <section
    v-if="hasProposal"
    class="border border-navy/30 bg-white px-3 py-3 space-y-3"
  >
    <div class="space-y-3">
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
          <span
            v-if="props.state.proposal?.correlationId"
            class="relative inline-flex group"
          >
            <button
              type="button"
              class="btn-ghost h-[28px] px-2 py-1 text-[11px] font-mono normal-case border-navy/30 bg-canvas shadow-none text-navy/70"
              :aria-expanded="showDebug"
              aria-label="Visa correlation-id"
              @click="showDebug = !showDebug"
            >
              ...
            </button>
            <span
              class="pointer-events-none absolute right-0 top-full z-10 mt-1 whitespace-nowrap border border-navy/30 bg-white px-2 py-1 text-[10px] text-navy/70 opacity-0 shadow-brutal-sm transition-opacity group-hover:opacity-100"
              aria-hidden="true"
            >
              Visa correlation-id
            </span>
          </span>
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
        v-if="showDebug && props.state.proposal?.correlationId"
        class="border border-navy/20 bg-white px-3 py-2 text-[10px] text-navy/70"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="font-mono break-all">correlation-id: {{ props.state.proposal.correlationId }}</span>
          <button
            type="button"
            class="text-[10px] font-semibold text-navy/60 hover:text-navy"
            @click="copyText(props.state.proposal.correlationId)"
          >
            Kopiera
          </button>
        </div>
      </div>

      <div
        v-if="props.state.previewError"
        class="p-3 border border-error bg-error/10 text-sm text-error"
      >
        <p>{{ props.state.previewError }}</p>
        <details
          v-if="props.state.previewErrorDetails"
          class="mt-2"
        >
          <summary class="cursor-pointer text-xs text-error/90">
            Visa detaljer
          </summary>
          <div class="mt-2 space-y-2">
            <p
              v-if="props.state.previewErrorDetails.hunk_header"
              class="text-[11px] font-mono text-error/90 break-words"
            >
              {{ props.state.previewErrorDetails.hunk_header }}
            </p>
            <pre
              v-if="props.state.previewErrorDetails.expected_snippet"
              class="text-[11px] whitespace-pre-wrap border border-error/30 bg-white/60 p-2"
            ><code>{{ props.state.previewErrorDetails.expected_snippet }}</code></pre>
            <pre
              v-if="props.state.previewErrorDetails.base_snippet"
              class="text-[11px] whitespace-pre-wrap border border-error/30 bg-white/60 p-2"
            ><code>{{ props.state.previewErrorDetails.base_snippet }}</code></pre>
          </div>
        </details>
      </div>

      <div
        v-if="props.state.applyError"
        class="p-3 border border-error bg-error/10 text-sm text-error"
      >
        {{ props.state.applyError }}
      </div>

      <div
        v-if="requiresConfirmation && props.state.previewMeta"
        class="p-3 border border-warning bg-warning/10 text-sm text-navy space-y-2"
      >
        <p class="font-semibold">
          Granska extra noga
        </p>
        <p class="text-xs text-navy/80">
          Förhandsvisningen använde <span class="font-semibold">fuzz={{ fuzzLevel }}</span> och
          <span class="font-semibold">förskjutning={{ maxOffset }} rader</span>.
        </p>
        <p
          v-if="normalizations.length > 0"
          class="text-xs text-navy/70"
        >
          Normaliseringar: {{ normalizations.join(", ") }}.
        </p>
        <label class="flex items-start gap-2 text-xs text-navy/80">
          <input
            type="checkbox"
            class="mt-0.5"
            :checked="props.state.confirmationAccepted"
            :disabled="props.state.isApplying"
            @change="updateConfirmationAccepted"
          >
          <span>Jag har granskat ändringen och vill använda den.</span>
        </label>
      </div>

      <div
        v-if="applyDisabledReason && !props.state.canApply && !props.state.previewError"
        class="text-xs text-navy/60"
      >
        {{ applyDisabledReason }}
      </div>

      <div
        v-if="props.state.diffItems.length > 0"
        class="h-[320px] min-h-[240px]"
      >
        <AiVirtualFileDiffViewer
          :items="props.state.diffItems"
          before-label="Nuvarande"
          after-label="F&ouml;rslag"
        />
      </div>
      <div
        v-else
        class="p-3 panel-inset-canvas text-sm text-navy/70"
      >
        Ingen diff att visa.
      </div>
    </div>
  </section>
</template>
