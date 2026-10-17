<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { UiDenseActionButton } from "../ui";

import type { components } from "../../api/openapi";
import type { SettingsFormValues } from "../../composables/tools/toolSettingsHelpers";
import type { FileRefInfo } from "../../composables/tools/fileRefHelpers";
import ToolRunSettingsPanel from "../tool-run/ToolRunSettingsPanel.vue";

type CreateDraftVersionRequest = components["schemas"]["CreateDraftVersionRequest"];
type ToolSettingsSchema = NonNullable<CreateDraftVersionRequest["settings_schema"]>;

type SandboxSettingsCardProps = {
  versionId: string;
  isReadOnly: boolean;
  hasSettingsSchema: boolean;
  settingsSchema: ToolSettingsSchema | null;
  settingsSchemaError: string | null;
  settingsValues: SettingsFormValues;
  settingsErrorMessage: string | null;
  isLoadingSettings: boolean;
  isSavingSettings: boolean;
  availableFileRefs?: FileRefInfo[];
  saveSettings: () => Promise<void>;
};

const props = defineProps<SandboxSettingsCardProps>();

const emit = defineEmits<{
  (event: "update:settingsValues", value: SettingsFormValues): void;
  (event: "update:settingsErrorMessage", value: string | null): void;
}>();

const isOpen = ref(false);
const isSaveDisabled = computed(() => props.isReadOnly || Boolean(props.settingsSchemaError));

function toggleSettings(): void {
  isOpen.value = !isOpen.value;
}

watch(
  () => props.hasSettingsSchema,
  (next) => {
    if (!next) {
      isOpen.value = false;
    }
  },
);

watch(
  () => props.settingsSchemaError,
  (next) => {
    if (next) {
      isOpen.value = false;
    }
  },
);
</script>

<template>
  <div
    v-if="props.hasSettingsSchema || props.settingsSchemaError"
    class="panel-inset"
  >
    <div class="flex items-center justify-between gap-3 px-3 py-2 border-b border-navy/20">
      <span class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
        Inställningar
      </span>

      <UiDenseActionButton
        :label="isOpen ? 'Dölj' : 'Visa'"
        :disabled="!props.hasSettingsSchema"
        :expanded="isOpen"
        @click="toggleSettings"
      />
    </div>

    <p
      v-if="props.settingsSchemaError"
      class="px-3 py-2 text-xs font-semibold text-critical"
    >
      {{ props.settingsSchemaError }}
    </p>

    <div
      v-if="isOpen && props.hasSettingsSchema && props.settingsSchema"
      class="px-3 py-3 bg-canvas/30"
    >
      <ToolRunSettingsPanel
        :id-base="`sandbox-${props.versionId}`"
        :schema="props.settingsSchema"
        :model-value="props.settingsValues"
        :is-loading="props.isLoadingSettings"
        :is-saving="props.isSavingSettings"
        :available-file-refs="props.availableFileRefs"
        variant="embedded"
        density="compact"
        :is-save-disabled="isSaveDisabled"
        :error-message="props.settingsErrorMessage"
        @update:model-value="emit('update:settingsValues', $event)"
        @update:error-message="emit('update:settingsErrorMessage', $event)"
        @save="props.saveSettings"
      />
    </div>
  </div>
</template>
