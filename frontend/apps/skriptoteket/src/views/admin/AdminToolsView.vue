<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { apiGet, apiPost, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import CreateDraftToolModal from "../../components/admin/CreateDraftToolModal.vue";
import { useToast } from "../../composables/useToast";
import ToolListRow from "../../components/tools/ToolListRow.vue";
import SystemMessage from "../../components/ui/SystemMessage.vue";
import ToggleSwitch from "../../components/ui/ToggleSwitch.vue";

type ListAdminToolsResponse = components["schemas"]["ListAdminToolsResponse"];
type AdminToolItem = components["schemas"]["AdminToolItem"];
type PublishToolResponse = components["schemas"]["PublishToolResponse"];
type DepublishToolResponse = components["schemas"]["DepublishToolResponse"];
type CreateDraftToolResponse = components["schemas"]["CreateDraftToolResponse"];

const tools = ref<AdminToolItem[]>([]);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);
const actionInProgress = ref<string | null>(null);
const actionColumnWidth = ref("8.5rem");
const measureEditActionRef = ref<HTMLDivElement | null>(null);
const measureReviewActionRef = ref<HTMLDivElement | null>(null);
const isCreateModalOpen = ref(false);
const createTitle = ref("");
const createSummary = ref("");
const createError = ref<string | null>(null);
const isCreating = ref(false);
const router = useRouter();
const toast = useToast();

function updateActionColumnWidth(): void {
  const editWidth = measureEditActionRef.value?.getBoundingClientRect().width ?? 0;
  const reviewWidth = measureReviewActionRef.value?.getBoundingClientRect().width ?? 0;
  const next = Math.ceil(Math.max(editWidth, reviewWidth));
  if (next > 0) {
    actionColumnWidth.value = `${next}px`;
  }
}

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

const editActionClass = "btn-ghost text-center no-underline";

const reviewActionClass = "btn-cta text-center no-underline";

function actionLabel(tool: AdminToolItem): string {
  return tool.has_pending_review ? "Granska" : "Redigera";
}

function actionClass(tool: AdminToolItem): string {
  return tool.has_pending_review ? reviewActionClass : editActionClass;
}

// Status label for tools in development
function getDevStatus(tool: AdminToolItem): string {
  if (tool.version_count === 0) return "Ingen kod";
  if (tool.has_pending_review) return "Granskas";
  if (tool.latest_version_state === "draft") return "Utkast";
  return "";
}

// Status styling for tools in development
function getDevStatusClass(tool: AdminToolItem): string {
  if (tool.has_pending_review)
    return "bg-burgundy/10 text-burgundy border border-burgundy/40";
  if (tool.version_count === 0) return "bg-navy/10 text-navy/60";
  return "bg-canvas text-navy/70 border border-navy/30";
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("sv-SE", { dateStyle: "medium", timeStyle: "short" });
}

function truncate(text: string | null, maxLength: number): string {
  if (!text) return "-";
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}

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
      toast.failure("Det gick inte att publicera verktyget.");
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
      toast.failure("Det gick inte att avpublicera verktyget.");
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
  void nextTick().then(updateActionColumnWidth);
});
</script>

<template>
  <div
    class="space-y-8"
    :style="{ '--admin-tools-action-col': actionColumnWidth }"
  >
    <div
      class="fixed -left-[9999px] top-0 opacity-0 pointer-events-none"
      aria-hidden="true"
    >
      <div
        ref="measureEditActionRef"
        :class="editActionClass"
      >
        Redigera
      </div>
      <div
        ref="measureReviewActionRef"
        :class="reviewActionClass"
      >
        Granska
      </div>
    </div>

    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div class="space-y-2">
        <h1 class="page-title">Verktyg (admin)</h1>
        <p class="page-description">Hantera publicering av verktyg.</p>
      </div>
      <button
        type="button"
        class="btn-primary"
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
      class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      Laddar...
    </div>

    <template v-else>
      <!-- Empty state -->
      <div
        v-if="tools.length === 0"
        class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
      >
        Inga verktyg finns.
      </div>

      <!-- Section 1: Pågående (tools in development) -->
      <section
        v-if="inProgressTools.length > 0"
        class="space-y-3"
      >
        <div>
          <h2 class="text-lg font-semibold text-navy">Pågående</h2>
          <p class="text-sm text-navy/60">Verktyg under utveckling</p>
        </div>
        <ul class="border border-navy bg-white shadow-brutal-sm divide-y divide-navy/15">
          <ToolListRow
            v-for="tool in inProgressTools"
            :key="tool.id"
            grid-class="sm:grid-cols-[minmax(0,1fr)_12rem_var(--admin-tools-action-col)] lg:grid-cols-[minmax(0,40rem)_12rem_var(--admin-tools-action-col)]"
            status-class="justify-self-start"
            actions-class="justify-self-start sm:justify-self-stretch"
          >
            <template #main>
              <div class="text-base font-semibold text-navy truncate">{{ tool.title }}</div>
              <div class="text-xs text-navy/60">
                URL-namn: <span class="font-mono">{{ tool.slug }}</span>
              </div>
              <div class="text-xs text-navy/70">
                {{ truncate(tool.summary, 80) }}
              </div>
            </template>

            <template #status>
              <span
                v-if="getDevStatus(tool)"
                class="inline-block px-2 py-1 text-xs font-medium whitespace-nowrap"
                :class="getDevStatusClass(tool)"
              >
                {{ getDevStatus(tool) }}
              </span>
            </template>

            <template #actions>
              <RouterLink
                :to="`/admin/tools/${tool.id}`"
                :class="[actionClass(tool), 'w-full']"
              >
                {{ actionLabel(tool) }}
              </RouterLink>
            </template>
          </ToolListRow>
        </ul>
      </section>

      <!-- Section 2: Klara med ändringar (publishable tools with in-review updates) -->
      <section
        v-if="readyToolsWithPendingReview.length > 0"
        class="space-y-3"
      >
        <div>
          <h2 class="text-lg font-semibold text-navy">Klara med ändringar</h2>
          <p class="text-sm text-navy/60">Publicerade verktyg med ny version under granskning</p>
        </div>
        <ul class="border border-navy bg-white shadow-brutal-sm divide-y divide-navy/15">
          <ToolListRow
            v-for="tool in readyToolsWithPendingReview"
            :key="tool.id"
            grid-class="sm:grid-cols-[minmax(0,1fr)_12rem_var(--admin-tools-action-col)] lg:grid-cols-[minmax(0,40rem)_12rem_var(--admin-tools-action-col)]"
            status-class="justify-self-start"
            actions-class="justify-self-start sm:justify-self-stretch"
          >
            <template #main>
              <div class="flex flex-col gap-1 min-w-0 sm:flex-row sm:items-center sm:gap-2">
                <div class="text-base font-semibold text-navy truncate min-w-0">
                  {{ tool.title }}
                </div>
                <span
                  class="inline-block px-2 py-1 text-xs font-medium bg-burgundy/10 text-burgundy border border-burgundy/40 whitespace-nowrap self-start sm:self-auto shrink-0"
                >
                  Ny version granskas
                </span>
              </div>
              <div class="text-xs text-navy/60">
                URL-namn: <span class="font-mono">{{ tool.slug }}</span> · Uppdaterad
                {{ formatDateTime(tool.updated_at) }}
              </div>
              <div class="text-xs text-navy/70">
                {{ truncate(tool.summary, 80) }}
              </div>
            </template>

            <template #status>
              <div class="flex items-center gap-2">
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
            </template>

            <template #actions>
              <RouterLink
                :to="`/admin/tools/${tool.id}`"
                :class="[actionClass(tool), 'w-full']"
              >
                {{ actionLabel(tool) }}
              </RouterLink>
            </template>
          </ToolListRow>
        </ul>
      </section>

      <!-- Section 2: Klara (publishable tools) -->
      <section
        v-if="readyToolsWithoutPendingReview.length > 0"
        class="space-y-3"
      >
        <div>
          <h2 class="text-lg font-semibold text-navy">Klara</h2>
          <p class="text-sm text-navy/60">Verktyg med godkänt skript</p>
        </div>
        <ul class="border border-navy bg-white shadow-brutal-sm divide-y divide-navy/15">
          <ToolListRow
            v-for="tool in readyToolsWithoutPendingReview"
            :key="tool.id"
            grid-class="sm:grid-cols-[minmax(0,1fr)_12rem_var(--admin-tools-action-col)] lg:grid-cols-[minmax(0,40rem)_12rem_var(--admin-tools-action-col)]"
            status-class="justify-self-start"
            actions-class="justify-self-start sm:justify-self-stretch"
          >
            <template #main>
              <div class="text-base font-semibold text-navy truncate">{{ tool.title }}</div>
              <div class="text-xs text-navy/60">
                URL-namn: <span class="font-mono">{{ tool.slug }}</span> · Uppdaterad
                {{ formatDateTime(tool.updated_at) }}
              </div>
              <div class="text-xs text-navy/70">
                {{ truncate(tool.summary, 80) }}
              </div>
            </template>

            <template #status>
              <div class="flex items-center gap-2">
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
            </template>

            <template #actions>
              <RouterLink
                :to="`/admin/tools/${tool.id}`"
                :class="[actionClass(tool), 'w-full']"
              >
                {{ actionLabel(tool) }}
              </RouterLink>
            </template>
          </ToolListRow>
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
