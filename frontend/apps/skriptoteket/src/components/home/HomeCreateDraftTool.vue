<script setup lang="ts">
import CreateDraftToolModal from "../admin/CreateDraftToolModal.vue";
import { useCreateDraftToolModal } from "../../composables/admin/useCreateDraftToolModal";
import { IconArrow } from "../icons";

const createDraftToolModal = useCreateDraftToolModal();
const isCreateModalOpen = createDraftToolModal.isOpen;
const createTitle = createDraftToolModal.title;
const createSummary = createDraftToolModal.summary;
const createError = createDraftToolModal.error;
const isCreating = createDraftToolModal.isSubmitting;

function openCreateModal(): void {
  createDraftToolModal.open();
}

function closeCreateModal(): void {
  createDraftToolModal.close();
}

async function createDraftTool(): Promise<void> {
  await createDraftToolModal.submit();
}
</script>

<template>
  <button
    type="button"
    class="dashboard-card group text-left"
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
  </button>
</template>
