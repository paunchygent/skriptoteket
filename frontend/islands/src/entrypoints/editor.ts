import { createApp } from "vue";

import EditorIslandApp from "../editor/EditorIslandApp.vue";
import type { EditorBootPayload } from "../editor/types";

import "../styles.css";

const root = document.getElementById("spa-island-editor");
if (!root) {
  throw new Error("SPA island root not found: #spa-island-editor");
}

const payloadEl = document.getElementById("spa-island-editor-payload");
if (!payloadEl || payloadEl.textContent === null) {
  throw new Error("SPA island payload not found: #spa-island-editor-payload");
}

const payload = JSON.parse(payloadEl.textContent) as EditorBootPayload;

document.getElementById("spa-editor-main-target")?.replaceChildren();
document.getElementById("spa-editor-sidebar-target")?.replaceChildren();

createApp(EditorIslandApp, { payload }).mount(root);

