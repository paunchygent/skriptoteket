import type { Ref } from "vue";

import type { VirtualFileTextMap } from "../virtualFiles";

type EditorFieldRefs = {
  entrypoint: Ref<string>;
  sourceCode: Ref<string>;
  settingsSchemaText: Ref<string>;
  inputSchemaText: Ref<string>;
  usageInstructions: Ref<string>;
};

type AppliedEditOpsSnapshot = {
  beforeFiles: VirtualFileTextMap;
  afterFiles: VirtualFileTextMap;
  beforeFingerprint: string;
  afterFingerprint: string;
  appliedAt: string;
};

export function cloneVirtualFiles(files: VirtualFileTextMap): VirtualFileTextMap {
  return { ...files };
}

export function virtualFilesFingerprint(files: VirtualFileTextMap): string {
  return [
    files["entrypoint.txt"],
    files["tool.py"],
    files["settings_schema.json"],
    files["input_schema.json"],
    files["usage_instructions.md"],
  ].join("\u0000");
}

export function applyVirtualFiles(fields: EditorFieldRefs, nextFiles: VirtualFileTextMap): void {
  fields.entrypoint.value = nextFiles["entrypoint.txt"];
  fields.sourceCode.value = nextFiles["tool.py"];
  fields.settingsSchemaText.value = nextFiles["settings_schema.json"];
  fields.inputSchemaText.value = nextFiles["input_schema.json"];
  fields.usageInstructions.value = nextFiles["usage_instructions.md"];
}

export function createAppliedSnapshot(
  beforeFiles: VirtualFileTextMap,
  afterFiles: VirtualFileTextMap,
): AppliedEditOpsSnapshot {
  return {
    beforeFiles,
    afterFiles,
    beforeFingerprint: virtualFilesFingerprint(beforeFiles),
    afterFingerprint: virtualFilesFingerprint(afterFiles),
    appliedAt: new Date().toISOString(),
  };
}

export type { AppliedEditOpsSnapshot, EditorFieldRefs };
