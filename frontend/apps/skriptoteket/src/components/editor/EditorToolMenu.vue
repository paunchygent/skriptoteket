<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useCreateDraftToolModal } from "../../composables/admin/useCreateDraftToolModal";
import { useAdminToolsIndex } from "../../composables/admin/useAdminToolsIndex";
import { listRecentEditorTools } from "../../composables/editor/editorRecentTools";
import { searchTools } from "../../composables/tools/toolSearch";
import { useAuthStore } from "../../stores/auth";
import CreateDraftToolModal from "../admin/CreateDraftToolModal.vue";

type ListMyToolsResponse = components["schemas"]["ListMyToolsResponse"];
type MyToolItem = components["schemas"]["MyToolItem"];

const props = defineProps<{
  activeToolId: string;
  activeToolTitle: string;
  activeToolSlug: string;
  canCreateTool: boolean;
}>();

const auth = useAuthStore();
const router = useRouter();
const {
  tools: adminTools,
  isLoading: isAdminToolsLoading,
  error: adminToolsError,
  ensureLoaded: ensureAdminToolsLoaded,
} = useAdminToolsIndex();

const utilityButtonClass =
  "btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none";

const menuButtonClass =
  "btn-ghost w-full justify-start px-[var(--huleedu-space-3)] py-[var(--huleedu-space-2)] text-[11px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/20 bg-white leading-snug";

const isOpen = ref(false);
const menuRef = ref<HTMLElement | null>(null);
const searchQuery = ref("");

const isLoadingMyTools = ref(false);
const myToolsError = ref<string | null>(null);
const myTools = ref<MyToolItem[]>([]);

const recentTools = ref(listRecentEditorTools(auth.user?.id ?? ""));

const createDraftToolModal = useCreateDraftToolModal();
const isCreateModalOpen = createDraftToolModal.isOpen;
const createTitle = createDraftToolModal.title;
const createSummary = createDraftToolModal.summary;
const createError = createDraftToolModal.error;
const isCreating = createDraftToolModal.isSubmitting;

function refreshRecents(): void {
  recentTools.value = listRecentEditorTools(auth.user?.id ?? "");
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

type SearchCandidate = {
  id: string;
  title: string;
  slug: string;
};

const searchCandidates = computed<SearchCandidate[]>(() => {
  if (props.canCreateTool) {
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
  if (props.canCreateTool) return adminToolsError.value;
  return myToolsError.value;
});

const isSearchLoading = computed(() => {
  if (!normalizedSearch.value) return false;
  if (props.canCreateTool) return isAdminToolsLoading.value;
  return isLoadingMyTools.value;
});

const shouldShowSearchOverflow = computed(() => {
  if (!toolSearch.value.normalizedQuery) return false;
  if (searchErrorMessage.value) return false;
  if (isSearchLoading.value) return false;
  return toolSearch.value.totalMatches > toolSearch.value.results.length;
});

async function loadMyTools(): Promise<void> {
  if (isLoadingMyTools.value) return;

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

function toggleMenu(): void {
  isOpen.value = !isOpen.value;
  if (isOpen.value) {
    refreshRecents();
    void loadMyTools();
  }
}

function closeMenu(): void {
  isOpen.value = false;
  searchQuery.value = "";
}

function handleDocumentClick(event: MouseEvent): void {
  const target = event.target as Node | null;
  if (!target) return;
  if (menuRef.value && !menuRef.value.contains(target)) {
    closeMenu();
  }
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key !== "Escape") {
    return;
  }
  if (isOpen.value) {
    event.preventDefault();
    event.stopPropagation();
    closeMenu();
  }
}

onMounted(() => {
  document.addEventListener("click", handleDocumentClick);
  document.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleDocumentClick);
  document.removeEventListener("keydown", handleKeydown);
});

watch(
  () => normalizedSearch.value,
  async (value) => {
    if (!value) return;
    if (!props.canCreateTool) return;
    await ensureAdminToolsLoaded();
  },
);

async function openTool(toolId: string): Promise<void> {
  if (!toolId) return;
  closeMenu();
  await router.push(`/admin/tools/${toolId}`);
}

function openCreateModal(): void {
  closeMenu();
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
  <div
    ref="menuRef"
    class="relative"
  >
    <button
      type="button"
      :class="utilityButtonClass"
      :aria-expanded="isOpen"
      aria-haspopup="menu"
      aria-label="Verktyg"
      @click="toggleMenu"
    >
      Verktyg
      <span class="ml-1">▾</span>
    </button>

    <div
      v-if="isOpen"
      class="absolute left-0 top-full mt-[var(--huleedu-space-2)] w-[min(420px,92vw)] border border-navy bg-canvas z-[var(--huleedu-z-tooltip)]"
      role="menu"
    >
      <div class="p-[var(--huleedu-space-3)] space-y-[var(--huleedu-space-3)]">
        <div class="space-y-[var(--huleedu-space-1)]">
          <div class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
            Aktivt verktyg
          </div>
          <div class="text-[11px] text-navy/70">
            <span class="font-semibold">{{ props.activeToolTitle || "(Namnlöst verktyg)" }}</span>
            <span class="text-navy/50"> · </span>
            <span class="font-mono text-navy/60">{{ props.activeToolSlug || props.activeToolId }}</span>
          </div>
        </div>

        <div class="space-y-[var(--huleedu-space-1)]">
          <label class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
            Sök
          </label>
          <input
            v-model="searchQuery"
            class="w-full h-[28px] border border-navy/30 bg-white px-2.5 text-[11px] text-navy shadow-none leading-none"
            placeholder="Sök på titel eller URL-namn…"
          >
          <div class="text-[10px] text-navy/50">
            Söker i alla verktyg du har rätt att redigera.
          </div>
        </div>

        <div
          v-if="toolSearch.normalizedQuery"
          class="border-t border-navy/20 pt-[var(--huleedu-space-3)] space-y-[var(--huleedu-space-2)]"
        >
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
            class="max-h-[min(220px,50vh)] overflow-y-auto border border-navy/20 bg-white divide-y divide-navy/15"
          >
            <button
              v-for="tool in toolSearch.results"
              :key="tool.id"
              type="button"
              :class="menuButtonClass"
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
            <template v-if="props.canCreateTool">
              <button
                type="button"
                class="font-semibold uppercase tracking-wide text-navy underline underline-offset-4 hover:text-burgundy"
                @click="
                  closeMenu();
                  void router.push('/admin/tools');
                "
              >
                Visa alla verktyg
              </button>
            </template>
          </div>
        </div>

        <template v-else>
          <div class="border-t border-navy/20 pt-[var(--huleedu-space-3)] space-y-[var(--huleedu-space-2)]">
            <div class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
              Senast öppnade
            </div>
            <div
              v-if="recentTools.length === 0"
              class="text-[11px] text-navy/60"
            >
              Inga senaste verktyg än.
            </div>
            <div
              v-else
              class="max-h-[min(220px,50vh)] overflow-y-auto border border-navy/20 bg-white divide-y divide-navy/15"
            >
              <button
                v-for="tool in recentTools"
                :key="tool.toolId"
                type="button"
                :class="menuButtonClass"
                @click="openTool(tool.toolId)"
              >
                <div class="text-[11px] font-semibold text-navy truncate">
                  {{ tool.title || "(Namnlöst verktyg)" }}
                </div>
                <div class="text-[10px] text-navy/60 font-mono truncate">
                  {{ tool.slug || tool.toolId }}
                </div>
              </button>
            </div>
          </div>

          <div class="border-t border-navy/20 pt-[var(--huleedu-space-3)] space-y-[var(--huleedu-space-2)]">
            <div class="flex items-center justify-between gap-[var(--huleedu-space-3)]">
              <div class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
                Mina verktyg
              </div>
              <button
                v-if="props.canCreateTool"
                type="button"
                class="text-[10px] font-semibold uppercase tracking-wide text-navy underline underline-offset-4 hover:text-burgundy"
                @click="
                  closeMenu();
                  void router.push('/admin/tools');
                "
              >
                Alla verktyg
              </button>
            </div>

            <div
              v-if="myToolsError"
              class="border border-error/30 bg-error/10 px-2 py-1 text-[11px] text-error"
            >
              {{ myToolsError }}
            </div>

            <div
              v-else-if="isLoadingMyTools"
              class="flex items-center gap-2 text-[11px] text-navy/60"
            >
              <span class="inline-block w-3 h-3 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
              <span>Laddar…</span>
            </div>

            <div
              v-else-if="sortedMyTools.length === 0"
              class="text-[11px] text-navy/60"
            >
              Inga verktyg hittades.
            </div>

            <div
              v-else
              class="max-h-[min(220px,50vh)] overflow-y-auto border border-navy/20 bg-white divide-y divide-navy/15"
            >
              <button
                v-for="tool in sortedMyTools"
                :key="tool.id"
                type="button"
                :class="menuButtonClass"
                @click="openTool(tool.id)"
              >
                <div class="text-[11px] font-semibold text-navy truncate">
                  {{ tool.title }}
                </div>
                <div class="text-[10px] text-navy/60 truncate">
                  {{ tool.is_published ? "Publicerad" : "Ej publicerad" }}
                </div>
              </button>
            </div>
          </div>
        </template>

        <div class="border-t border-navy/20 pt-[var(--huleedu-space-3)] flex flex-wrap gap-[var(--huleedu-space-2)]">
          <button
            type="button"
            class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none"
            @click="
              closeMenu();
              void router.push('/editor?pick=1');
            "
          >
            Välj verktyg…
          </button>

          <button
            v-if="props.canCreateTool"
            type="button"
            class="btn-primary h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 leading-none"
            @click="openCreateModal"
          >
            Skapa nytt…
          </button>
        </div>
      </div>
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
