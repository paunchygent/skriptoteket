import { createApp } from "vue";

import RuntimeIslandApp from "../runtime/RuntimeIslandApp.vue";

import "../styles.css";

type RuntimeIslandRoot = HTMLElement & {
  dataset: {
    spaRuntime?: string;
    spaRuntimeMounted?: string;
    toolId?: string;
    runId?: string;
    context?: string;
  };
};

function mountRuntimeIslands(): void {
  const roots = Array.from(
    document.querySelectorAll<RuntimeIslandRoot>("[data-spa-runtime='true']"),
  );

  for (const root of roots) {
    if (root.dataset.spaRuntimeMounted === "true") continue;

    const toolId = root.dataset.toolId;
    const runId = root.dataset.runId;
    const context = root.dataset.context ?? "default";

    if (!toolId || !runId) continue;

    root.dataset.spaRuntimeMounted = "true";

    const container = root.closest<HTMLElement>("[data-spa-runtime-container='true']");
    for (const fallback of container?.querySelectorAll<HTMLElement>(
      "[data-spa-runtime-fallback='true']",
    ) ?? []) {
      fallback.hidden = true;
    }

    root.hidden = false;
    root.replaceChildren();
    createApp(RuntimeIslandApp, { toolId, runId, context }).mount(root);
  }
}

mountRuntimeIslands();

document.body.addEventListener("htmx:afterSwap", () => {
  mountRuntimeIslands();
});
