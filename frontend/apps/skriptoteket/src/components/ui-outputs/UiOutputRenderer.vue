<script setup lang="ts">
import { computed } from "vue";
import type { Component } from "vue";

import type { components } from "../../api/openapi";

import UiOutputHtmlSandboxed from "./UiOutputHtmlSandboxed.vue";
import UiOutputJson from "./UiOutputJson.vue";
import UiOutputMarkdown from "./UiOutputMarkdown.vue";
import UiOutputNotice from "./UiOutputNotice.vue";
import UiOutputTable from "./UiOutputTable.vue";
import UiOutputVegaLite from "./UiOutputVegaLite.vue";

type UiOutput = NonNullable<components["schemas"]["UiPayloadV2"]["outputs"]>[number];
type UiOutputKind = UiOutput["kind"];

const props = defineProps<{ output: UiOutput }>();

const COMPONENT_BY_KIND: Record<UiOutputKind, Component> = {
  notice: UiOutputNotice,
  markdown: UiOutputMarkdown,
  table: UiOutputTable,
  json: UiOutputJson,
  html_sandboxed: UiOutputHtmlSandboxed,
  vega_lite: UiOutputVegaLite,
};

const component = computed<Component>(() => COMPONENT_BY_KIND[props.output.kind]);
</script>

<template>
  <component
    :is="component"
    :output="output"
  />
</template>
