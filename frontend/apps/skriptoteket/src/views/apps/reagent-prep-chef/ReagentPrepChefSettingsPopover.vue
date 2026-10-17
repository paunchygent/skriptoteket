<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

import { UiGlyph } from "../../../components/ui/shared";
import { UiDenseActionButton, UiDenseIconButton } from "../../../components/ui";

import type { ReagentPrepChefDefaultsResult } from "./types";

type Props = {
  canCalculate: boolean;
  isDefaultsSaving: boolean;
  isDefaultsLoading: boolean;
  defaults: ReagentPrepChefDefaultsResult | null;
  isSavingDefaultsToVault: boolean;
  isLoadingDefaultsFromVault: boolean;
  lastSavedDefaultsVaultRef: string | null;
};

const props = defineProps<Props>();

const emit = defineEmits<{
  (event: "saveDefaults"): void;
  (event: "loadDefaults"): void;
  (event: "clearDefaults"): void;
  (event: "saveDefaultsToVault"): void;
  (event: "openDefaultsVaultPicker"): void;
}>();

const showSettings = ref(false);
const settingsTriggerRef = ref<HTMLSpanElement | null>(null);
const settingsPopoverRef = ref<HTMLDivElement | null>(null);

function closeSettings(): void {
  showSettings.value = false;
}

function toggleSettings(): void {
  showSettings.value = !showSettings.value;
}

function handleSettingsClickOutside(event: MouseEvent): void {
  if (!showSettings.value) return;
  const target = event.target;
  if (!target || !(target instanceof Node)) return;
  if (settingsTriggerRef.value?.contains(target) || settingsPopoverRef.value?.contains(target)) {
    return;
  }
  closeSettings();
}

function handleSettingsEscape(event: KeyboardEvent): void {
  if (event.key === "Escape" && showSettings.value) {
    closeSettings();
  }
}

onMounted(() => {
  document.addEventListener("click", handleSettingsClickOutside);
  document.addEventListener("keydown", handleSettingsEscape);
});

onUnmounted(() => {
  document.removeEventListener("click", handleSettingsClickOutside);
  document.removeEventListener("keydown", handleSettingsEscape);
});
</script>

<template>
  <div class="relative ml-auto">
    <span ref="settingsTriggerRef">
      <UiDenseActionButton
        label="Inställningar"
        title="Inställningar"
        :expanded="showSettings"
        has-popup="dialog"
        aria-controls="rpc-settings-popover"
        @click.stop="toggleSettings"
      >
        <template #leading>
          <UiGlyph
            meaning="settings"
            :size="16"
            :stroke-width="2.5"
          />
        </template>
      </UiDenseActionButton>
    </span>

    <Transition name="popover">
      <div
        v-if="showSettings"
        id="rpc-settings-popover"
        ref="settingsPopoverRef"
        class="absolute right-0 mt-2 z-50 w-[min(22rem,calc(100vw-2rem))] rounded-[var(--huleedu-panel-radius)] border border-navy/20 bg-modal shadow-md p-4 pr-10 text-sm text-navy/80"
        role="dialog"
        aria-modal="false"
        aria-label="Inställningar"
      >
        <UiDenseIconButton
          class="absolute top-2 right-2"
          label="Stäng inställningar"
          @click="closeSettings"
        >
          <UiGlyph
            meaning="close"
            :size="14"
            :stroke-width="2.5"
          />
        </UiDenseIconButton>

        <p class="font-semibold text-navy mb-2">Inställningar</p>

        <div class="space-y-2">
          <p class="text-xs text-navy/60">
            Standardinställningar sparas per användare. Du kan alltid ändra dem senare.
          </p>
          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="btn-primary"
              :disabled="props.isDefaultsSaving || !props.canCalculate"
              @click="emit('saveDefaults')"
            >
              {{ props.isDefaultsSaving ? "Sparar…" : "Spara som standard" }}
            </button>
            <button
              type="button"
              class="btn-ghost"
              :disabled="props.isDefaultsLoading || !props.defaults?.defaults"
              @click="emit('loadDefaults')"
            >
              Ladda standard
            </button>
            <button
              type="button"
              class="btn-ghost"
              :disabled="props.isDefaultsSaving || !props.defaults?.defaults"
              @click="emit('clearDefaults')"
            >
              Rensa
            </button>
          </div>
        </div>

        <div class="border-t border-navy/20 pt-3 mt-3 space-y-2">
          <p class="text-xs text-navy/60">
            Du kan också spara och ladda standardinställningar som en fil i Mina filer.
          </p>
          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="btn-ghost"
              :disabled="props.isSavingDefaultsToVault || !props.canCalculate"
              @click="emit('saveDefaultsToVault')"
            >
              {{ props.isSavingDefaultsToVault ? "Sparar…" : "Spara i Mina filer" }}
            </button>
            <button
              type="button"
              class="btn-ghost"
              :disabled="props.isLoadingDefaultsFromVault"
              @click="emit('openDefaultsVaultPicker')"
            >
              {{ props.isLoadingDefaultsFromVault ? "Laddar…" : "Ladda från Mina filer" }}
            </button>
          </div>
          <p
            v-if="props.lastSavedDefaultsVaultRef"
            class="text-[11px] text-navy/60"
          >
            Senast sparad: <span class="font-mono">{{ props.lastSavedDefaultsVaultRef }}</span>
          </p>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.popover-enter-active,
.popover-leave-active {
  transition: opacity var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.popover-enter-from,
.popover-leave-to {
  opacity: 0;
}
</style>
