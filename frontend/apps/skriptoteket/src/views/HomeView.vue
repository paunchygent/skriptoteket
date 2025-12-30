<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { apiGet, isApiError } from "../api/client";
import type { components } from "../api/openapi";
import FavoritesSection from "../components/home/FavoritesSection.vue";
import RecentToolsSection from "../components/home/RecentToolsSection.vue";
import SectionHeader from "../components/home/SectionHeader.vue";
import { IconArrow } from "../components/icons";
import { useFavorites } from "../composables/useFavorites";
import { useLoginModal } from "../composables/useLoginModal";
import { useAuthStore } from "../stores/auth";
import type { CatalogItem } from "../types/catalog";

type ListMyRunsResponse = components["schemas"]["ListMyRunsResponse"];
type ListMyToolsResponse = components["schemas"]["ListMyToolsResponse"];
type ListAdminToolsResponse = components["schemas"]["ListAdminToolsResponse"];
type ListFavoritesResponse = components["schemas"]["ListFavoritesResponse"];
type ListRecentToolsResponse = components["schemas"]["ListRecentToolsResponse"];

const auth = useAuthStore();
const loginModal = useLoginModal();
const { toggleFavorite, isToggling } = useFavorites();

const isAuthenticated = computed(() => auth.isAuthenticated);
const canSeeContributor = computed(() => auth.hasAtLeastRole("contributor"));
const canSeeAdmin = computed(() => auth.hasAtLeastRole("admin"));
const userName = computed(() => auth.displayName);

// Dashboard data
const runsCount = ref(0);
const runsInList = ref(0);
const runsLoading = ref(false);
const currentMonth = new Date().toLocaleString("sv-SE", { month: "long" });

function formatCount(n: number): string {
  if (n >= 1000) {
    const k = n / 1000;
    return k % 1 === 0 ? `${k}k` : `${k.toFixed(1)}k`;
  }
  return String(n);
}

const toolsTotal = ref(0);
const toolsPublished = ref(0);
const toolsLoading = ref(false);

const adminToolsTotal = ref(0);
const adminToolsPublished = ref(0);
const adminPendingReview = ref(0);
const adminLoading = ref(false);

const dashboardError = ref<string | null>(null);

// Favorites and recent tools
const favorites = ref<CatalogItem[]>([]);
const recentTools = ref<CatalogItem[]>([]);

async function loadUserDashboard(): Promise<void> {
  runsLoading.value = true;
  try {
    const response = await apiGet<ListMyRunsResponse>("/api/v1/my-runs");
    runsCount.value = response.total_count;
    runsInList.value = response.runs.length;
  } catch (error: unknown) {
    if (isApiError(error)) {
      dashboardError.value = error.message;
    }
  } finally {
    runsLoading.value = false;
  }
}

async function loadContributorDashboard(): Promise<void> {
  toolsLoading.value = true;
  try {
    const response = await apiGet<ListMyToolsResponse>("/api/v1/my-tools");
    toolsTotal.value = response.tools.length;
    toolsPublished.value = response.tools.filter((t) => t.is_published).length;
  } catch (error: unknown) {
    if (isApiError(error)) {
      dashboardError.value = error.message;
    }
  } finally {
    toolsLoading.value = false;
  }
}

async function loadAdminDashboard(): Promise<void> {
  adminLoading.value = true;
  try {
    const response = await apiGet<ListAdminToolsResponse>("/api/v1/admin/tools");
    adminToolsTotal.value = response.tools.length;
    adminToolsPublished.value = response.tools.filter((t) => t.is_published).length;
    adminPendingReview.value = response.tools.filter((t) => t.has_pending_review).length;
  } catch (error: unknown) {
    if (isApiError(error)) {
      dashboardError.value = error.message;
    }
  } finally {
    adminLoading.value = false;
  }
}

async function loadFavorites(): Promise<void> {
  try {
    const response = await apiGet<ListFavoritesResponse>("/api/v1/favorites?limit=5");
    favorites.value = response.items as CatalogItem[];
  } catch {
    // Silent fail - section just won't show
  }
}

async function loadRecentTools(): Promise<void> {
  try {
    const response = await apiGet<ListRecentToolsResponse>("/api/v1/me/recent-tools?limit=5");
    recentTools.value = response.items as CatalogItem[];
  } catch {
    // Silent fail - section just won't show
  }
}

async function handleFavoriteToggled(payload: { id: string; isFavorite: boolean }): Promise<void> {
  if (isToggling(payload.id)) return;

  const nextIsFavorite = !payload.isFavorite;

  // Optimistic update for favorites list
  const prevFavorites = favorites.value;
  favorites.value = prevFavorites.flatMap((item) => {
    if (item.id !== payload.id) return item;
    if (!nextIsFavorite) return [];
    return { ...item, is_favorite: nextIsFavorite };
  });

  // Optimistic update for recent tools list
  const prevRecent = recentTools.value;
  recentTools.value = prevRecent.map((item) =>
    item.id === payload.id ? { ...item, is_favorite: nextIsFavorite } : item
  );

  const finalIsFavorite = await toggleFavorite(payload.id, payload.isFavorite);
  if (finalIsFavorite !== nextIsFavorite) {
    favorites.value = prevFavorites;
    recentTools.value = prevRecent;
  }
}

onMounted(async () => {
  if (!isAuthenticated.value) return;

  // Load all dashboard data in parallel
  await Promise.all([
    loadUserDashboard(),
    loadFavorites(),
    loadRecentTools(),
    canSeeContributor.value ? loadContributorDashboard() : Promise.resolve(),
    canSeeAdmin.value ? loadAdminDashboard() : Promise.resolve(),
  ]);
});
</script>

<template>
  <div>
    <!-- ═══════════════════════════════════════════════════════════════════════
         PRE-LOGIN: Hero + Features
         ═══════════════════════════════════════════════════════════════════════ -->
    <template v-if="!isAuthenticated">
      <!-- Hero Section -->
      <section class="py-16 text-center">
        <h1
          class="font-serif text-5xl md:text-6xl font-bold text-navy tracking-tighter leading-tight"
        >
          Verktyg för lärare
        </h1>
        <p class="mt-4 text-lg text-navy/70 max-w-xl mx-auto">
          Ladda upp en fil, välj ett verktyg, ladda ned resultatet.
        </p>
        <p class="mt-10">
          <button
            type="button"
            class="btn-primary px-8 py-4 text-sm font-semibold tracking-wide"
            @click="loginModal.open()"
          >
            Logga in
          </button>
        </p>
      </section>

      <!-- Features Section -->
      <section class="py-16 border-t border-navy/10">
        <div class="grid gap-12 md:grid-cols-3 max-w-5xl mx-auto">
          <!-- Card 1 -->
          <div class="relative">
            <div
              class="absolute -top-3 -left-2 w-8 h-8 bg-burgundy border border-navy flex items-center justify-center"
            >
              <span class="text-canvas font-bold text-sm">1</span>
            </div>
            <div class="pt-6 pl-5 border-l-2 border-navy min-h-[120px]">
              <h3 class="font-semibold text-navy text-lg">Dela och återanvänd</h3>
              <p class="mt-2 text-sm text-navy/70 leading-relaxed">
                Slipp skriva samma skript om och om igen. Hitta färdiga verktyg
                eller bidra med egna idéer.
              </p>
            </div>
          </div>

          <!-- Card 2 -->
          <div class="relative">
            <div
              class="absolute -top-3 -left-2 w-8 h-8 bg-burgundy border border-navy flex items-center justify-center"
            >
              <span class="text-canvas font-bold text-sm">2</span>
            </div>
            <div class="pt-6 pl-5 border-l-2 border-navy min-h-[120px]">
              <h3 class="font-semibold text-navy text-lg">Enkel uppladdning</h3>
              <p class="mt-2 text-sm text-navy/70 leading-relaxed">
                Ladda upp en fil, kör, ladda ner resultatet. Ingen IDE, ingen
                terminal, ingen installation.
              </p>
            </div>
          </div>

          <!-- Card 3 -->
          <div class="relative">
            <div
              class="absolute -top-3 -left-2 w-8 h-8 bg-burgundy border border-navy flex items-center justify-center"
            >
              <span class="text-canvas font-bold text-sm">3</span>
            </div>
            <div class="pt-6 pl-5 border-l-2 border-navy min-h-[120px]">
              <h3 class="font-semibold text-navy text-lg">Tryggt och lokalt</h3>
              <p class="mt-2 text-sm text-navy/70 leading-relaxed">
                Alla filer behandlas säkert på vår server. Verktyg granskas
                innan publicering.
              </p>
            </div>
          </div>
        </div>
      </section>
    </template>

    <!-- ═══════════════════════════════════════════════════════════════════════
         POST-LOGIN: Role-guarded Dashboard
         ═══════════════════════════════════════════════════════════════════════ -->
    <template v-else>
      <div class="max-w-4xl space-y-10">
        <!-- Error message -->
        <div
          v-if="dashboardError"
          class="p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
        >
          {{ dashboardError }}
        </div>

        <!-- Greeting -->
        <section class="space-y-1">
          <h1 class="font-serif text-3xl font-bold text-navy">
            Välkommen<template v-if="userName">, {{ userName }}</template>
          </h1>
          <p class="text-sm text-navy/70">Vad vill du göra?</p>
        </section>

        <!-- ═══════════════════════════════════════════════════════════════════
             PERSONALIZED SECTIONS: Favorites and Recent Tools
             ═══════════════════════════════════════════════════════════════════ -->
        <FavoritesSection
          :items="favorites"
          :is-toggling="isToggling"
          @favorite-toggled="handleFavoriteToggled"
        />

        <RecentToolsSection
          :items="recentTools"
          :is-toggling="isToggling"
          @favorite-toggled="handleFavoriteToggled"
        />

        <!-- ═══════════════════════════════════════════════════════════════════
             USER SECTION: All authenticated users
             ═══════════════════════════════════════════════════════════════════ -->
        <section class="space-y-4">
          <div class="grid gap-5 sm:grid-cols-2">
            <!-- Senaste körningar -->
            <RouterLink
              to="/my-runs"
              class="dashboard-card group"
            >
              <div class="card-header">
                <span class="card-label">Senaste körningar</span>
                <IconArrow
                  :size="18"
                  class="card-arrow"
                />
              </div>
              <div class="card-stats">
                <span
                  v-if="runsLoading"
                  class="text-navy/40"
                >...</span>
                <span
                  v-else
                  class="stat-number"
                >{{ formatCount(runsCount) }}</span>
                <span class="stat-label">körningar i {{ currentMonth }}</span>
              </div>
              <p class="card-description">
                Se de senaste {{ runsInList }} körningarna.
              </p>
            </RouterLink>

            <!-- Hitta verktyg -->
            <RouterLink
              to="/browse"
              class="dashboard-card group"
            >
              <div class="card-header">
                <span class="card-label">Hitta verktyg</span>
                <IconArrow
                  :size="18"
                  class="card-arrow"
                />
              </div>
              <p class="card-description mt-4">
                Bläddra i katalogen och kör det du behöver.
              </p>
            </RouterLink>
          </div>
        </section>

        <!-- ═══════════════════════════════════════════════════════════════════
             CONTRIBUTOR SECTION: contributor+ only
             ═══════════════════════════════════════════════════════════════════ -->
        <section
          v-if="canSeeContributor"
          class="space-y-4"
        >
          <SectionHeader title="Bidragsgivare" />
          <div class="grid gap-5 sm:grid-cols-2">
            <!-- Mina verktyg -->
            <RouterLink
              to="/my-tools"
              class="dashboard-card group"
            >
              <div class="card-header">
                <span class="card-label">Mina verktyg</span>
                <IconArrow
                  :size="18"
                  class="card-arrow"
                />
              </div>
              <div class="card-stats">
                <span
                  v-if="toolsLoading"
                  class="text-navy/40"
                >...</span>
                <template v-else>
                  <span class="stat-number">{{ toolsTotal }}</span>
                  <span class="stat-label">
                    verktyg
                    <span
                      v-if="toolsPublished > 0"
                      class="text-success"
                    >
                      ({{ toolsPublished }} publicerade)
                    </span>
                  </span>
                </template>
              </div>
              <p class="card-description">
                Hantera verktyg du ansvarar för.
              </p>
            </RouterLink>

            <!-- Föreslå verktyg -->
            <RouterLink
              to="/suggestions/new"
              class="dashboard-card group"
            >
              <div class="card-header">
                <span class="card-label">Föreslå verktyg</span>
                <IconArrow
                  :size="18"
                  class="card-arrow"
                />
              </div>
              <p class="card-description mt-4">
                Har du en idé? Skicka in ett förslag.
              </p>
            </RouterLink>
          </div>
        </section>

        <!-- ═══════════════════════════════════════════════════════════════════
             ADMIN SECTION: admin+ only
             ═══════════════════════════════════════════════════════════════════ -->
        <section
          v-if="canSeeAdmin"
          class="space-y-4"
        >
          <SectionHeader title="Administration" />
          <div class="grid gap-5 sm:grid-cols-2">
            <!-- Att granska -->
            <RouterLink
              to="/admin/tools"
              class="dashboard-card group"
              :class="{ 'border-warning': adminPendingReview > 0 }"
            >
              <div class="card-header">
                <span class="card-label">Att granska</span>
                <IconArrow
                  :size="18"
                  class="card-arrow"
                />
              </div>
              <div class="card-stats">
                <span
                  v-if="adminLoading"
                  class="text-navy/40"
                >...</span>
                <template v-else>
                  <span
                    class="stat-number"
                    :class="{ 'text-warning': adminPendingReview > 0 }"
                  >
                    {{ adminPendingReview }}
                  </span>
                  <span class="stat-label">väntar på granskning</span>
                </template>
              </div>
              <p class="card-description">
                Granska och publicera verktyg.
              </p>
            </RouterLink>

            <!-- Alla verktyg -->
            <RouterLink
              to="/admin/tools"
              class="dashboard-card group"
            >
              <div class="card-header">
                <span class="card-label">Alla verktyg</span>
                <IconArrow
                  :size="18"
                  class="card-arrow"
                />
              </div>
              <div class="card-stats">
                <span
                  v-if="adminLoading"
                  class="text-navy/40"
                >...</span>
                <template v-else>
                  <span class="stat-number">{{ adminToolsTotal }}</span>
                  <span class="stat-label">
                    totalt
                    <span
                      v-if="adminToolsPublished > 0"
                      class="text-success"
                    >
                      ({{ adminToolsPublished }} publicerade)
                    </span>
                  </span>
                </template>
              </div>
              <p class="card-description">
                Administrera verktyg i systemet.
              </p>
            </RouterLink>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* Dashboard card */
.dashboard-card {
  display: block;
  padding: 1.25rem;
  border: 1px solid var(--color-navy);
  background-color: white;
  box-shadow: 4px 4px 0 0 var(--color-navy);
  text-decoration: none;
  transition: all 0.15s ease;
}

.dashboard-card:hover {
  box-shadow: 6px 6px 0 0 var(--color-navy);
  transform: translate(-2px, -2px);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.card-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-navy);
  transition: color 0.15s ease;
}

.dashboard-card:hover .card-label {
  color: var(--color-burgundy);
}

.card-arrow {
  color: var(--color-navy);
  flex-shrink: 0;
  transition: transform 0.15s ease, color 0.15s ease;
}

.dashboard-card:hover .card-arrow {
  transform: translateX(4px);
  color: var(--color-burgundy);
}

.card-stats {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.stat-number {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-navy);
  line-height: 1;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--color-navy);
  opacity: 0.6;
}

.card-description {
  margin-top: 0.5rem;
  font-size: 0.8125rem;
  color: var(--color-navy);
  opacity: 0.6;
  line-height: 1.4;
}

/* Success color for published counts */
.text-success {
  color: var(--huleedu-success);
}

/* Warning color for pending review */
.text-warning {
  color: var(--huleedu-warning);
}

.border-warning {
  border-color: var(--huleedu-warning);
}
</style>
