<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { apiGet, isApiError } from "../api/client";
import type { components } from "../api/openapi";
import ToolListRow from "../components/tools/ToolListRow.vue";
import CreateDraftToolModal from "../components/admin/CreateDraftToolModal.vue";
import { useCreateDraftToolModal } from "../composables/admin/useCreateDraftToolModal";
import { useAuthStore } from "../stores/auth";

type ListMyToolsResponse = components["schemas"]["ListMyToolsResponse"];
type MyToolItem = components["schemas"]["MyToolItem"];

const tools = ref<MyToolItem[]>([]);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);

const auth = useAuthStore();
const canCreateTool = computed(() => auth.hasAtLeastRole("admin"));

const createDraftToolModal = useCreateDraftToolModal();
const isCreateModalOpen = createDraftToolModal.isOpen;
const createTitle = createDraftToolModal.title;
const createSummary = createDraftToolModal.summary;
const createError = createDraftToolModal.error;
const isCreating = createDraftToolModal.isSubmitting;

const hasTools = computed(() => tools.value.length > 0);

function openCreateModal(): void {
  createDraftToolModal.open();
}

function closeCreateModal(): void {
  createDraftToolModal.close();
}

async function createDraftTool(): Promise<void> {
  await createDraftToolModal.submit();
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
  <div class="space-y-6">
    <div class="space-y-2 max-w-[40rem]">
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
      class="w-full p-8 border border-navy bg-white shadow-brutal flex flex-col items-center text-center space-y-4"
    >
      <div class="space-y-2 max-w-[40rem]">
        <p class="text-navy font-semibold">Du har inga verktyg att underhålla ännu.</p>
        <p class="text-sm text-navy/60 max-w-sm">
          Här samlas verktyg som du skapat eller blivit tilldelad ansvar för.
          <template v-if="canCreateTool">Vill du börja bygga något nytt?</template>
          <template v-else>Har du en idé? Föreslå ett verktyg.</template>
        </p>
      </div>
      <button
        v-if="canCreateTool"
        type="button"
        class="btn-primary px-6"
        @click="openCreateModal"
      >
        Skapa ditt första verktyg
      </button>
      <RouterLink
        v-else
        to="/suggestions/new"
        class="btn-primary px-6 no-underline"
      >
        Föreslå verktyg
      </RouterLink>
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
