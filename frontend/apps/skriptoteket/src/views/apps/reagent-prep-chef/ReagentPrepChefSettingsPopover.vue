<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

import { IconSettings, IconX } from "../../../components/icons";

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
const settingsTriggerRef = ref<HTMLButtonElement | null>(null);
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
    <button
      ref="settingsTriggerRef"
      type="button"
      class="btn-ghost h-[32px] px-3 py-1.5 text-[11px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none border-navy/30 bg-white shadow-none flex items-center gap-2"
      aria-label="Inställningar"
      title="Inställningar"
      :aria-expanded="showSettings"
      aria-controls="rpc-settings-popover"
      @click.stop="toggleSettings"
    >
      <IconSettings :size="16" />
      <span>Inställningar</span>
    </button>

    <Transition name="popover">
      <div
        v-if="showSettings"
        id="rpc-settings-popover"
        ref="settingsPopoverRef"
        class="absolute right-0 mt-2 z-50 w-[min(22rem,calc(100vw-2rem))] border border-navy bg-panel shadow-brutal-sm p-4 pr-10 text-sm text-navy/80"
        role="dialog"
        aria-modal="false"
        aria-label="Inställningar"
      >
        <button
          type="button"
          class="absolute top-2 right-2 h-7 w-7 grid place-items-center border border-transparent rounded-[var(--huleedu-radius-sm)] text-navy/60 hover:text-action hover:border-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-action/40 focus-visible:outline-offset-2"
          aria-label="Stäng inställningar"
          @click="closeSettings"
        >
          <IconX :size="14" />
        </button>

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
  transition:
    opacity 150ms var(--huleedu-ease-default),
    transform 150ms var(--huleedu-ease-default);
}

.popover-enter-from,
.popover-leave-to {
  opacity: 0;
  transform: translateY(-0.25rem);
}
</style>
