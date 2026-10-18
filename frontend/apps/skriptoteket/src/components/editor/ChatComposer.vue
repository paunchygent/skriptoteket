<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { UiDenseActionButton, UiDenseIconButton, UiSegmentedToggle } from "../ui";
import { UiGlyph } from "../ui/shared";

type ChatComposerProps = {
  isStreaming: boolean;
  isEditOpsLoading: boolean;
  assistantActivity?: "thinking" | "writing" | null;
  canClear?: boolean;
  editOpsIsSlow?: boolean;
  clearDraftToken?: number;
  aiBlockedNote?: string | null;
};

const props = withDefaults(defineProps<ChatComposerProps>(), {
  assistantActivity: null,
  canClear: false,
  editOpsIsSlow: false,
  clearDraftToken: 0,
  aiBlockedNote: null,
});

const emit = defineEmits<{
  (event: "send", message: string): void;
  (event: "requestEditOps", message: string): void;
  (event: "cancel"): void;
  (event: "clear"): void;
}>();

type ChatComposerMode = "chat" | "edit";

const mode = ref<ChatComposerMode>("chat");
const modeOptions = [
  { value: "chat", label: "Chat" },
  { value: "edit", label: "Edit" },
];
const draft = ref("");
const textarea = ref<HTMLTextAreaElement | null>(null);

const canSubmit = computed(
  () =>
    !props.isStreaming &&
    !props.isEditOpsLoading &&
    !props.aiBlockedNote &&
    draft.value.trim().length > 0,
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
  if (props.aiBlockedNote) {
    return;
  }
  const message = draft.value.trim();
  if (!message || props.isStreaming || props.isEditOpsLoading) {
    return;
  }
  emit("send", message);
  draft.value = "";
}

function handleRequestEditOps(): void {
  if (props.aiBlockedNote) {
    return;
  }
  const message = draft.value.trim();
  if (!message || props.isStreaming || props.isEditOpsLoading) {
    return;
  }
  emit("requestEditOps", message);
}

function handleSubmit(): void {
  if (props.aiBlockedNote) {
    return;
  }
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
        aria-label="Meddelande till kodassistenten"
        class="w-full resize-none border border-navy/30 bg-panel px-3 py-2 pr-10 text-sm text-navy shadow-none"
        :placeholder="mode === 'chat' ? 'Fråga mig vad du vill' : 'Beskriv vad du vill ändra...'"
        :disabled="props.isStreaming || Boolean(props.aiBlockedNote)"
        @keydown="handleKeydown"
      />

      <UiDenseIconButton
        :label="primaryActionLabel"
        class="absolute bottom-2 right-2"
        :disabled="!canSubmit"
        @click="handleSubmit"
      >
        <UiGlyph
          meaning="send"
          :size="16"
          class="h-4 w-4"
          aria-hidden="true"
        />
      </UiDenseIconButton>
    </div>

    <div class="flex flex-wrap items-center justify-between gap-2">
      <UiSegmentedToggle
        :model-value="mode"
        :options="modeOptions"
        aria-label="Läge"
        density="compact"
        width="auto"
        :disabled="props.isStreaming || props.isEditOpsLoading"
        @update:model-value="mode = $event as ChatComposerMode"
      />

      <div class="flex items-center gap-2">
        <UiDenseActionButton
          v-if="props.isStreaming"
          label="Avbryt"
          @click="emit('cancel')"
        />

        <UiDenseActionButton
          label="Ny chatt"
          :disabled="!props.canClear || props.isStreaming || props.isEditOpsLoading"
          @click="emit('clear')"
        />
      </div>
    </div>

    <p
      v-if="props.aiBlockedNote"
      class="text-[10px] text-navy/60"
      data-testid="editor-ai-admin-only-note"
    >
      {{ props.aiBlockedNote }}
    </p>

    <div class="text-[10px] text-navy/60">
      <template v-if="props.isStreaming">
        {{ props.assistantActivity === "writing" ? "Skriver..." : "Tänker..." }}
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
