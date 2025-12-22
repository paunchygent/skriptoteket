<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiFetch, apiGet, isApiError } from "../api/client";
import type { components } from "../api/openapi";

type ToolMetadataResponse = components["schemas"]["ToolMetadataResponse"];
type StartToolRunResponse = components["schemas"]["StartToolRunResponse"];

const route = useRoute();
const router = useRouter();

const slug = computed(() => {
  const param = route.params.slug;
  return typeof param === "string" ? param : "";
});

const tool = ref<ToolMetadataResponse | null>(null);
const selectedFiles = ref<File[]>([]);
const isLoading = ref(true);
const isSubmitting = ref(false);
const errorMessage = ref<string | null>(null);

async function fetchTool(): Promise<void> {
  if (!slug.value) {
    return;
  }

  isLoading.value = true;
  errorMessage.value = null;

  try {
    tool.value = await apiGet<ToolMetadataResponse>(`/api/v1/tools/${encodeURIComponent(slug.value)}`);
  } catch (error: unknown) {
    tool.value = null;
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Failed to load tool";
    }
  } finally {
    isLoading.value = false;
  }
}

function onFilesSelected(event: Event): void {
  const input = event.target as HTMLInputElement | null;
  selectedFiles.value = input?.files ? Array.from(input.files) : [];
}

async function submit(): Promise<void> {
  if (!slug.value) {
    errorMessage.value = "Missing tool slug";
    return;
  }
  if (isSubmitting.value) {
    return;
  }
  if (selectedFiles.value.length === 0) {
    errorMessage.value = "Välj minst en fil.";
    return;
  }

  isSubmitting.value = true;
  errorMessage.value = null;

  try {
    const formData = new FormData();
    for (const file of selectedFiles.value) {
      formData.append("files", file);
    }

    const response = await apiFetch<StartToolRunResponse>(`/api/v1/tools/${encodeURIComponent(slug.value)}/run`, {
      method: "POST",
      body: formData,
    });

    await router.push({
      name: "tool-result",
      params: { slug: slug.value, runId: response.run_id },
    });
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Körning misslyckades.";
    }
  } finally {
    isSubmitting.value = false;
  }
}

onMounted(() => {
  void fetchTool();
});

watch(slug, () => {
  void fetchTool();
});

const uploadHint = computed(() => {
  const constraints = tool.value?.upload_constraints;
  if (!constraints) return null;

  return `Max ${constraints.max_files} filer, ${constraints.max_file_bytes} byte per fil, ${constraints.max_total_bytes} byte totalt.`;
});
</script>

<template>
  <div class="max-w-2xl">
    <RouterLink
      to="/browse"
      class="text-sm text-navy/70 underline hover:text-burgundy"
    >
      ← Tillbaka till katalog
    </RouterLink>

    <div class="mt-4 space-y-2">
      <h1 class="text-2xl font-semibold text-navy">
        {{ tool?.title ?? (isLoading ? "Laddar..." : "Okänt verktyg") }}
      </h1>
      <p
        v-if="tool?.summary"
        class="text-navy/60"
      >
        {{ tool.summary }}
      </p>
    </div>

    <div
      v-if="errorMessage"
      class="mt-4 p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
    >
      {{ errorMessage }}
    </div>

    <form
      class="mt-6 space-y-4"
      @submit.prevent="submit"
    >
      <div class="space-y-2">
        <label class="block text-sm font-semibold text-navy">Ladda upp filer</label>

        <input
          type="file"
          multiple
          required
          class="block w-full text-sm text-navy file:mr-3 file:px-4 file:py-2 file:border file:border-navy file:bg-white file:text-navy file:shadow-brutal-sm file:font-semibold"
          @change="onFilesSelected"
        >

        <p
          v-if="uploadHint"
          class="text-xs text-navy/60"
        >
          {{ uploadHint }}
        </p>

        <ul
          v-if="selectedFiles.length > 0"
          class="list-disc pl-5 text-sm text-navy/80"
        >
          <li
            v-for="file in selectedFiles"
            :key="`${file.name}-${file.size}`"
          >
            {{ file.name }}
            <span class="text-navy/60">({{ file.size }} byte)</span>
          </li>
        </ul>
      </div>

      <button
        type="submit"
        class="px-4 py-2 border border-navy bg-burgundy text-canvas shadow-brutal font-semibold uppercase tracking-wide disabled:opacity-50"
        :disabled="isSubmitting"
      >
        {{ isSubmitting ? "Kör..." : "Kör" }}
      </button>
    </form>
  </div>
</template>

