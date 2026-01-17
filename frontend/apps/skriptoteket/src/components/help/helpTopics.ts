import { defineAsyncComponent, type AsyncComponentLoader, type Component } from "vue";

import type { HelpTopicId } from "./useHelp";
import HelpTopicLoadError from "./topics/HelpTopicLoadError.vue";
import HelpTopicLoading from "./topics/HelpTopicLoading.vue";

type HelpTopicLoader = AsyncComponentLoader<Component>;

const helpTopicLoaders: Record<HelpTopicId, HelpTopicLoader> = {
  login: () => import("./topics/HelpTopicLogin.vue"),
  home: () => import("./topics/HelpTopicHome.vue"),
  browse_professions: () => import("./topics/HelpTopicBrowseProfessions.vue"),
  browse_categories: () => import("./topics/HelpTopicBrowseCategories.vue"),
  browse_tools: () => import("./topics/HelpTopicBrowseTools.vue"),
  tools_run: () => import("./topics/HelpTopicToolsRun.vue"),
  tools_result: () => import("./topics/HelpTopicToolsResult.vue"),
  my_tools: () => import("./topics/HelpTopicMyTools.vue"),
  apps_detail: () => import("./topics/HelpTopicAppsDetail.vue"),
  suggestions_new: () => import("./topics/HelpTopicSuggestionsNew.vue"),
  admin_suggestions: () => import("./topics/HelpTopicAdminSuggestions.vue"),
  admin_tools: () => import("./topics/HelpTopicAdminTools.vue"),
  admin_editor: () => import("./topics/HelpTopicAdminEditor.vue"),
};

function createAsyncTopic(loader: HelpTopicLoader): Component {
  return defineAsyncComponent({
    loader,
    loadingComponent: HelpTopicLoading,
    errorComponent: HelpTopicLoadError,
    delay: 150,
    timeout: 15000,
  });
}

const helpTopicComponents: Record<HelpTopicId, Component> = {
  login: createAsyncTopic(helpTopicLoaders.login),
  home: createAsyncTopic(helpTopicLoaders.home),
  browse_professions: createAsyncTopic(helpTopicLoaders.browse_professions),
  browse_categories: createAsyncTopic(helpTopicLoaders.browse_categories),
  browse_tools: createAsyncTopic(helpTopicLoaders.browse_tools),
  tools_run: createAsyncTopic(helpTopicLoaders.tools_run),
  tools_result: createAsyncTopic(helpTopicLoaders.tools_result),
  my_tools: createAsyncTopic(helpTopicLoaders.my_tools),
  apps_detail: createAsyncTopic(helpTopicLoaders.apps_detail),
  suggestions_new: createAsyncTopic(helpTopicLoaders.suggestions_new),
  admin_suggestions: createAsyncTopic(helpTopicLoaders.admin_suggestions),
  admin_tools: createAsyncTopic(helpTopicLoaders.admin_tools),
  admin_editor: createAsyncTopic(helpTopicLoaders.admin_editor),
};

export function resolveHelpTopicComponent(topic: HelpTopicId | null): Component | null {
  if (!topic) {
    return null;
  }
  return helpTopicComponents[topic] ?? null;
}

export function prefetchHelpTopics(topics: HelpTopicId[]): void {
  for (const topic of new Set(topics)) {
    const loader = helpTopicLoaders[topic];
    if (loader) {
      void loader();
    }
  }
}
