import { createApp, type App } from "vue";

import EditorIslandApp from "../editor/EditorIslandApp.vue";
import type { EditorBootPayload } from "../editor/types";

import "../styles.css";

type EditorIslandRoot = HTMLElement & {
  dataset: {
    spaEditorMounted?: string;
  };
};

let mountedApp: App<Element> | null = null;

function getEditorMountKey(payload: EditorBootPayload): string {
  return [
    payload.tool_id,
    payload.selected_version_id ?? "",
    payload.save_mode,
    payload.derived_from_version_id ?? "",
    payload.entrypoint,
  ].join(":");
}

function mountEditorIsland(): void {
  const root = document.getElementById("spa-island-editor") as EditorIslandRoot | null;
  if (!root) {
    // Navigated away; allow GC to clean up the mounted app state.
    if (mountedApp) mountedApp.unmount();
    mountedApp = null;
    return;
  }

  const payloadEl = document.getElementById("spa-island-editor-payload");
  if (!payloadEl || payloadEl.textContent === null) return;

  let payload: EditorBootPayload;
  try {
    payload = JSON.parse(payloadEl.textContent) as EditorBootPayload;
  } catch (err) {
    console.error("Failed to parse editor SPA payload", err);
    return;
  }

  const mountKey = getEditorMountKey(payload);
  if (root.dataset.spaEditorMounted === mountKey) return;

  // Prevent leaks when navigating between editor pages via HTMX (hx-boost).
  if (mountedApp) mountedApp.unmount();
  mountedApp = null;

  root.dataset.spaEditorMounted = mountKey;

  document.getElementById("spa-editor-main-target")?.replaceChildren();
  document.getElementById("spa-editor-sidebar-target")?.replaceChildren();

  root.replaceChildren();
  mountedApp = createApp(EditorIslandApp, { payload });
  mountedApp.mount(root);
}

mountEditorIsland();

document.body.addEventListener("htmx:afterSwap", () => {
  mountEditorIsland();
});
