<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import CreateDraftToolModal from "../../components/admin/CreateDraftToolModal.vue";
import SystemMessage from "../../components/ui/SystemMessage.vue";
import { useCreateDraftToolModal } from "../../composables/admin/useCreateDraftToolModal";
import { useAdminToolsIndex } from "../../composables/admin/useAdminToolsIndex";
import {
  getLastRecentEditorToolId,
  listRecentEditorTools,
  removeRecentEditorTool,
} from "../../composables/editor/editorRecentTools";
import { searchTools } from "../../composables/tools/toolSearch";
import { useAuthStore } from "../../stores/auth";

type ListMyToolsResponse = components["schemas"]["ListMyToolsResponse"];
type MyToolItem = components["schemas"]["MyToolItem"];
type EditorBootResponse = components["schemas"]["EditorBootResponse"];

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const {
  tools: adminTools,
  isLoading: isAdminToolsLoading,
  error: adminToolsError,
  ensureLoaded: ensureAdminToolsLoaded,
} = useAdminToolsIndex();

const isForcedPick = computed(() => route.query.pick === "1");
const canCreateTool = computed(() => auth.hasAtLeastRole("admin"));

const searchQuery = ref("");
const recentTools = ref(listRecentEditorTools(auth.user?.id ?? ""));
const myTools = ref<MyToolItem[]>([]);
const isLoadingMyTools = ref(false);
const myToolsError = ref<string | null>(null);

const redirectError = ref<string | null>(null);
const isRedirecting = ref(false);

const createDraftToolModal = useCreateDraftToolModal();
const isCreateModalOpen = createDraftToolModal.isOpen;
const createTitle = createDraftToolModal.title;
const createSummary = createDraftToolModal.summary;
const createError = createDraftToolModal.error;
const isCreating = createDraftToolModal.isSubmitting;

const searchRef = ref<HTMLElement | null>(null);
const isSearchOpen = ref(false);

function refreshRecents(): void {
  recentTools.value = listRecentEditorTools(auth.user?.id ?? "");
}

type SearchCandidate = {
  id: string;
  title: string;
  slug: string;
};

function openCreateModal(): void {
  createDraftToolModal.open();
}

function closeCreateModal(): void {
  createDraftToolModal.close();
}

async function createDraftTool(): Promise<void> {
  await createDraftToolModal.submit();
}

const normalizedSearch = computed(() => searchQuery.value.trim().toLowerCase());

const recencyByToolId = computed(() => {
  const entries = recentTools.value.map((tool) => [tool.toolId, tool.openedAt] as const);
  return new Map(entries);
});

const sortedMyTools = computed(() => {
  const tools = [...myTools.value];
  const recency = recencyByToolId.value;
  tools.sort((a, b) => {
    const aRecency = recency.get(a.id) ?? null;
    const bRecency = recency.get(b.id) ?? null;
    if (aRecency !== null && bRecency !== null) return bRecency - aRecency;
    if (aRecency !== null) return -1;
    if (bRecency !== null) return 1;
    return a.title.localeCompare(b.title, "sv-SE");
  });
  return tools;
});

const searchCandidates = computed<SearchCandidate[]>(() => {
  if (canCreateTool.value) {
    const allTools = adminTools.value ?? [];
    return allTools.map((tool) => ({
      id: tool.id,
      title: tool.title,
      slug: tool.slug,
    }));
  }

  return myTools.value.map((tool) => ({
    id: tool.id,
    title: tool.title,
    slug: tool.slug,
  }));
});

const toolSearch = computed(() => {
  return searchTools({
    candidates: searchCandidates.value,
    query: searchQuery.value,
    limit: 5,
    locale: "sv-SE",
    recencyById: recencyByToolId.value,
  });
});

const searchErrorMessage = computed(() => {
  if (canCreateTool.value) return adminToolsError.value;
  return myToolsError.value;
});

const isSearchLoading = computed(() => {
  if (!normalizedSearch.value) return false;
  if (canCreateTool.value) return isAdminToolsLoading.value;
  return isLoadingMyTools.value;
});

const shouldShowSearchOverflow = computed(() => {
  if (!toolSearch.value.normalizedQuery) return false;
  if (searchErrorMessage.value) return false;
  if (isSearchLoading.value) return false;
  return toolSearch.value.totalMatches > toolSearch.value.results.length;
});

async function loadMyTools(): Promise<void> {
  isLoadingMyTools.value = true;
  myToolsError.value = null;

  try {
    const response = await apiGet<ListMyToolsResponse>("/api/v1/my-tools");
    myTools.value = response.tools;
  } catch (error: unknown) {
    if (isApiError(error)) {
      myToolsError.value = error.message;
    } else if (error instanceof Error) {
      myToolsError.value = error.message;
    } else {
      myToolsError.value = "Det gick inte att ladda verktyg.";
    }
  } finally {
    isLoadingMyTools.value = false;
  }
}

async function openTool(toolId: string): Promise<void> {
  if (!toolId) return;
  isSearchOpen.value = false;
  searchQuery.value = "";
  await router.push(`/admin/tools/${toolId}`);
}

function closeSearch(): void {
  isSearchOpen.value = false;
  searchQuery.value = "";
}

function handleDocumentClick(event: MouseEvent): void {
  const target = event.target as Node | null;
  if (!target) return;
  if (isSearchOpen.value && searchRef.value && !searchRef.value.contains(target)) {
    closeSearch();
  }
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key !== "Escape") return;
  if (isSearchOpen.value) {
    event.preventDefault();
    closeSearch();
  }
}

async function tryRedirectToLastTool(): Promise<boolean> {
  const userId = auth.user?.id ?? "";
  if (!userId) return false;

  const lastToolId = getLastRecentEditorToolId(userId);
  if (!lastToolId) return false;

  isRedirecting.value = true;
  redirectError.value = null;

  try {
    await apiGet<EditorBootResponse>(`/api/v1/editor/tools/${encodeURIComponent(lastToolId)}`);
    await router.replace(`/admin/tools/${lastToolId}`);
    return true;
  } catch (error: unknown) {
    if (isApiError(error) && (error.status === 403 || error.status === 404)) {
      removeRecentEditorTool(userId, lastToolId);
      refreshRecents();
      redirectError.value = "Det senaste verktyget gick inte att öppna längre. Välj ett annat.";
      return false;
    }

    redirectError.value =
      error instanceof Error ? error.message : "Det gick inte att öppna det senaste verktyget.";
    return false;
  } finally {
    isRedirecting.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", handleDocumentClick);
  document.addEventListener("keydown", handleKeydown);

  void (async () => {
    await auth.bootstrap();
    refreshRecents();

    if (!isForcedPick.value) {
      const didRedirect = await tryRedirectToLastTool();
      if (didRedirect) return;
    }

    await loadMyTools();
  })();
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleDocumentClick);
  document.removeEventListener("keydown", handleKeydown);
});

watch(
  () => normalizedSearch.value,
  async (value) => {
    if (!value) {
      isSearchOpen.value = false;
      return;
    }
    if (!canCreateTool.value) return;
    await ensureAdminToolsLoaded();
  },
);
</script>

<template>
  <div class="space-y-[var(--huleedu-space-6)]">
    <div class="flex flex-wrap items-end justify-between gap-[var(--huleedu-space-4)]">
      <div class="space-y-[var(--huleedu-space-2)] max-w-[40rem]">
        <h1 class="page-title">Kodredigeraren</h1>
        <p class="page-description">
          Fortsätt där du slutade.
        </p>
        <p class="text-xs text-navy/60">
          <RouterLink
            to="/my-tools"
            class="text-navy underline underline-offset-4 hover:text-action"
          >
            Mina verktyg
          </RouterLink>
          <template v-if="canCreateTool">
            <span class="text-navy/30"> · </span>
            <RouterLink
              to="/admin/tools"
              class="text-navy underline underline-offset-4 hover:text-action"
            >
              Alla verktyg
            </RouterLink>
          </template>
        </p>

        <div
          ref="searchRef"
          class="relative space-y-[var(--huleedu-space-1)]"
        >
          <label class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
            Sök
          </label>
          <input
            v-model="searchQuery"
            data-testid="editor-hub-search-input"
            class="w-full h-[28px] border border-navy/30 bg-white px-2.5 text-[11px] text-navy shadow-none leading-none"
            placeholder="Sök på titel eller URL-namn…"
            @focus="isSearchOpen = true"
          >
          <div class="text-[10px] text-navy/50">
            Söker i alla verktyg du har rätt att redigera.
          </div>

          <div
            v-if="isSearchOpen && toolSearch.normalizedQuery"
            class="absolute left-0 top-full mt-[var(--huleedu-space-2)] w-[min(520px,92vw)] border border-navy bg-panel shadow-brutal-sm z-[var(--huleedu-z-tooltip)]"
          >
            <div class="p-[var(--huleedu-space-3)] space-y-[var(--huleedu-space-2)]">
              <div class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
                Sökresultat
              </div>

              <div
                v-if="searchErrorMessage"
                class="border border-error/30 bg-error/10 px-2 py-1 text-[11px] text-error"
              >
                {{ searchErrorMessage }}
              </div>

              <div
                v-else-if="isSearchLoading"
                class="flex items-center gap-2 text-[11px] text-navy/60"
              >
                <span class="inline-block w-3 h-3 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
                <span>Laddar…</span>
              </div>

              <div
                v-else-if="toolSearch.results.length === 0"
                class="text-[11px] text-navy/60"
              >
                Inga verktyg matchar sökningen.
              </div>

              <div
                v-else
                class="border border-navy/20 divide-y divide-navy/15"
              >
                <button
                  v-for="tool in toolSearch.results"
                  :key="tool.id"
                  type="button"
                  class="w-full text-left px-[var(--huleedu-space-3)] py-[var(--huleedu-space-2)] hover:bg-canvas transition-colors"
                  @click="openTool(tool.id)"
                >
                  <div class="min-w-0">
                    <div class="text-[11px] font-semibold text-navy truncate">
                      {{ tool.title || "(Namnlöst verktyg)" }}
                    </div>
                    <div class="text-[10px] text-navy/60 font-mono truncate">
                      {{ tool.slug || tool.id }}
                    </div>
                  </div>
                </button>
              </div>

              <div
                v-if="shouldShowSearchOverflow"
                class="text-[10px] text-navy/60"
              >
                Visar {{ toolSearch.results.length }} av {{ toolSearch.totalMatches }}.
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-[var(--huleedu-space-3)]">
        <button
          v-if="canCreateTool"
          type="button"
          class="btn-primary"
          @click="openCreateModal"
        >
          Skapa nytt verktyg
        </button>
      </div>
    </div>

    <SystemMessage
      v-model="redirectError"
      variant="warning"
    />

    <div
      v-if="isRedirecting"
      class="flex items-center gap-[var(--huleedu-space-3)] p-[var(--huleedu-space-4)] border border-navy bg-panel shadow-brutal-sm text-sm text-navy/70"
    >
      <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
      <span>Öppnar senaste verktyg…</span>
    </div>

    <div
      v-else
      class="grid gap-[var(--huleedu-space-6)] lg:grid-cols-2"
    >
      <section
        class="border border-navy bg-panel shadow-brutal-sm p-[var(--huleedu-space-4)] space-y-[var(--huleedu-space-4)]"
      >
        <header class="space-y-[var(--huleedu-space-1)]">
          <h2 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Senast öppnade
          </h2>
          <p class="text-sm text-navy/60 max-w-[40rem]">
            Verktyg du nyligen öppnat i kodredigeraren.
          </p>
        </header>

        <div
          v-if="recentTools.length === 0"
          class="p-[var(--huleedu-space-4)] border border-navy/20 bg-canvas text-sm text-navy/70"
        >
          Inga senaste verktyg än.
        </div>

        <ul
          v-else
          data-testid="editor-hub-recent-tools-list"
          class="border border-navy/20 divide-y divide-navy/15"
        >
          <li
            v-for="tool in recentTools"
            :key="tool.toolId"
          >
            <button
              type="button"
              class="w-full text-left px-[var(--huleedu-space-3)] py-[var(--huleedu-space-2)] hover:bg-canvas transition-colors"
              @click="openTool(tool.toolId)"
            >
              <div class="text-sm font-semibold text-navy truncate">
                {{ tool.title || "(Namnlöst verktyg)" }}
              </div>
              <div class="text-[11px] text-navy/60">
                <span class="font-mono">{{ tool.slug || tool.toolId }}</span>
              </div>
            </button>
          </li>
        </ul>
      </section>

      <section
        class="border border-navy bg-panel shadow-brutal-sm p-[var(--huleedu-space-4)] space-y-[var(--huleedu-space-4)]"
      >
        <header class="space-y-[var(--huleedu-space-1)]">
          <h2 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Mina verktyg
          </h2>
          <p class="text-sm text-navy/60 max-w-[40rem]">
            Verktyg du ansvarar för att underhålla.
          </p>
          <template v-if="canCreateTool">
            <p class="text-xs text-navy/60">
              <RouterLink
                to="/admin/tools"
                class="text-navy underline underline-offset-4 hover:text-action"
              >
                Visa alla verktyg
              </RouterLink>
            </p>
          </template>
        </header>

        <SystemMessage
          v-model="myToolsError"
          variant="error"
        />

        <div
          v-if="isLoadingMyTools"
          data-testid="editor-hub-my-tools-loading"
          class="flex items-center gap-[var(--huleedu-space-3)] p-[var(--huleedu-space-4)] border border-navy/20 bg-canvas text-sm text-navy/70"
        >
          <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
          <span>Laddar…</span>
        </div>

        <div
          v-else-if="sortedMyTools.length === 0"
          data-testid="editor-hub-my-tools-empty"
          class="p-[var(--huleedu-space-4)] border border-navy/20 bg-canvas text-sm text-navy/70"
        >
          Inga verktyg hittades.
        </div>

        <ul
          v-else
          data-testid="editor-hub-my-tools-list"
          class="border border-navy/20 divide-y divide-navy/15"
        >
          <li
            v-for="tool in sortedMyTools"
            :key="tool.id"
          >
            <button
              type="button"
              class="w-full text-left px-[var(--huleedu-space-3)] py-[var(--huleedu-space-2)] hover:bg-canvas transition-colors"
              @click="openTool(tool.id)"
            >
              <div class="text-sm font-semibold text-navy truncate">
                {{ tool.title }}
              </div>
              <div class="text-[11px] text-navy/60">
                {{ tool.is_published ? "Publicerad" : "Ej publicerad" }}
              </div>
            </button>
          </li>
        </ul>
      </section>
    </div>
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
