import {
  defineAsyncComponent,
  defineComponent,
  h,
  type AsyncComponentLoader,
  type Component,
} from "vue";

import type { HelpTopicId } from "./helpTopicCatalog";
import HelpTopicLoadError from "./topics/HelpTopicLoadError.vue";
import HelpTopicLoading from "./topics/HelpTopicLoading.vue";

type HelpTopicLoader = AsyncComponentLoader<Component>;

/**
 * Create a loader that binds a ``section`` prop to
 * ``HelpTopicPlanner.vue`` so each planner mode gets its own async
 * component entry without duplicating the Vue file.
 */
function plannerSectionLoader(section: string): HelpTopicLoader {
  return () =>
    import("./topics/HelpTopicPlanner.vue").then((mod) =>
      defineComponent({
        name: `HelpTopicPlanner_${section}`,
        render() {
          return h(mod.default, { section });
        },
      }),
    );
}

const helpTopicLoaders: Record<HelpTopicId, HelpTopicLoader> = {
  login: () => import("./topics/HelpTopicLogin.vue"),
  auth_lifecycle: () => import("./topics/HelpTopicAuthLifecycle.vue"),
  provisioning_required: () => import("./topics/HelpTopicProvisioningRequired.vue"),
  home: () => import("./topics/HelpTopicHome.vue"),
  browse_professions: () => import("./topics/HelpTopicBrowseProfessions.vue"),
  browse_categories: () => import("./topics/HelpTopicBrowseCategories.vue"),
  browse_tools: () => import("./topics/HelpTopicBrowseTools.vue"),
  tools_run: () => import("./topics/HelpTopicToolsRun.vue"),
  tools_result: () => import("./topics/HelpTopicToolsResult.vue"),
  vault: () => import("./topics/HelpTopicVault.vue"),
  profile: () => import("./topics/HelpTopicProfile.vue"),
  my_tools: () => import("./topics/HelpTopicMyTools.vue"),
  editor_hub: () => import("./topics/HelpTopicEditorHub.vue"),
  apps_detail: () => import("./topics/HelpTopicAppsDetail.vue"),
  suggestions_new: () => import("./topics/HelpTopicSuggestionsNew.vue"),
  admin_suggestions: () => import("./topics/HelpTopicAdminSuggestions.vue"),
  admin_tools: () => import("./topics/HelpTopicAdminTools.vue"),
  admin_editor: () => import("./topics/HelpTopicAdminEditor.vue"),
  admin_users: () => import("./topics/HelpTopicAdminUsers.vue"),
  forbidden: () => import("./topics/HelpTopicForbidden.vue"),
  route_recovery: () => import("./topics/HelpTopicRouteRecovery.vue"),
  planner_overview: plannerSectionLoader("planner_overview"),
  planner_seating: plannerSectionLoader("planner_seating"),
  planner_grouping: plannerSectionLoader("planner_grouping"),
  planner_rules: plannerSectionLoader("planner_rules"),
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
  auth_lifecycle: createAsyncTopic(helpTopicLoaders.auth_lifecycle),
  provisioning_required: createAsyncTopic(helpTopicLoaders.provisioning_required),
  home: createAsyncTopic(helpTopicLoaders.home),
  browse_professions: createAsyncTopic(helpTopicLoaders.browse_professions),
  browse_categories: createAsyncTopic(helpTopicLoaders.browse_categories),
  browse_tools: createAsyncTopic(helpTopicLoaders.browse_tools),
  tools_run: createAsyncTopic(helpTopicLoaders.tools_run),
  tools_result: createAsyncTopic(helpTopicLoaders.tools_result),
  vault: createAsyncTopic(helpTopicLoaders.vault),
  profile: createAsyncTopic(helpTopicLoaders.profile),
  my_tools: createAsyncTopic(helpTopicLoaders.my_tools),
  editor_hub: createAsyncTopic(helpTopicLoaders.editor_hub),
  apps_detail: createAsyncTopic(helpTopicLoaders.apps_detail),
  suggestions_new: createAsyncTopic(helpTopicLoaders.suggestions_new),
  admin_suggestions: createAsyncTopic(helpTopicLoaders.admin_suggestions),
  admin_tools: createAsyncTopic(helpTopicLoaders.admin_tools),
  admin_editor: createAsyncTopic(helpTopicLoaders.admin_editor),
  admin_users: createAsyncTopic(helpTopicLoaders.admin_users),
  forbidden: createAsyncTopic(helpTopicLoaders.forbidden),
  route_recovery: createAsyncTopic(helpTopicLoaders.route_recovery),
  planner_overview: createAsyncTopic(helpTopicLoaders.planner_overview),
  planner_seating: createAsyncTopic(helpTopicLoaders.planner_seating),
  planner_grouping: createAsyncTopic(helpTopicLoaders.planner_grouping),
  planner_rules: createAsyncTopic(helpTopicLoaders.planner_rules),
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
