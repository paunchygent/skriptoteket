import { createApp } from "vue";

import DemoApp from "../DemoApp.vue";

const root = document.getElementById("spa-island-demo");
if (!root) {
  throw new Error("SPA island root not found: #spa-island-demo");
}

const message = root.dataset.message ?? "Hej från Vue + Vite!";
createApp(DemoApp, { message }).mount(root);
