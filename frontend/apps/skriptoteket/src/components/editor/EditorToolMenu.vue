<script setup lang="ts">
/**
 * Dense tool-switch menu for the editor toolbar.
 *
 * Relationships:
 * - consumes shared dense menu primitives while keeping tool-search content local
 * - provides the editor-side proving ground for generic dense menu triggers and items
 */

import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useCreateDraftToolModal } from "../../composables/admin/useCreateDraftToolModal";
import { useAdminToolsIndex } from "../../composables/admin/useAdminToolsIndex";
import { listRecentEditorTools } from "../../composables/editor/editorRecentTools";
import { searchTools } from "../../composables/tools/toolSearch";
import { useAuthStore } from "../../stores/auth";
import { IconPlus } from "../icons";
import {
  DENSE_FORM_INPUT_CLASS,
  DENSE_MENU_PANEL_CLASS,
  DENSE_MENU_SECTION_LABEL_CLASS,
  UiDenseActionButton,
  UiDenseMenuButton,
  denseMenuItemClass,
} from "../ui";
import { useDenseMenuSurface } from "../ui/useDenseMenuSurface";
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

const isOpen = ref(false);
const menuContainerRef = ref<HTMLElement | null>(null);
const menuRef = ref<HTMLElement | null>(null);
const menuTriggerRef = ref<InstanceType<typeof UiDenseMenuButton> | null>(null);
const searchQuery = ref("");

const {
  closeMenu,
  toggleMenu,
  onTriggerKeydown,
  onMenuKeydown,
} = useDenseMenuSurface({
  isOpen,
  containerRef: menuContainerRef,
  menuRef,
  triggerRef: menuTriggerRef,
});

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

function handleToggleMenu(): void {
  toggleMenu();
}

watch(
  () => isOpen.value,
  (value) => {
    if (value) {
      refreshRecents();
      void loadMyTools();
      return;
    }
    searchQuery.value = "";
  },
);

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
  searchQuery.value = "";
  await router.push(`/admin/tools/${toolId}`);
}

async function openToolPicker(): Promise<void> {
  closeMenu();
  searchQuery.value = "";
  await router.push("/editor?pick=1");
}

async function openAdminToolsIndex(): Promise<void> {
  closeMenu();
  searchQuery.value = "";
  await router.push("/admin/tools");
}

function openCreateModal(): void {
  closeMenu();
  searchQuery.value = "";
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
    ref="menuContainerRef"
    class="relative"
  >
    <UiDenseMenuButton
      ref="menuTriggerRef"
      label="Verktyg"
      :expanded="isOpen"
      @click="handleToggleMenu"
      @keydown="onTriggerKeydown"
    />

    <div
      v-if="isOpen"
      ref="menuRef"
      class="absolute left-0 top-full mt-[var(--huleedu-space-2)] w-[min(420px,92vw)] bg-canvas"
      :class="DENSE_MENU_PANEL_CLASS"
      role="menu"
      @keydown="onMenuKeydown"
    >
      <div class="p-[var(--huleedu-space-3)] space-y-[var(--huleedu-space-3)]">
        <div class="space-y-[var(--huleedu-space-1)]">
          <div :class="DENSE_MENU_SECTION_LABEL_CLASS">
            Aktivt verktyg
          </div>
          <div class="text-[11px] text-navy/70">
            <span class="font-semibold">{{ props.activeToolTitle || "(Namnlöst verktyg)" }}</span>
            <span class="text-navy/50"> · </span>
            <span class="font-mono text-navy/60">{{ props.activeToolSlug || props.activeToolId }}</span>
          </div>
        </div>

        <div class="space-y-[var(--huleedu-space-1)]">
          <label :class="DENSE_MENU_SECTION_LABEL_CLASS">
            Sök
          </label>
          <input
            v-model="searchQuery"
            :class="DENSE_FORM_INPUT_CLASS"
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
          <div :class="DENSE_MENU_SECTION_LABEL_CLASS">
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
            class="max-h-[min(220px,50vh)] overflow-y-auto border border-navy/20 bg-panel divide-y divide-navy/15"
          >
            <button
              v-for="tool in toolSearch.results"
              :key="tool.id"
              type="button"
              :class="denseMenuItemClass()"
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
                class="font-semibold uppercase tracking-wide text-navy underline underline-offset-4 hover:text-action"
                @click="void openAdminToolsIndex()"
              >
                Visa alla verktyg
              </button>
            </template>
          </div>
        </div>

        <template v-else>
          <div class="border-t border-navy/20 pt-[var(--huleedu-space-3)] space-y-[var(--huleedu-space-2)]">
            <div :class="DENSE_MENU_SECTION_LABEL_CLASS">
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
              class="max-h-[min(220px,50vh)] overflow-y-auto border border-navy/20 bg-panel divide-y divide-navy/15"
            >
              <button
                v-for="tool in recentTools"
                :key="tool.toolId"
                type="button"
                :class="denseMenuItemClass()"
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
              <div :class="DENSE_MENU_SECTION_LABEL_CLASS">
                Mina verktyg
              </div>
              <button
                v-if="props.canCreateTool"
                type="button"
                class="text-[10px] font-semibold uppercase tracking-wide text-navy underline underline-offset-4 hover:text-action"
                @click="void openAdminToolsIndex()"
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
              class="max-h-[min(220px,50vh)] overflow-y-auto border border-navy/20 bg-panel divide-y divide-navy/15"
            >
              <button
                v-for="tool in sortedMyTools"
                :key="tool.id"
                type="button"
                :class="denseMenuItemClass()"
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
          <UiDenseActionButton
            label="Välj verktyg…"
            @click="void openToolPicker()"
          />

          <UiDenseActionButton
            v-if="props.canCreateTool"
            label="Skapa nytt…"
            tone="primary"
            @click="openCreateModal"
          >
            <template #leading>
              <IconPlus :size="14" />
            </template>
          </UiDenseActionButton>
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
