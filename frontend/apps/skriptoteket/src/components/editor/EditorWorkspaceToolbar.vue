<script setup lang="ts">
/**
 * Dense workspace toolbar for the script editor.
 *
 * Relationships:
 * - consumes the shared dense-tool primitives introduced in PR-0157
 * - keeps editor-specific save/open and AI status content local while reading shared button/menu contracts
 */

import { computed, ref } from "vue";

import { IconRedo, IconUndo } from "../icons";
import {
  DENSE_FORM_INPUT_CLASS,
  DENSE_MENU_PANEL_CLASS,
  DENSE_MENU_SECTION_LABEL_CLASS,
  UiDenseIconButton,
  UiDenseMenuButton,
  UiDenseStatusPill,
  denseStatusPillClass,
  denseMenuItemClass,
  type DenseStatusTone,
} from "../ui";
import { useDenseMenuSurface } from "../ui/useDenseMenuSurface";

import EditorToolMenu from "./EditorToolMenu.vue";

type EditorWorkspaceToolbarProps = {
  toolId: string;
  toolTitle: string;
  toolSlug: string;
  canCreateTool: boolean;
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

const isSaveMenuOpen = ref(false);
const saveMenuContainerRef = ref<HTMLElement | null>(null);
const saveMenuRef = ref<HTMLElement | null>(null);
const saveMenuTriggerRef = ref<InstanceType<typeof UiDenseMenuButton> | null>(null);
const checkpointLabel = ref("");
const isAiMenuOpen = ref(false);
const aiMenuContainerRef = ref<HTMLElement | null>(null);
const aiMenuRef = ref<HTMLElement | null>(null);
const aiMenuTriggerRef = ref<HTMLButtonElement | null>(null);

const {
  closeMenu: closeSaveMenu,
  toggleMenu: toggleSaveMenu,
  onTriggerKeydown: onSaveTriggerKeydown,
  onMenuKeydown: onSaveMenuKeydown,
} = useDenseMenuSurface({
  isOpen: isSaveMenuOpen,
  containerRef: saveMenuContainerRef,
  menuRef: saveMenuRef,
  triggerRef: saveMenuTriggerRef,
});

const { toggleMenu: toggleAiMenu, onMenuKeydown: onAiMenuKeydown } = useDenseMenuSurface({
  isOpen: isAiMenuOpen,
  containerRef: aiMenuContainerRef,
  menuRef: aiMenuRef,
  triggerRef: aiMenuTriggerRef,
});

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
    blockers.push("Kodredigeraren är låst för redigering.");
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

function handleCreateCheckpoint(): void {
  emit("createCheckpoint", checkpointLabel.value.trim());
  checkpointLabel.value = "";
  closeSaveMenu();
}

const aiStatusTone = computed<DenseStatusTone>(() => {
  if (props.aiError) {
    return "error";
  }
  if (props.aiStatus === "applied") {
    return "success";
  }
  return "neutral";
});

const aiPillClass = computed(() =>
  denseStatusPillClass({
    tone: aiStatusTone.value,
    interactive: true,
    active: isAiMenuOpen.value,
  }),
);

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
        ref="saveMenuContainerRef"
        class="relative"
      >
        <UiDenseMenuButton
          ref="saveMenuTriggerRef"
          label="Spara/Öppna"
          :expanded="isSaveMenuOpen"
          @click="toggleSaveMenu()"
          @keydown="onSaveTriggerKeydown"
        />
        <div
          v-if="isSaveMenuOpen"
          ref="saveMenuRef"
          class="absolute left-0 top-full mt-2 w-[min(320px,90vw)] bg-canvas"
          :class="DENSE_MENU_PANEL_CLASS"
          role="menu"
          @keydown="onSaveMenuKeydown"
        >
          <div class="p-3 space-y-3">
            <div class="space-y-2">
              <div :class="DENSE_MENU_SECTION_LABEL_CLASS">
                Spara arbetsversion
              </div>
              <div class="space-y-1">
                <label :class="DENSE_MENU_SECTION_LABEL_CLASS">
                  Ändringssammanfattning (valfritt)
                </label>
                <input
                  :value="props.changeSummary"
                  :class="DENSE_FORM_INPUT_CLASS"
                  placeholder="T.ex. fixade bugg..."
                  :disabled="props.isReadOnly"
                  @input="emit('update:changeSummary', ($event.target as HTMLInputElement).value)"
                >
              </div>
              <button
                type="button"
                role="menuitem"
                :class="denseMenuItemClass()"
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
                <div :class="DENSE_MENU_SECTION_LABEL_CLASS">
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
              <div :class="DENSE_MENU_SECTION_LABEL_CLASS">
                Återställningspunkt
              </div>
              <div class="space-y-1">
                <label :class="DENSE_MENU_SECTION_LABEL_CLASS">
                  Namn (valfritt)
                </label>
                <input
                  v-model="checkpointLabel"
                  :class="DENSE_FORM_INPUT_CLASS"
                  placeholder="T.ex. före refactor"
                  :disabled="props.isReadOnly"
                >
              </div>
              <button
                type="button"
                role="menuitem"
                :class="denseMenuItemClass()"
                :disabled="props.isReadOnly || props.isCheckpointBusy"
                @click="handleCreateCheckpoint"
              >
                Spara ny återställningspunkt
              </button>
            </div>

            <div class="border-t border-navy/20 pt-3 space-y-2">
              <div :class="DENSE_MENU_SECTION_LABEL_CLASS">
                Öppna
              </div>
              <button
                type="button"
                role="menuitem"
                :class="denseMenuItemClass()"
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

      <EditorToolMenu
        :active-tool-id="props.toolId"
        :active-tool-title="props.toolTitle"
        :active-tool-slug="props.toolSlug"
        :can-create-tool="props.canCreateTool"
      />

      <UiDenseIconButton
        :label="props.isChatCollapsed ? 'Öppna kodassistenten' : 'Stäng kodassistenten'"
        class="lg:hidden"
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
      </UiDenseIconButton>

      <div
        v-if="props.aiStatus"
        ref="aiMenuContainerRef"
        class="relative flex items-center gap-1 shrink-0"
      >
        <button
          ref="aiMenuTriggerRef"
          type="button"
          :class="aiPillClass"
          :aria-expanded="isAiMenuOpen"
          aria-haspopup="menu"
          aria-label="AI-ändring"
          @click="toggleAiMenu()"
        >
          AI
        </button>

        <UiDenseIconButton
          label="Ångra AI-ändring"
          :disabled="!props.aiCanUndo"
          :title="props.aiUndoDisabledReason || undefined"
          @click="emit('undoAi')"
        >
          <IconUndo :size="16" />
        </UiDenseIconButton>

        <UiDenseIconButton
          label="Återställ AI-ändring"
          :disabled="!props.aiCanRedo"
          :title="props.aiRedoDisabledReason || undefined"
          @click="emit('redoAi')"
        >
          <IconRedo :size="16" />
        </UiDenseIconButton>

        <div
          v-if="isAiMenuOpen"
          ref="aiMenuRef"
          class="absolute left-0 top-full mt-2 w-[min(320px,90vw)] bg-canvas"
          :class="DENSE_MENU_PANEL_CLASS"
          role="menu"
          @keydown="onAiMenuKeydown"
        >
          <div class="p-3 space-y-2">
            <div class="space-y-1">
              <div :class="DENSE_MENU_SECTION_LABEL_CLASS">
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

      <UiDenseStatusPill
        v-if="props.hasDirtyChanges"
        label="Osparat"
        tone="warning"
      />

      <UiDenseStatusPill
        v-if="props.lockBadgeLabel"
        :label="props.lockBadgeLabel"
        :tone="props.lockBadgeTone === 'success' ? 'success' : 'neutral'"
      />
    </div>
  </div>
</template>
