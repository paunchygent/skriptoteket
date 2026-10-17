<script setup lang="ts">
import { RouterLink } from "vue-router";
import CreateDraftToolModal from "../../components/admin/CreateDraftToolModal.vue";
import { SystemMessage, UiDenseSpinner } from "../../components/ui";
import { useCreateDraftToolModal } from "../../composables/admin/useCreateDraftToolModal";
import { useEditorHub } from "../../composables/editor/useEditorHub";

const {
  canCreateTool,
  searchQuery,
  searchRef,
  isSearchOpen,
  toolSearch,
  searchErrorMessage,
  isSearchLoading,
  shouldShowSearchOverflow,
  recentTools,
  sortedMyTools,
  isLoadingMyTools,
  myToolsError,
  redirectError,
  isRedirecting,
  openTool,
} = useEditorHub();

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
            class="w-full h-[28px] border border-[var(--huleedu-panel-border)] bg-canvas px-2.5 text-[11px] text-navy shadow-none leading-none"
            placeholder="Sök på titel eller URL-namn…"
            @focus="isSearchOpen = true"
          >
          <div class="text-[10px] text-navy/50">
            Söker i alla verktyg du har rätt att redigera.
          </div>

          <div
            v-if="isSearchOpen && toolSearch.normalizedQuery"
            class="absolute left-0 top-full mt-[var(--huleedu-space-2)] w-[min(520px,92vw)] rounded-[var(--huleedu-panel-radius)] border border-[var(--huleedu-panel-border)] bg-modal shadow-md z-[var(--huleedu-z-tooltip)]"
          >
            <div class="p-[var(--huleedu-space-3)] space-y-[var(--huleedu-space-2)]">
              <div class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
                Sökresultat
              </div>

              <SystemMessage
                v-if="searchErrorMessage"
                :model-value="searchErrorMessage"
                tone="failure"
                role="alert"
              />

              <div
                v-else-if="isSearchLoading"
                class="flex items-center gap-2 text-[11px] text-navy/60"
              >
                <UiDenseSpinner />
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
      tone="warning"
      dismissible
      role="status"
      aria-live="polite"
      aria-atomic="true"
    />

    <div
      v-if="isRedirecting"
      class="flex items-center gap-[var(--huleedu-space-3)] p-[var(--huleedu-space-4)] rounded-[var(--huleedu-panel-radius)] border border-[var(--huleedu-panel-border)] bg-panel text-sm text-navy/70"
    >
      <UiDenseSpinner :size="16" />
      <span>Öppnar senaste verktyg…</span>
    </div>

    <div
      v-else
      class="grid gap-[var(--huleedu-space-6)] lg:grid-cols-2"
    >
      <section
        class="rounded-[var(--huleedu-panel-radius)] border border-[var(--huleedu-panel-border)] bg-panel p-[var(--huleedu-space-4)] space-y-[var(--huleedu-space-4)]"
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
        class="rounded-[var(--huleedu-panel-radius)] border border-[var(--huleedu-panel-border)] bg-panel p-[var(--huleedu-space-4)] space-y-[var(--huleedu-space-4)]"
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
          tone="failure"
          dismissible
          role="alert"
          aria-live="assertive"
          aria-atomic="true"
        />

        <div
          v-if="isLoadingMyTools"
          data-testid="editor-hub-my-tools-loading"
          class="flex items-center gap-[var(--huleedu-space-3)] p-[var(--huleedu-space-4)] border border-navy/20 bg-canvas text-sm text-navy/70"
        >
          <UiDenseSpinner :size="16" />
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
