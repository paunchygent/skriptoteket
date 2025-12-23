<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { apiGet, apiPost, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import ToolListRow from "../../components/tools/ToolListRow.vue";
import ToggleSwitch from "../../components/ui/ToggleSwitch.vue";

type ListAdminToolsResponse = components["schemas"]["ListAdminToolsResponse"];
type AdminToolItem = components["schemas"]["AdminToolItem"];
type PublishToolResponse = components["schemas"]["PublishToolResponse"];
type DepublishToolResponse = components["schemas"]["DepublishToolResponse"];

const tools = ref<AdminToolItem[]>([]);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);
const actionInProgress = ref<string | null>(null);

// Split tools into two sections (ADR-0033)
const inProgressTools = computed(() =>
  tools.value.filter((t) => t.active_version_id === null),
);

const readyTools = computed(() =>
  tools.value.filter((t) => t.active_version_id !== null),
);

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
    return "bg-warning/20 text-warning border border-warning";
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
  errorMessage.value = null;
  successMessage.value = null;

  try {
    const response = await apiPost<PublishToolResponse>(
      `/api/v1/admin/tools/${tool.id}/publish`,
      {},
    );
    const index = tools.value.findIndex((t) => t.id === tool.id);
    if (index !== -1) {
      tools.value[index] = response.tool;
    }
    successMessage.value = `Verktyget "${tool.title}" har publicerats.`;
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att publicera verktyget.";
    }
  } finally {
    actionInProgress.value = null;
  }
}

async function depublishTool(tool: AdminToolItem): Promise<void> {
  if (actionInProgress.value) return;

  actionInProgress.value = tool.id;
  errorMessage.value = null;
  successMessage.value = null;

  try {
    const response = await apiPost<DepublishToolResponse>(
      `/api/v1/admin/tools/${tool.id}/depublish`,
      {},
    );
    const index = tools.value.findIndex((t) => t.id === tool.id);
    if (index !== -1) {
      tools.value[index] = response.tool;
    }
    successMessage.value = `Verktyget "${tool.title}" har avpublicerats.`;
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att avpublicera verktyget.";
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
  <div class="space-y-8">
    <div class="space-y-2">
      <h1 class="text-2xl font-semibold text-navy">Verktyg (admin)</h1>
      <p class="text-sm text-navy/70">Hantera publicering av verktyg.</p>
    </div>

    <div
      v-if="successMessage"
      class="p-4 border border-success bg-success/10 shadow-brutal-sm text-sm text-success"
    >
      {{ successMessage }}
    </div>

    <div
      v-if="errorMessage"
      class="p-4 border border-burgundy bg-white shadow-brutal-sm text-sm text-burgundy"
    >
      {{ errorMessage }}
    </div>

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
            grid-class="sm:grid-cols-[1fr_5rem_auto]"
          >
            <template #main>
              <div class="text-base font-semibold text-navy truncate">{{ tool.title }}</div>
              <div class="text-xs text-navy/60">
                <span class="font-mono">{{ tool.slug }}</span>
              </div>
              <div class="text-xs text-navy/70">
                {{ truncate(tool.summary, 80) }}
              </div>
            </template>

            <template #status>
              <span
                v-if="getDevStatus(tool)"
                class="inline-block px-2 py-1 text-xs font-medium"
                :class="getDevStatusClass(tool)"
              >
                {{ getDevStatus(tool) }}
              </span>
            </template>

            <template #actions>
              <RouterLink
                :to="`/admin/tools/${tool.id}`"
                class="px-4 py-2 text-xs font-bold uppercase tracking-widest bg-white text-navy border border-navy shadow-brutal-sm btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none"
              >
                Redigera
              </RouterLink>
            </template>
          </ToolListRow>
        </ul>
      </section>

      <!-- Section 2: Klara (publishable tools) -->
      <section
        v-if="readyTools.length > 0"
        class="space-y-3"
      >
        <div>
          <h2 class="text-lg font-semibold text-navy">Klara</h2>
          <p class="text-sm text-navy/60">Verktyg med godkänt skript</p>
        </div>
        <ul class="border border-navy bg-white shadow-brutal-sm divide-y divide-navy/15">
          <ToolListRow
            v-for="tool in readyTools"
            :key="tool.id"
            grid-class="sm:grid-cols-[1fr_9rem_auto]"
            status-class="justify-self-start"
          >
            <template #main>
              <div class="text-base font-semibold text-navy truncate">{{ tool.title }}</div>
              <div class="text-xs text-navy/60">
                <span class="font-mono">{{ tool.slug }}</span> · Uppdaterad
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
                class="px-4 py-2 text-xs font-bold uppercase tracking-widest bg-white text-navy border border-navy shadow-brutal-sm btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none"
              >
                Redigera
              </RouterLink>
            </template>
          </ToolListRow>
        </ul>
      </section>
    </template>
  </div>
</template>
