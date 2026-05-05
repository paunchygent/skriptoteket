<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { apiGet, apiPost, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import CreateDraftToolModal from "../../components/admin/CreateDraftToolModal.vue";
import { useToast } from "../../composables/useToast";
import SystemMessage from "../../components/ui/SystemMessage.vue";
import ToggleSwitch from "../../components/ui/ToggleSwitch.vue";
import { useCreateDraftToolModal } from "../../composables/admin/useCreateDraftToolModal";

type ListAdminToolsResponse = components["schemas"]["ListAdminToolsResponse"];
type AdminToolItem = components["schemas"]["AdminToolItem"];
type PublishToolResponse = components["schemas"]["PublishToolResponse"];
type DepublishToolResponse = components["schemas"]["DepublishToolResponse"];

const tools = ref<AdminToolItem[]>([]);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);
const actionInProgress = ref<string | null>(null);
const toast = useToast();
const createDraftToolModal = useCreateDraftToolModal();
const isCreateModalOpen = createDraftToolModal.isOpen;
const createTitle = createDraftToolModal.title;
const createSummary = createDraftToolModal.summary;
const createError = createDraftToolModal.error;
const isCreating = createDraftToolModal.isSubmitting;

// Split tools into two sections (ADR-0033)
const inProgressTools = computed(() =>
  tools.value.filter((t) => t.active_version_id === null),
);

const readyTools = computed(() =>
  tools.value.filter((t) => t.active_version_id !== null),
);

const readyToolsWithPendingReview = computed(() =>
  readyTools.value.filter((t) => t.has_pending_review),
);

const readyToolsWithoutPendingReview = computed(() =>
  readyTools.value.filter((t) => !t.has_pending_review),
);

function truncate(text: string | null, maxLength: number): string {
  if (!text) return "-";
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}

function openCreateModal(): void {
  createDraftToolModal.open();
}

function closeCreateModal(): void {
  createDraftToolModal.close();
}

async function createDraftTool(): Promise<void> {
  await createDraftToolModal.submit();
}

async function load(): Promise<void> {
  isLoading.value = true;
  errorMessage.value = null;

  try {
    const response = await apiGet<ListAdminToolsResponse>("/api/v1/admin/tools");
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

async function publishTool(tool: AdminToolItem): Promise<void> {
  if (actionInProgress.value) return;

  actionInProgress.value = tool.id;

  try {
    const response = await apiPost<PublishToolResponse>(
      `/api/v1/admin/tools/${tool.id}/publish`,
      {},
    );
    const index = tools.value.findIndex((t) => t.id === tool.id);
    if (index !== -1) {
      tools.value[index] = response.tool;
    }
    toast.success(`Verktyget "${tool.title}" har publicerats.`);
  } catch (error: unknown) {
    if (isApiError(error)) {
      toast.failure(error.message);
    } else if (error instanceof Error) {
      toast.failure(error.message);
    } else {
      toast.failure("Det gick inte att publicera verktyget. Försök igen.");
    }
  } finally {
    actionInProgress.value = null;
  }
}

async function depublishTool(tool: AdminToolItem): Promise<void> {
  if (actionInProgress.value) return;

  actionInProgress.value = tool.id;

  try {
    const response = await apiPost<DepublishToolResponse>(
      `/api/v1/admin/tools/${tool.id}/depublish`,
      {},
    );
    const index = tools.value.findIndex((t) => t.id === tool.id);
    if (index !== -1) {
      tools.value[index] = response.tool;
    }
    toast.success(`Verktyget "${tool.title}" har avpublicerats.`);
  } catch (error: unknown) {
    if (isApiError(error)) {
      toast.failure(error.message);
    } else if (error instanceof Error) {
      toast.failure(error.message);
    } else {
      toast.failure("Det gick inte att avpublicera verktyget. Försök igen.");
    }
  } finally {
    actionInProgress.value = null;
  }
}

async function togglePublishState(tool: AdminToolItem, newValue: boolean): Promise<void> {
  // Confirm unpublish (turning OFF)
  if (!newValue) {
    const confirmed = window.confirm(
      `Vill du avpublicera "${tool.title}"? Verktyget blir inte längre tillgängligt för användare.`,
    );
    if (!confirmed) return;
  }

  if (newValue) {
    await publishTool(tool);
  } else {
    await depublishTool(tool);
  }
}

onMounted(() => {
  void load();
});
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between w-full">
      <div class="space-y-2 max-w-[40rem]">
        <h1 class="page-title">Hantera verktyg</h1>
        <p class="page-description">Hantera publicering av verktyg.</p>
      </div>
      <button
        type="button"
        class="btn-primary shrink-0"
        @click="openCreateModal"
      >
        Skapa nytt verktyg
      </button>
    </div>

    <SystemMessage
      v-model="errorMessage"
      variant="error"
    />

    <div
      v-if="isLoading"
      class="p-4 border border-navy bg-panel shadow-brutal-sm text-sm text-navy/70"
    >
      Laddar...
    </div>

    <template v-else>
      <!-- Section 1: Pågående (tools in development) - only show if has items -->
      <section
        v-if="inProgressTools.length > 0"
        class="space-y-3"
      >
        <h2 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          Pågående
        </h2>
        <ul class="border border-navy bg-panel shadow-brutal-sm">
          <li
            v-for="tool in inProgressTools"
            :key="tool.id"
            class="border-b border-navy/20 last:border-b-0"
          >
            <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 sm:gap-4 p-4 hover:bg-action/5 transition-colors">
              <div class="flex flex-col gap-1 min-w-0 max-w-[40rem]">
                <span class="text-sm font-medium text-navy">{{ tool.title }}</span>
                <span class="text-xs text-navy/60 break-words">{{ truncate(tool.summary, 80) }}</span>
              </div>
              <RouterLink
                :to="`/admin/tools/${tool.id}`"
                class="shrink-0 text-sm font-medium text-navy border-b border-navy/40 pb-0.5 hover:text-action hover:border-action transition-colors"
              >
                Redigera
              </RouterLink>
            </div>
          </li>
        </ul>
      </section>

      <!-- Section 2: Klara med ändringar (publishable tools with in-review updates) -->
      <section
        v-if="readyToolsWithPendingReview.length > 0"
        class="space-y-3"
      >
        <h2 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          Klara med ändringar
        </h2>
        <ul class="border border-navy bg-panel shadow-brutal-sm">
          <li
            v-for="tool in readyToolsWithPendingReview"
            :key="tool.id"
            class="border-b border-navy/20 last:border-b-0"
          >
            <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 sm:gap-4 p-4 hover:bg-action/5 transition-colors">
              <div class="flex flex-col gap-1 min-w-0 max-w-[40rem]">
                <span class="text-sm font-medium text-navy">{{ tool.title }}</span>
                <span class="text-xs text-navy/60 break-words">{{ truncate(tool.summary, 80) }}</span>
              </div>
              <div class="flex items-center gap-4 shrink-0">
                <div class="flex items-center gap-2 w-[8.5rem]">
                  <ToggleSwitch
                    :model-value="tool.is_published"
                    :disabled="actionInProgress === tool.id"
                    @update:model-value="togglePublishState(tool, $event)"
                  />
                  <span
                    class="text-xs whitespace-nowrap"
                    :class="tool.is_published ? 'text-success font-medium' : 'text-navy/50'"
                  >
                    {{ tool.is_published ? "Publicerad" : "Ej publicerad" }}
                  </span>
                </div>
                <RouterLink
                  :to="`/admin/tools/${tool.id}`"
                  class="text-sm font-semibold text-action border-b border-action/40 pb-0.5 hover:border-action transition-colors"
                >
                  Granska
                </RouterLink>
              </div>
            </div>
          </li>
        </ul>
      </section>

      <!-- Section 3: Klara (publishable tools) -->
      <section
        v-if="readyToolsWithoutPendingReview.length > 0"
        class="space-y-3"
      >
        <h2 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          Klara
        </h2>
        <ul class="border border-navy bg-panel shadow-brutal-sm">
          <li
            v-for="tool in readyToolsWithoutPendingReview"
            :key="tool.id"
            class="border-b border-navy/20 last:border-b-0"
          >
            <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 sm:gap-4 p-4 hover:bg-action/5 transition-colors">
              <div class="flex flex-col gap-1 min-w-0 max-w-[40rem]">
                <span class="text-sm font-medium text-navy">{{ tool.title }}</span>
                <span class="text-xs text-navy/60 break-words">{{ truncate(tool.summary, 80) }}</span>
              </div>
              <div class="flex items-center gap-4 shrink-0">
                <div class="flex items-center gap-2 w-[8.5rem]">
                  <ToggleSwitch
                    :model-value="tool.is_published"
                    :disabled="actionInProgress === tool.id"
                    @update:model-value="togglePublishState(tool, $event)"
                  />
                  <span
                    class="text-xs whitespace-nowrap"
                    :class="tool.is_published ? 'text-success font-medium' : 'text-navy/50'"
                  >
                    {{ tool.is_published ? "Publicerad" : "Ej publicerad" }}
                  </span>
                </div>
                <RouterLink
                  :to="`/admin/tools/${tool.id}`"
                  class="text-sm font-medium text-navy border-b border-navy/40 pb-0.5 hover:text-action hover:border-action transition-colors"
                >
                  Redigera
                </RouterLink>
              </div>
            </div>
          </li>
        </ul>
      </section>
    </template>
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

<style scoped>
</style>
