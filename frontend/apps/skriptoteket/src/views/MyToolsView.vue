<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { apiGet, apiPost, isApiError } from "../api/client";
import type { components } from "../api/openapi";
import ToolListRow from "../components/tools/ToolListRow.vue";
import CreateDraftToolModal from "../components/admin/CreateDraftToolModal.vue";
import { useToast } from "../composables/useToast";

type ListMyToolsResponse = components["schemas"]["ListMyToolsResponse"];
type MyToolItem = components["schemas"]["MyToolItem"];
type CreateDraftToolResponse = components["schemas"]["CreateDraftToolResponse"];

const tools = ref<MyToolItem[]>([]);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);

const isCreateModalOpen = ref(false);
const createTitle = ref("");
const createSummary = ref("");
const createError = ref<string | null>(null);
const isCreating = ref(false);

const router = useRouter();
const toast = useToast();

const hasTools = computed(() => tools.value.length > 0);

function openCreateModal(): void {
  createTitle.value = "";
  createSummary.value = "";
  createError.value = null;
  isCreateModalOpen.value = true;
}

function closeCreateModal(): void {
  isCreateModalOpen.value = false;
}

function normalizedOptionalString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

async function createDraftTool(): Promise<void> {
  if (isCreating.value) return;

  const title = createTitle.value.trim();
  if (!title) {
    createError.value = "Titel krävs.";
    return;
  }

  isCreating.value = true;
  createError.value = null;

  try {
    const response = await apiPost<CreateDraftToolResponse>("/api/v1/admin/tools", {
      title,
      summary: normalizedOptionalString(createSummary.value),
    });

    closeCreateModal();
    toast.success("Verktyg skapat.");
    await router.push(`/admin/tools/${response.tool.id}`);
  } catch (error: unknown) {
    if (isApiError(error)) {
      createError.value = error.message;
    } else if (error instanceof Error) {
      createError.value = error.message;
    } else {
      createError.value = "Det gick inte att skapa verktyget.";
    }
  } finally {
    isCreating.value = false;
  }
}

async function loadTools(): Promise<void> {
  isLoading.value = true;
  errorMessage.value = null;

  try {
    const response = await apiGet<ListMyToolsResponse>("/api/v1/my-tools");
    tools.value = response.tools;
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att ladda verktyg.";
    }
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  void loadTools();
});
</script>

<template>
  <div class="max-w-4xl space-y-6">
    <div class="space-y-2">
      <h1 class="page-title">Mina verktyg</h1>
      <p class="page-description">Verktyg som du ansvarar för att underhålla.</p>
    </div>

    <div
      v-if="isLoading"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      Laddar...
    </div>

    <div
      v-else-if="errorMessage"
      class="p-4 border border-error bg-white shadow-brutal-sm text-sm text-error"
    >
      {{ errorMessage }}
    </div>

    <div
      v-else-if="!hasTools"
      class="p-8 border border-navy bg-white shadow-brutal flex flex-col items-center text-center space-y-4"
    >
      <div class="space-y-2">
        <p class="text-navy font-semibold">Du har inga verktyg att underhålla ännu.</p>
        <p class="text-sm text-navy/60 max-w-sm">
          Här samlas verktyg som du skapat eller blivit tilldelad ansvar för.
          Vill du börja bygga något nytt?
        </p>
      </div>
      <button
        type="button"
        class="btn-primary px-6"
        @click="openCreateModal"
      >
        Skapa ditt första verktyg
      </button>
    </div>

    <ul
      v-else
      class="border border-navy bg-white shadow-brutal-sm divide-y divide-navy/15"
    >
      <ToolListRow
        v-for="tool in tools"
        :key="tool.id"
        grid-class="sm:grid-cols-[1fr_9rem_auto]"
        main-class="space-y-1 min-w-0 lg:max-w-[40rem]"
        status-class="justify-self-start"
      >
        <template #main>
          <div class="text-base font-semibold text-navy truncate">
            {{ tool.title }}
          </div>
          <div
            v-if="tool.summary"
            class="text-xs text-navy/70"
          >
            {{ tool.summary }}
          </div>
        </template>

        <template #status>
          <span
            class="text-xs whitespace-nowrap"
            :class="tool.is_published ? 'text-success font-medium' : 'text-navy/50'"
          >
            {{ tool.is_published ? "Publicerad" : "Ej publicerad" }}
          </span>
        </template>

        <template #actions>
          <RouterLink
            :to="`/admin/tools/${tool.id}`"
            class="btn-ghost no-underline"
          >
            Redigera
          </RouterLink>
        </template>
      </ToolListRow>
    </ul>
  </div>

  <CreateDraftToolModal
    :is-open="isCreateModalOpen"
    :title="createTitle"
    :summary="createSummary"
    :error="createError"
    :is-submitting="isCreating"
    @close="closeCreateModal"
    @submit="createDraftTool"
    @update:error="createError = $event"
    @update:title="createTitle = $event"
    @update:summary="createSummary = $event"
  />
</template>
