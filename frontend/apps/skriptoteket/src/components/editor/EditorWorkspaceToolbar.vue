<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

type EditorWorkspaceToolbarProps = {
  isSaving: boolean;
  isReadOnly: boolean;
  hasDirtyChanges: boolean;
  saveLabel: string;
  saveTitle: string;
  changeSummary: string;
  inputSchemaError: string | null;
  settingsSchemaError: string | null;
  hasBlockingSchemaIssues: boolean;
  isCheckpointBusy: boolean;
  lockBadgeLabel: string | null;
  lockBadgeTone: "success" | "neutral";
};

const props = defineProps<EditorWorkspaceToolbarProps>();

const emit = defineEmits<{
  (event: "save"): void;
  (event: "openHistoryDrawer"): void;
  (event: "createCheckpoint"): void;
  (event: "update:changeSummary", value: string): void;
}>();

const utilityButtonClass =
  "btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none";

const isSaveMenuOpen = ref(false);
const saveMenuRef = ref<HTMLElement | null>(null);

const isSaveDisabled = computed(
  () =>
    props.isSaving ||
    props.isReadOnly ||
    Boolean(props.inputSchemaError) ||
    Boolean(props.settingsSchemaError) ||
    props.hasBlockingSchemaIssues,
);

function toggleSaveMenu(): void {
  isSaveMenuOpen.value = !isSaveMenuOpen.value;
}

function closeSaveMenu(): void {
  isSaveMenuOpen.value = false;
}

function handleDocumentClick(event: MouseEvent): void {
  const target = event.target as Node | null;
  if (!target || !saveMenuRef.value) return;
  if (!saveMenuRef.value.contains(target)) {
    closeSaveMenu();
  }
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    closeSaveMenu();
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
          class="absolute left-0 top-full mt-2 w-[min(320px,90vw)] border border-navy bg-canvas shadow-brutal-sm z-20"
          role="menu"
        >
          <div class="p-3 space-y-3">
            <div class="space-y-2">
              <div class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
                Spara
              </div>
              <button
                type="button"
                role="menuitem"
                class="w-full text-left px-3 py-2 text-xs text-navy border border-navy/30 bg-white shadow-brutal-sm hover:bg-canvas transition-colors"
                :disabled="isSaveDisabled"
                :title="props.saveTitle || undefined"
                @click="
                  emit('save');
                  closeSaveMenu();
                "
              >
                {{ props.saveLabel }}
              </button>
              <div class="space-y-1">
                <label class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
                  Ändringssammanfattning
                </label>
                <input
                  :value="props.changeSummary"
                  class="w-full border border-navy bg-white px-2.5 py-2 text-xs text-navy shadow-brutal-sm"
                  placeholder="T.ex. fixade bugg..."
                  :disabled="props.isReadOnly"
                  @input="emit('update:changeSummary', ($event.target as HTMLInputElement).value)"
                >
              </div>
              <button
                type="button"
                role="menuitem"
                class="w-full text-left px-3 py-2 text-xs text-navy border border-navy/30 bg-white shadow-brutal-sm hover:bg-canvas transition-colors"
                :disabled="props.isReadOnly || props.isCheckpointBusy"
                @click="
                  emit('createCheckpoint');
                  closeSaveMenu();
                "
              >
                Skapa lokal återställningspunkt
              </button>
            </div>

            <div class="border-t border-navy/20 pt-3 space-y-2">
              <div class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
                Öppna
              </div>
              <button
                type="button"
                role="menuitem"
                class="w-full text-left px-3 py-2 text-xs text-navy border border-navy/30 bg-white shadow-brutal-sm hover:bg-canvas transition-colors"
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
