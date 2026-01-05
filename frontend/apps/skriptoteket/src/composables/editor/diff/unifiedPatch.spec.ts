import { describe, expect, it } from "vitest";

import { buildUnifiedPatch, normalizeTextForPatch } from "./unifiedPatch";

describe("unifiedPatch", () => {
  describe("normalizeTextForPatch", () => {
    it("normalizes CRLF and CR to LF", () => {
      expect(normalizeTextForPatch("a\r\nb\rc")).toBe("a\nb\nc\n");
    });

    it("returns empty strings as-is", () => {
      expect(normalizeTextForPatch("")).toBe("");
    });

    it("adds a trailing newline for non-empty strings", () => {
      expect(normalizeTextForPatch("hello")).toBe("hello\n");
      expect(normalizeTextForPatch("hello\n")).toBe("hello\n");
    });
  });

  describe("buildUnifiedPatch", () => {
    it("builds LF-normalized patches with stable pseudo-paths", () => {
      const patch = buildUnifiedPatch({
        virtualFileId: "tool.py",
        before: "hello\r\n",
        after: "hello2\r\n",
      });

      expect(patch).toContain("--- a/tool.py");
      expect(patch).toContain("+++ b/tool.py");
      expect(patch).toContain("-hello");
      expect(patch).toContain("+hello2");
      expect(patch).not.toContain("\r");
      expect(patch.endsWith("\n")).toBe(true);
    });

    it("forces a trailing newline and avoids 'No newline at end of file' markers", () => {
      const patch = buildUnifiedPatch({
        virtualFileId: "usage_instructions.md",
        before: "hello",
        after: "hello2",
      });

      expect(patch).not.toContain("No newline at end of file");
      expect(patch.endsWith("\n")).toBe(true);
    });
  });
});
