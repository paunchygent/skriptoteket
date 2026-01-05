import { describe, expect, it } from "vitest";

import {
  VIRTUAL_FILE_IDS,
  isVirtualFileId,
  virtualFileTextFromEditorBoot,
  virtualFileTextFromEditorFields,
} from "./virtualFiles";

describe("virtualFiles", () => {
  it("exposes canonical virtual file ids in a stable order", () => {
    expect(VIRTUAL_FILE_IDS).toEqual([
      "tool.py",
      "entrypoint.txt",
      "settings_schema.json",
      "input_schema.json",
      "usage_instructions.md",
    ]);
  });

  it("detects virtual file ids", () => {
    for (const id of VIRTUAL_FILE_IDS) {
      expect(isVirtualFileId(id)).toBe(true);
    }

    expect(isVirtualFileId("tool.ts")).toBe(false);
    expect(isVirtualFileId("")).toBe(false);
    expect(isVirtualFileId(null)).toBe(false);
    expect(isVirtualFileId(undefined)).toBe(false);
    expect(isVirtualFileId(123)).toBe(false);
  });

  it("maps editor fields to canonical virtual file ids", () => {
    const result = virtualFileTextFromEditorFields({
      entrypoint: "run_tool",
      sourceCode: "print('hi')",
      settingsSchemaText: "{\n  \"type\": \"object\"\n}\n",
      inputSchemaText: "{\n  \"type\": \"array\"\n}\n",
      usageInstructions: "Do the thing",
    });

    expect(result).toEqual({
      "tool.py": "print('hi')",
      "entrypoint.txt": "run_tool",
      "settings_schema.json": "{\n  \"type\": \"object\"\n}\n",
      "input_schema.json": "{\n  \"type\": \"array\"\n}\n",
      "usage_instructions.md": "Do the thing",
    });
  });

  it("maps editor boot response fields to canonical virtual file ids", () => {
    const result = virtualFileTextFromEditorBoot({
      entrypoint: "run_tool",
      source_code: "print('hi')",
      settings_schema: [{ type: "object" }],
      input_schema: undefined,
      usage_instructions: null,
    });

    expect(result).toEqual({
      "tool.py": "print('hi')",
      "entrypoint.txt": "run_tool",
      "settings_schema.json": "[\n  {\n    \"type\": \"object\"\n  }\n]",
      "input_schema.json": "",
      "usage_instructions.md": "",
    });
  });
});
