<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch, withDefaults } from "vue";

type ChatComposerProps = {
  isStreaming: boolean;
  isEditOpsLoading: boolean;
  canClear?: boolean;
  editOpsIsSlow?: boolean;
  clearDraftToken?: number;
};

const props = withDefaults(defineProps<ChatComposerProps>(), {
  canClear: false,
  editOpsIsSlow: false,
  clearDraftToken: 0,
});

const emit = defineEmits<{
  (event: "send", message: string): void;
  (event: "requestEditOps", message: string): void;
  (event: "cancel"): void;
  (event: "clear"): void;
}>();

type ChatComposerMode = "chat" | "edit";

const mode = ref<ChatComposerMode>("chat");
const draft = ref("");
const textarea = ref<HTMLTextAreaElement | null>(null);

const canSubmit = computed(
  () => !props.isStreaming && !props.isEditOpsLoading && draft.value.trim().length > 0,
);

const primaryActionLabel = computed(() => (mode.value === "chat" ? "Skicka" : "Föreslå ändringar"));

function resetDraftTextarea(): void {
  const element = textarea.value;
  if (!element) {
    return;
  }
  element.style.height = "";
  element.style.overflowY = "";
}

function resizeDraftTextarea(): void {
  const element = textarea.value;
  if (!element) {
    return;
  }

  if (!draft.value) {
    resetDraftTextarea();
    return;
  }

  element.style.height = "auto";
  const maxHeightPx = 260;
  const nextHeight = Math.min(element.scrollHeight, maxHeightPx);
  element.style.height = `${nextHeight}px`;
  element.style.overflowY = element.scrollHeight > maxHeightPx ? "auto" : "hidden";
}

function handleSend(): void {
  const message = draft.value.trim();
  if (!message || props.isStreaming || props.isEditOpsLoading) {
    return;
  }
  emit("send", message);
  draft.value = "";
}

function handleRequestEditOps(): void {
  const message = draft.value.trim();
  if (!message || props.isStreaming || props.isEditOpsLoading) {
    return;
  }
  emit("requestEditOps", message);
}

function handleSubmit(): void {
  if (mode.value === "chat") {
    handleSend();
    return;
  }
  handleRequestEditOps();
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    handleSubmit();
  }
}

onMounted(() => {
  resetDraftTextarea();
});

watch(
  () => draft.value,
  async () => {
    await nextTick();
    resizeDraftTextarea();
  },
  { flush: "post" },
);

watch(
  () => props.clearDraftToken,
  async () => {
    draft.value = "";
    await nextTick();
    resetDraftTextarea();
  },
);
</script>

<template>
  <div class="space-y-2">
    <div class="relative">
      <textarea
        ref="textarea"
        v-model="draft"
        rows="2"
        class="w-full resize-none border border-navy/30 bg-white px-3 py-2 pr-10 text-sm text-navy shadow-none"
        :placeholder="mode === 'chat' ? 'Fråga mig vad du vill' : 'Beskriv vad du vill ändra...'"
        :disabled="props.isStreaming"
        @keydown="handleKeydown"
      />

      <button
        type="button"
        class="absolute bottom-2 right-2 inline-flex h-7 w-7 items-center justify-center text-navy/70 hover:text-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy/40 disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="!canSubmit"
        :aria-label="primaryActionLabel"
        @click="handleSubmit"
      >
        <svg
          viewBox="0 0 24 24"
          class="h-4 w-4"
          aria-hidden="true"
        >
          <path
            d="M20.9 11.3L4.6 3.2c-.6-.3-1.3.2-1.2.9l1.1 6.2c.1.4.4.8.9.9l7.1 1.1-7.1 1.1c-.4.1-.8.4-.9.9l-1.1 6.2c-.1.7.6 1.2 1.2.9l16.3-8.1c.7-.3.7-1.3 0-1.6z"
            fill="currentColor"
          />
        </svg>
      </button>
    </div>

    <div class="flex flex-wrap items-center justify-between gap-2">
      <div
        class="relative inline-grid grid-cols-2 overflow-hidden border border-navy/30 bg-white"
        role="tablist"
        aria-label="Läge"
      >
        <span
          class="absolute inset-y-0 left-0 w-1/2 bg-navy transition-transform"
          :class="mode === 'chat' ? 'translate-x-0' : 'translate-x-full'"
          style="transition-timing-function: var(--huleedu-ease-default, ease);"
          aria-hidden="true"
        />
        <span
          class="absolute inset-y-0 left-1/2 w-px bg-navy/20"
          aria-hidden="true"
        />

        <button
          type="button"
          role="tab"
          :aria-selected="mode === 'chat'"
          class="relative z-10 px-2 py-1 text-[10px] font-semibold tracking-[var(--huleedu-tracking-label)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy/40"
          :class="mode === 'chat' ? 'text-canvas' : 'text-navy/70 hover:text-navy'"
          :disabled="props.isStreaming || props.isEditOpsLoading"
          @click="mode = 'chat'"
        >
          Chat
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="mode === 'edit'"
          class="relative z-10 px-2 py-1 text-[10px] font-semibold tracking-[var(--huleedu-tracking-label)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-navy/40"
          :class="mode === 'edit' ? 'text-canvas' : 'text-navy/70 hover:text-navy'"
          :disabled="props.isStreaming || props.isEditOpsLoading"
          @click="mode = 'edit'"
        >
          Edit
        </button>
      </div>

      <div class="flex items-center gap-2">
        <button
          v-if="props.isStreaming"
          type="button"
          class="btn-ghost shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas leading-none"
          @click="emit('cancel')"
        >
          Avbryt
        </button>

        <button
          type="button"
          class="btn-ghost shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas leading-none"
          :disabled="!props.canClear || props.isStreaming || props.isEditOpsLoading"
          @click="emit('clear')"
        >
          Ny chatt
        </button>
      </div>
    </div>

    <div class="text-[10px] text-navy/60">
      <template v-if="props.isStreaming">
        AI skriver...
      </template>
      <template v-else-if="props.isEditOpsLoading">
        <span>Skapar förslag...</span>
        <span
          v-if="props.editOpsIsSlow"
          class="block pt-1 text-navy/50"
        >
          Tar lite längre tid än vanligt. Lokala modeller kan ta upp till ~2 min.
        </span>
      </template>
      <template v-else>
        Enter skickar, Shift+Enter ny rad.
      </template>
    </div>
  </div>
</template>
