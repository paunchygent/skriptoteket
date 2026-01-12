<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

type EditorWorkspaceToolbarProps = {
  isSaving: boolean;
  isReadOnly: boolean;
  hasDirtyChanges: boolean;
  isChatCollapsed: boolean;
  saveLabel: string;
  saveTitle: string;
  changeSummary: string;
  inputSchemaError: string | null;
  settingsSchemaError: string | null;
  hasBlockingSchemaIssues: boolean;
  isCheckpointBusy: boolean;
  lockBadgeLabel: string | null;
  lockBadgeTone: "success" | "neutral";
  aiStatus: "applied" | "undone" | null;
  aiAppliedAt: string | null;
  aiCanUndo: boolean;
  aiUndoDisabledReason: string | null;
  aiCanRedo: boolean;
  aiRedoDisabledReason: string | null;
  aiError: string | null;
};

const props = defineProps<EditorWorkspaceToolbarProps>();

const emit = defineEmits<{
  (event: "save"): void;
  (event: "openHistoryDrawer"): void;
  (event: "createCheckpoint", label: string): void;
  (event: "update:changeSummary", value: string): void;
  (event: "toggleChatCollapsed"): void;
  (event: "undoAi"): void;
  (event: "redoAi"): void;
}>();

const utilityButtonClass =
  "btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none";

const menuButtonClass =
  "btn-ghost w-full justify-start h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-white leading-none";

const isSaveMenuOpen = ref(false);
const saveMenuRef = ref<HTMLElement | null>(null);
const checkpointLabel = ref("");
const isAiMenuOpen = ref(false);
const aiMenuRef = ref<HTMLElement | null>(null);

const isSaveDisabled = computed(
  () =>
    props.isSaving ||
    props.isReadOnly ||
    Boolean(props.inputSchemaError) ||
    Boolean(props.settingsSchemaError) ||
    props.hasBlockingSchemaIssues,
);

const saveBlockers = computed(() => {
  const blockers: string[] = [];
  if (props.isReadOnly) {
    blockers.push("Editorn är låst för redigering.");
  }
  if (props.inputSchemaError) {
    blockers.push("Indata (JSON): ogiltig. Kontrollera “Indata & inställningar”.");
  }
  if (props.settingsSchemaError) {
    blockers.push("Inställningar (JSON): ogiltig. Kontrollera “Indata & inställningar”.");
  }
  if (props.hasBlockingSchemaIssues) {
    blockers.push("Blockerande schemafel. Åtgärda innan du sparar.");
  }
  if (props.isSaving) {
    blockers.push("Sparar...");
  }
  return blockers;
});

function toggleSaveMenu(): void {
  isSaveMenuOpen.value = !isSaveMenuOpen.value;
}

function closeSaveMenu(): void {
  isSaveMenuOpen.value = false;
}

function toggleAiMenu(): void {
  isAiMenuOpen.value = !isAiMenuOpen.value;
}

function closeAiMenu(): void {
  isAiMenuOpen.value = false;
}

function handleCreateCheckpoint(): void {
  emit("createCheckpoint", checkpointLabel.value.trim());
  checkpointLabel.value = "";
  closeSaveMenu();
}

function handleDocumentClick(event: MouseEvent): void {
  const target = event.target as Node | null;
  if (!target) return;
  if (saveMenuRef.value && !saveMenuRef.value.contains(target)) {
    closeSaveMenu();
  }
  if (aiMenuRef.value && !aiMenuRef.value.contains(target)) {
    closeAiMenu();
  }
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    closeSaveMenu();
    closeAiMenu();
  }
}

onMounted(() => {
  document.addEventListener("click", handleDocumentClick);
  document.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleDocumentClick);
  document.removeEventListener("keydown", handleKeydown);
});

const aiPillClass = computed(() => {
  const base =
    "inline-flex items-center h-[28px] px-2 py-1 text-[10px] font-semibold uppercase tracking-wide border leading-none";
  if (props.aiError) {
    return `${base} border-error text-error bg-error/10`;
  }
  if (props.aiStatus === "applied") {
    return `${base} border-success text-success bg-success/10`;
  }
  return `${base} border-navy/30 text-navy/70 bg-canvas/40`;
});

function formatDateTime(value: string | number): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  const formatted = new Intl.DateTimeFormat("sv-SE", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
  return formatted.replace(",", "");
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-3">
    <div class="flex flex-wrap items-center gap-2">
      <div
        ref="saveMenuRef"
        class="relative"
      >
        <button
          type="button"
          :class="utilityButtonClass"
          :aria-expanded="isSaveMenuOpen"
          aria-haspopup="menu"
          aria-label="Spara/Öppna"
          @click="toggleSaveMenu"
        >
          Spara/Öppna
          <span class="ml-1">▾</span>
        </button>
        <div
          v-if="isSaveMenuOpen"
          class="absolute left-0 top-full mt-2 w-[min(320px,90vw)] border border-navy bg-canvas z-[var(--huleedu-z-tooltip)]"
          role="menu"
        >
          <div class="p-3 space-y-3">
            <div class="space-y-2">
              <div class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
                Spara arbetsversion
              </div>
              <div class="space-y-1">
                <label class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
                  Ändringssammanfattning (valfritt)
                </label>
                <input
                  :value="props.changeSummary"
                  class="w-full h-[28px] border border-navy/30 bg-white px-2.5 text-[11px] text-navy shadow-none leading-none"
                  placeholder="T.ex. fixade bugg..."
                  :disabled="props.isReadOnly"
                  @input="emit('update:changeSummary', ($event.target as HTMLInputElement).value)"
                >
              </div>
              <button
                type="button"
                role="menuitem"
                :class="menuButtonClass"
                :disabled="isSaveDisabled"
                :title="props.saveTitle || undefined"
                @click="
                  emit('save');
                  closeSaveMenu();
                "
              >
                {{ props.saveLabel }}
              </button>

              <div
                v-if="isSaveDisabled && saveBlockers.length > 0"
                class="pt-2 space-y-1"
              >
                <div class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
                  Blockerar sparning
                </div>
                <ul class="space-y-0.5 text-[10px] text-navy/60">
                  <li
                    v-for="(blocker, idx) in saveBlockers"
                    :key="idx"
                  >
                    • {{ blocker }}
                  </li>
                </ul>
              </div>
            </div>

            <div class="border-t border-navy/20 pt-3 space-y-2">
              <div class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
                Återställningspunkt
              </div>
              <div class="space-y-1">
                <label class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
                  Namn (valfritt)
                </label>
                <input
                  v-model="checkpointLabel"
                  class="w-full h-[28px] border border-navy/30 bg-white px-2.5 text-[11px] text-navy shadow-none leading-none"
                  placeholder="T.ex. före refactor"
                  :disabled="props.isReadOnly"
                >
              </div>
              <button
                type="button"
                role="menuitem"
                :class="menuButtonClass"
                :disabled="props.isReadOnly || props.isCheckpointBusy"
                @click="handleCreateCheckpoint"
              >
                Spara ny återställningspunkt
              </button>
            </div>

            <div class="border-t border-navy/20 pt-3 space-y-2">
              <div class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
                Öppna
              </div>
              <button
                type="button"
                role="menuitem"
                :class="menuButtonClass"
                @click="
                  emit('openHistoryDrawer');
                  closeSaveMenu();
                "
              >
                Öppna sparade
              </button>
            </div>
          </div>
        </div>
      </div>

      <button
        type="button"
        class="btn-ghost h-[28px] w-[28px] p-0 text-[12px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none lg:hidden"
        :aria-label="props.isChatCollapsed ? 'Öppna kodassistenten' : 'Stäng kodassistenten'"
        @click="emit('toggleChatCollapsed')"
      >
        <svg
          viewBox="0 0 24 24"
          class="h-4 w-4"
          aria-hidden="true"
        >
          <rect
            x="5"
            y="7"
            width="14"
            height="10"
            rx="2"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
          />
          <circle
            cx="9"
            cy="12"
            r="1"
            fill="currentColor"
          />
          <circle
            cx="15"
            cy="12"
            r="1"
            fill="currentColor"
          />
          <path
            d="M9 16h6"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
          />
          <path
            d="M8 5h8"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
          />
        </svg>
      </button>

      <div
        v-if="props.aiStatus"
        ref="aiMenuRef"
        class="relative flex items-center gap-1 shrink-0"
      >
        <button
          type="button"
          :class="aiPillClass"
          :aria-expanded="isAiMenuOpen"
          aria-haspopup="menu"
          aria-label="AI-ändring"
          @click="toggleAiMenu"
        >
          AI
        </button>

        <button
          type="button"
          class="btn-ghost h-[28px] w-[28px] p-0 text-[12px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none"
          :disabled="!props.aiCanUndo"
          :title="props.aiUndoDisabledReason || undefined"
          aria-label="Ångra AI-ändring"
          @click="emit('undoAi')"
        >
          ↶
        </button>

        <button
          type="button"
          class="btn-ghost h-[28px] w-[28px] p-0 text-[12px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none"
          :disabled="!props.aiCanRedo"
          :title="props.aiRedoDisabledReason || undefined"
          aria-label="Återställ AI-ändring"
          @click="emit('redoAi')"
        >
          ↷
        </button>

        <div
          v-if="isAiMenuOpen"
          class="absolute left-0 top-full mt-2 w-[min(320px,90vw)] border border-navy bg-canvas z-[var(--huleedu-z-tooltip)]"
          role="menu"
        >
          <div class="p-3 space-y-2">
            <div class="space-y-1">
              <div class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
                AI-ändring
              </div>
              <div class="text-[11px] text-navy/70">
                <span class="font-semibold">
                  {{ props.aiStatus === "applied" ? "Tillämpad" : "Återställd" }}
                </span>
                <span
                  v-if="props.aiAppliedAt"
                  class="text-navy/60"
                >
                  · {{ formatDateTime(props.aiAppliedAt) }}
                </span>
              </div>
            </div>

            <div
              v-if="props.aiError"
              class="border border-error/30 bg-error/10 px-2 py-1 text-[11px] text-error"
            >
              {{ props.aiError }}
            </div>

            <p class="text-[11px] text-navy/60">
              Återställningspunkt finns i “Öppna sparade”.
            </p>
          </div>
        </div>
      </div>

      <span
        v-if="props.hasDirtyChanges"
        class="text-[10px] text-burgundy font-semibold uppercase tracking-wide"
      >
        Osparat
      </span>

      <span
        v-if="props.lockBadgeLabel"
        class="inline-flex items-center h-[28px] px-2 py-1 text-[10px] font-semibold uppercase tracking-wide border leading-none"
        :class="props.lockBadgeTone === 'success'
          ? 'border-success text-success bg-success/10'
          : 'border-navy/30 text-navy/70 bg-canvas/40'"
      >
        {{ props.lockBadgeLabel }}
      </span>
    </div>
  </div>
</template>
