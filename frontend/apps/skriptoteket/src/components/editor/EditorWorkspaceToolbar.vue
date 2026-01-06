<script setup lang="ts">
type EditorWorkspaceToolbarProps = {
  isSaving: boolean;
  isReadOnly: boolean;
  hasDirtyChanges: boolean;
  saveLabel: string;
  saveTitle: string;
  canOpenCompare: boolean;
  openCompareTitle: string;
  changeSummary: string;
  inputSchemaError: string | null;
  settingsSchemaError: string | null;
  hasBlockingSchemaIssues: boolean;
  canEditTaxonomy: boolean;
  canEditMaintainers: boolean;
};

const props = defineProps<EditorWorkspaceToolbarProps>();

const emit = defineEmits<{
  (event: "save"): void;
  (event: "openCompare"): void;
  (event: "openHistoryDrawer"): void;
  (event: "openMetadataDrawer"): void;
  (event: "openMaintainersDrawer"): void;
  (event: "openInstructionsDrawer"): void;
  (event: "update:changeSummary", value: string): void;
}>();
</script>

<template>
  <div class="p-4 border-b border-navy/20">
    <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
      <!-- Save group: Spara + Osparat + Ändringssammanfattning -->
      <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:gap-3">
        <div class="flex items-center gap-2">
          <button
            type="button"
            :disabled="
              props.isSaving ||
                props.isReadOnly ||
                Boolean(props.inputSchemaError) ||
                Boolean(props.settingsSchemaError) ||
                props.hasBlockingSchemaIssues
            "
            :title="props.saveTitle || undefined"
            class="btn-primary min-w-[80px]"
            @click="emit('save')"
          >
            <span
              v-if="props.isSaving"
              class="inline-block w-3 h-3 border-2 border-canvas/30 border-t-canvas rounded-full animate-spin"
            />
            <span v-else>{{ props.saveLabel }}</span>
          </button>
          <span
            v-if="props.hasDirtyChanges"
            class="text-xs text-burgundy font-semibold uppercase tracking-wide"
          >
            Osparat
          </span>
        </div>

        <div class="min-w-[180px] max-w-xs space-y-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Ändringssammanfattning
          </label>
          <input
            :value="props.changeSummary"
            class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
            placeholder="T.ex. fixade bugg..."
            :disabled="props.isReadOnly"
            @input="emit('update:changeSummary', ($event.target as HTMLInputElement).value)"
          >
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button
          v-if="props.canOpenCompare"
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          :title="props.openCompareTitle || undefined"
          @click="emit('openCompare')"
        >
          Öppna jämförelse
        </button>
        <button
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          @click="emit('openHistoryDrawer')"
        >
          Öppna sparade
        </button>
        <button
          v-if="props.canEditTaxonomy"
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          @click="emit('openMetadataDrawer')"
        >
          Metadata
        </button>
        <button
          v-if="props.canEditMaintainers"
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          @click="emit('openMaintainersDrawer')"
        >
          Redigeringsbehörigheter
        </button>
        <button
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          @click="emit('openInstructionsDrawer')"
        >
          Instruktioner
        </button>
      </div>
    </div>
  </div>
</template>
