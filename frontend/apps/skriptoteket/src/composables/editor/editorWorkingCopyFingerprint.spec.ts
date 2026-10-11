import { describe, expect, it } from "vitest";

import type { EditorWorkingCopyFields } from "./editorPersistence";
import { areFieldsEqual, fieldsFingerprint } from "./editorWorkingCopyFingerprint";

function fieldsWithBundleFiles(bundleFiles: Record<string, string>): EditorWorkingCopyFields {
  return {
    entrypoint: "run_tool",
    sourceCode: "print('hi')",
    bundleFiles,
    settingsSchemaText: "[]",
    inputSchemaText: "[]",
    usageInstructions: "",
  };
}

describe("editorWorkingCopyFingerprint", () => {
  it("distinguishes bundles whose concatenated text is identical", () => {
    const oneFile = fieldsWithBundleFiles({ "a.py": "xy", "b.py": "" });
    const twoFiles = fieldsWithBundleFiles({ "a.py": "x", "b.py": "y" });

    expect(fieldsFingerprint(oneFile)).not.toBe(fieldsFingerprint(twoFiles));
    expect(areFieldsEqual(oneFile, twoFiles)).toBe(false);
  });

  it("is stable when the same bundle files arrive in another insertion order", () => {
    const first = fieldsWithBundleFiles({ "a.py": "x", "b.py": "y" });
    const second = fieldsWithBundleFiles({ "b.py": "y", "a.py": "x" });

    expect(fieldsFingerprint(first)).toBe(fieldsFingerprint(second));
    expect(areFieldsEqual(first, second)).toBe(true);
  });
});
