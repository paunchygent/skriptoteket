<template>
  <teleport to="#spa-editor-main-target">
    <label class="huleedu-label">Källkod</label>
    <div class="huleedu-editor-textarea-wrapper">
      <CodeMirrorEditor v-model="sourceCode" />
    </div>
  </teleport>

  <teleport to="#spa-editor-sidebar-target">
    <div class="huleedu-stack-sm">
      <div>
        <label class="huleedu-label">Startfunktion</label>
        <input
          v-model="entrypoint"
          class="huleedu-input"
          placeholder="main"
        >
      </div>
      <div>
        <label class="huleedu-label">Ändringssammanfattning</label>
        <input
          v-model="changeSummary"
          class="huleedu-input"
          placeholder="T.ex. fixade bugg..."
        >
      </div>
      <button
        type="button"
        class="huleedu-btn huleedu-btn-navy huleedu-w-full"
        :disabled="isSaving"
        @click="save"
      >
        {{ buttonLabel }}
      </button>
      <p
        v-if="errorMessage"
        class="huleedu-error"
      >
        {{ errorMessage }}
      </p>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import CodeMirrorEditor from "./CodeMirrorEditor.vue";
import type { EditorBootPayload, SaveResult } from "./types";

const props = defineProps<{ payload: EditorBootPayload }>();

const entrypoint = ref(props.payload.entrypoint);
const sourceCode = ref(props.payload.source_code);
const changeSummary = ref("");

const isSaving = ref(false);
const errorMessage = ref<string | null>(null);

const buttonLabel = computed(() => {
  if (isSaving.value) return "Sparar…";
  return props.payload.save_mode === "snapshot" ? "Spara" : "Skapa utkast";
});

function _normalizedOptionalString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function _getCsrfToken(): string | null {
  const input = document.querySelector("input[name='csrf_token']") as HTMLInputElement | null;
  const value = input?.value?.trim() ?? "";
  return value ? value : null;
}

async function save(): Promise<void> {
  if (isSaving.value) return;
  errorMessage.value = null;
  isSaving.value = true;

  try {
    const csrfToken = _getCsrfToken();
    if (!csrfToken) {
      errorMessage.value = "Din session saknar CSRF-token. Ladda om sidan och försök igen.";
      return;
    }

    const entrypointValue = entrypoint.value.trim();
    if (!entrypointValue) {
      errorMessage.value = "Startfunktion krävs.";
      return;
    }

    const changeSummaryValue = _normalizedOptionalString(changeSummary.value);

    const selectedVersionId = props.payload.selected_version_id;
    if (props.payload.save_mode === "snapshot" && !selectedVersionId) {
      errorMessage.value = "Versionen stämmer inte längre. Ladda om och försök igen.";
      return;
    }

    const url =
      props.payload.save_mode === "snapshot"
        ? `/api/v1/editor/tool-versions/${selectedVersionId}/save`
        : `/api/v1/editor/tools/${props.payload.tool_id}/draft`;

    const body =
      props.payload.save_mode === "snapshot"
        ? {
            entrypoint: entrypointValue,
            source_code: sourceCode.value,
            change_summary: changeSummaryValue,
            expected_parent_version_id: selectedVersionId,
          }
        : {
            entrypoint: entrypointValue,
            source_code: sourceCode.value,
            change_summary: changeSummaryValue,
            derived_from_version_id: props.payload.derived_from_version_id,
          };

    const response = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      let message = "Ett oväntat fel inträffade.";
      try {
        const data = (await response.json()) as { error?: { message?: string } };
        message = data.error?.message ?? message;
      } catch {
        // Ignore parse errors; keep default message.
      }
      errorMessage.value = message;
      return;
    }

    const data = (await response.json()) as SaveResult;
    window.location.assign(data.redirect_url);
  } catch (err) {
    console.error(err);
    errorMessage.value = "Det gick inte att spara just nu. Försök igen.";
  } finally {
    isSaving.value = false;
  }
}
</script>
