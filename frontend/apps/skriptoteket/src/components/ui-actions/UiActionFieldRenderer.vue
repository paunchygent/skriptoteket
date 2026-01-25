<script setup lang="ts">
import { computed } from "vue";
import type { Component } from "vue";

import type { components } from "../../api/openapi";

import UiActionFieldBoolean from "./UiActionFieldBoolean.vue";
import UiActionFieldEnum from "./UiActionFieldEnum.vue";
import UiActionFieldInteger from "./UiActionFieldInteger.vue";
import UiActionFieldMultiEnum from "./UiActionFieldMultiEnum.vue";
import UiActionFieldNumber from "./UiActionFieldNumber.vue";
import UiActionFieldString from "./UiActionFieldString.vue";
import UiActionFieldText from "./UiActionFieldText.vue";
import UiActionFieldFileRef from "./UiActionFieldFileRef.vue";
import type { FileRefInfo, FileRefSource } from "../../composables/tools/fileRefHelpers";

type UiActionField = NonNullable<components["schemas"]["UiFormAction"]["fields"]>[number];
type UiActionFieldKind = UiActionField["kind"];

type FieldValue = string | boolean | string[];

const props = defineProps<{
  field: UiActionField;
  idBase: string;
  modelValue: FieldValue;
  density?: "default" | "compact";
  availableFileRefs?: FileRefInfo[];
  fileRefErrors?: Record<string, string | null>;
  fileRefSourcesOverride?: FileRefSource[] | null;
}>();

const emit = defineEmits<{ "update:modelValue": [value: FieldValue] }>();

const COMPONENT_BY_KIND: Record<UiActionFieldKind, Component> = {
  string: UiActionFieldString,
  text: UiActionFieldText,
  integer: UiActionFieldInteger,
  number: UiActionFieldNumber,
  boolean: UiActionFieldBoolean,
  enum: UiActionFieldEnum,
  multi_enum: UiActionFieldMultiEnum,
  file_ref: UiActionFieldFileRef,
};

const component = computed<Component>(() => COMPONENT_BY_KIND[props.field.kind]);

const fieldId = computed(() => `${props.idBase}-f-${props.field.name}`);

const componentProps = computed<Record<string, unknown>>(() => {
  const baseProps = {
    field: props.field,
    modelValue: props.modelValue,
    density: props.density,
  };

  if (props.field.kind === "file_ref") {
    return {
      ...baseProps,
      availableFileRefs: props.availableFileRefs ?? [],
      errorMessage: props.fileRefErrors?.[props.field.name] ?? null,
      sourcesOverride: props.fileRefSourcesOverride ?? null,
    };
  }

  if (props.field.kind === "enum" || props.field.kind === "multi_enum") {
    return {
      ...baseProps,
      idBase: fieldId.value,
    };
  }

  return {
    ...baseProps,
    id: fieldId.value,
  };
});

function onUpdate(value: FieldValue): void {
  emit("update:modelValue", value);
}
</script>

<template>
  <component
    :is="component"
    v-bind="componentProps"
    @update:model-value="onUpdate"
  />
</template>
