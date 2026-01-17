<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { apiPost, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useToast } from "../../composables/useToast";
import CreateDraftToolModal from "../admin/CreateDraftToolModal.vue";
import { IconArrow } from "../icons";

type CreateDraftToolResponse = components["schemas"]["CreateDraftToolResponse"];

const router = useRouter();
const toast = useToast();

const isCreateModalOpen = ref(false);
const createTitle = ref("");
const createSummary = ref("");
const createError = ref<string | null>(null);
const isCreating = ref(false);

function normalizedOptionalString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function openCreateModal(): void {
  createTitle.value = "";
  createSummary.value = "";
  createError.value = null;
  isCreateModalOpen.value = true;
}

function closeCreateModal(): void {
  isCreateModalOpen.value = false;
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
</script>

<template>
  <div>
    <button
      type="button"
      class="dashboard-card group text-left w-full"
      @click="openCreateModal"
    >
      <div class="card-header">
        <span class="card-label">Skapa nytt verktyg</span>
        <IconArrow
          :size="18"
          class="card-arrow"
        />
      </div>
      <p class="card-description mt-4">
        Skapa ett nytt verktyg i systemet.
      </p>
    </button>

    <CreateDraftToolModal
      :is-open="isCreateModalOpen"
      :title="createTitle"
      :summary="createSummary"
      :error="createError"
      :is-submitting="isCreating"
      @update:title="createTitle = $event"
      @update:summary="createSummary = $event"
      @update:error="createError = $event"
      @close="closeCreateModal"
      @submit="createDraftTool"
    />
  </div>
</template>
