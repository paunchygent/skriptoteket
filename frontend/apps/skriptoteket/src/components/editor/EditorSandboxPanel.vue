<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import type { components } from "../../api/openapi";

import EntrypointDropdown from "./EntrypointDropdown.vue";

const SandboxRunner = defineAsyncComponent(() => import("./SandboxRunner.vue"));

type EditorVersionSummary = components["schemas"]["EditorVersionSummary"];
type CreateDraftVersionRequest = components["schemas"]["CreateDraftVersionRequest"];
type ToolInputSchema = NonNullable<CreateDraftVersionRequest["input_schema"]>;
type ToolSettingsSchema = NonNullable<CreateDraftVersionRequest["settings_schema"]>;

type EditorSandboxPanelProps = {
  toolId: string;
  selectedVersion: EditorVersionSummary | null;
  entrypointOptions: string[];
  entrypoint: string;
  isReadOnly: boolean;
  sourceCode: string;
  usageInstructions: string;
  settingsSchema: ToolSettingsSchema | null;
  settingsSchemaError: string | null;
  inputSchema: ToolInputSchema;
  inputSchemaError: string | null;
  hasBlockingSchemaIssues: boolean;
  schemaValidationError: string | null;
  validateSchemasNow: () => Promise<boolean>;
  variant?: "inline" | "mode";
};

const props = withDefaults(defineProps<EditorSandboxPanelProps>(), {
  variant: "inline",
});

const emit = defineEmits<{
  (event: "update:entrypoint", value: string): void;
}>();
</script>

<template>
  <div
    :class="[
      'flex flex-col min-h-0',
      props.variant === 'mode'
        ? 'h-full space-y-3'
        : 'border-t border-navy/20 pt-4 space-y-3',
    ]"
  >
    <h2
      v-if="props.variant !== 'mode'"
      class="text-sm font-semibold uppercase tracking-wide text-navy/70"
    >
      Testkör kod
    </h2>

    <!-- Entrypoint + file picker + run button -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
      <EntrypointDropdown
        :model-value="props.entrypoint"
        :options="props.entrypointOptions"
        :disabled="props.isReadOnly"
        @update:model-value="emit('update:entrypoint', $event)"
      />
    </div>

    <div
      :class="props.variant === 'mode' ? 'flex-1 min-h-0 flex flex-col' : ''"
      data-editor-panel="test"
    >
      <Suspense v-if="props.selectedVersion">
        <template #default>
          <div :class="props.variant === 'mode' ? 'flex-1 min-h-0 overflow-y-auto' : ''">
            <SandboxRunner
              :version-id="props.selectedVersion.id"
              :tool-id="props.toolId"
              :is-read-only="props.isReadOnly"
              :entrypoint="props.entrypoint"
              :source-code="props.sourceCode"
              :settings-schema="props.settingsSchema"
              :settings-schema-error="props.settingsSchemaError"
              :input-schema="props.inputSchema"
              :input-schema-error="props.inputSchemaError"
              :has-blocking-schema-issues="props.hasBlockingSchemaIssues"
              :schema-validation-error="props.schemaValidationError"
              :validate-schemas-now="props.validateSchemasNow"
              :usage-instructions="props.usageInstructions"
            />
          </div>
        </template>
        <template #fallback>
          <div
            class="panel-inset p-4 text-sm text-navy/70"
            :class="[
              props.variant === 'mode'
                ? 'flex-1 min-h-0 flex items-center justify-center gap-3'
                : 'flex items-center gap-3',
            ]"
            data-editor-state="test-loading"
          >
            <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
            <span>Laddar testkörning...</span>
          </div>
        </template>
      </Suspense>
      <div
        v-else
        :class="[
          'text-sm text-navy/60',
          props.variant === 'mode'
            ? 'flex-1 min-h-0 panel-inset p-4 flex items-center justify-center'
            : '',
        ]"
        data-editor-empty="test"
      >
        Spara ett utkast för att kunna testa.
      </div>
    </div>
  </div>
</template>
