<script setup lang="ts">
import { computed } from "vue";

import { useAuthStore } from "../../stores/auth";
import { getHelpIndexItems, type HelpIndexItem } from "./helpTopicCatalog";
import { useHelp } from "./useHelp";

const auth = useAuthStore();
const { showTopic } = useHelp();

const isAuthenticated = computed(() => auth.isAuthenticated);
const canSeeContributor = computed(() => auth.hasAtLeastRole("contributor"));
const canSeeAdmin = computed(() => auth.hasAtLeastRole("admin"));
const canSeeSuperuser = computed(() => auth.hasAtLeastRole("superuser"));

const starterIndexItems: HelpIndexItem[] = getHelpIndexItems("starter");
const contributorIndexItems: HelpIndexItem[] = getHelpIndexItems("contributor");
const adminIndexItems: HelpIndexItem[] = getHelpIndexItems("admin");
const superuserIndexItems: HelpIndexItem[] = getHelpIndexItems("superuser");
const loggedOutIndexItems: HelpIndexItem[] = getHelpIndexItems("logged_out");

const authenticatedIndexSections = computed(() =>
  [
    {
      key: "starter",
      title: "Kom igång",
      items: starterIndexItems,
      isVisible: true,
    },
    {
      key: "contributor",
      title: "Bidra",
      items: contributorIndexItems,
      isVisible: canSeeContributor.value,
    },
    {
      key: "admin",
      title: "Admin",
      items: adminIndexItems,
      isVisible: canSeeAdmin.value,
    },
    {
      key: "superuser",
      title: "Superadmin",
      items: superuserIndexItems,
      isVisible: canSeeSuperuser.value,
    },
  ].filter((section) => section.isVisible),
);
</script>

<template>
  <div class="space-y-6">
    <div class="space-y-3">
      <h3 class="text-lg font-semibold text-navy">Hjälpindex</h3>
      <p
        v-if="!isAuthenticated"
        class="text-sm text-navy/60"
      >
        Välj ett ämne för att komma igång.
      </p>
    </div>

    <div
      v-if="isAuthenticated"
      class="space-y-6"
    >
      <section
        v-for="section in authenticatedIndexSections"
        :key="section.key"
        class="space-y-3"
      >
        <h4 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          {{ section.title }}
        </h4>
        <ul
          data-test="help-index-list"
          class="border border-navy/15 bg-white divide-y divide-navy/15"
        >
          <li
            v-for="item in section.items"
            :key="item.topic"
          >
            <button
              type="button"
              class="w-full text-left flex items-start justify-between gap-4 px-4 py-3 hover:bg-navy/5 transition-colors"
              @click="showTopic(item.topic)"
            >
              <span class="flex flex-col gap-1">
                <span class="text-sm font-semibold text-navy">{{ item.title }}</span>
                <span class="text-xs text-navy/60">{{ item.description }}</span>
              </span>
              <span class="text-navy/40">→</span>
            </button>
          </li>
        </ul>
      </section>
    </div>

    <section
      v-else
      class="space-y-3"
    >
      <ul
        data-test="help-index-list"
        class="border border-navy/15 bg-white divide-y divide-navy/15"
      >
        <li
          v-for="item in loggedOutIndexItems"
          :key="item.topic"
        >
          <button
            type="button"
            class="w-full text-left flex items-center justify-between gap-4 px-4 py-3 hover:bg-navy/5 transition-colors"
            @click="showTopic(item.topic)"
          >
            <span class="text-sm font-semibold text-navy">{{ item.title }}</span>
            <span class="text-navy/40">→</span>
          </button>
        </li>
      </ul>
    </section>
  </div>
</template>
