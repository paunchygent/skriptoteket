import { describe, it, expect } from "vitest";
import { buildApiValues, buildFormValues, type SettingsField } from "./toolSettingsHelpers";

describe("toolSettingsHelpers", () => {
  describe("buildFormValues()", () => {
    it("converts string field from API", () => {
      const schema: SettingsField[] = [{ name: "title", kind: "string", label: "Title" }];
      const apiValues = { title: "Hello" };

      const result = buildFormValues(schema, apiValues);

      expect(result).toEqual({ title: "Hello" });
    });

    it("converts null/undefined string to empty string", () => {
      const schema: SettingsField[] = [{ name: "title", kind: "string", label: "Title" }];
      const apiValues = { title: null };

      const result = buildFormValues(schema, apiValues);

      expect(result).toEqual({ title: "" });
    });

    it("converts number to string for string fields", () => {
      const schema: SettingsField[] = [{ name: "count", kind: "string", label: "Count" }];
      const apiValues = { count: 42 };

      const result = buildFormValues(schema, apiValues);

      expect(result).toEqual({ count: "42" });
    });

    it("converts boolean field from API", () => {
      const schema: SettingsField[] = [{ name: "enabled", kind: "boolean", label: "Enabled" }];

      expect(buildFormValues(schema, { enabled: true })).toEqual({ enabled: true });
      expect(buildFormValues(schema, { enabled: false })).toEqual({ enabled: false });
      expect(buildFormValues(schema, { enabled: null })).toEqual({ enabled: false });
      expect(buildFormValues(schema, {})).toEqual({ enabled: false });
    });

    it("converts multi_enum field from API", () => {
      const schema: SettingsField[] = [
        {
          name: "tags",
          kind: "multi_enum",
          label: "Tags",
          options: [
            { label: "A", value: "a" },
            { label: "B", value: "b" },
            { label: "C", value: "c" },
          ],
        },
      ];

      expect(buildFormValues(schema, { tags: ["a", "b"] })).toEqual({ tags: ["a", "b"] });
      expect(buildFormValues(schema, { tags: [] })).toEqual({ tags: [] });
      expect(buildFormValues(schema, { tags: null })).toEqual({ tags: [] });
      expect(buildFormValues(schema, {})).toEqual({ tags: [] });
    });

    it("handles mixed invalid multi_enum arrays", () => {
      const schema: SettingsField[] = [
        {
          name: "tags",
          kind: "multi_enum",
          label: "Tags",
          options: [
            { label: "A", value: "a" },
            { label: "B", value: "b" },
          ],
        },
      ];

      // Array with non-string items should return empty
      expect(buildFormValues(schema, { tags: [1, 2, 3] })).toEqual({ tags: [] });
    });

    it("converts integer field as string for form", () => {
      const schema: SettingsField[] = [{ name: "count", kind: "integer", label: "Count" }];

      expect(buildFormValues(schema, { count: 42 })).toEqual({ count: "42" });
      expect(buildFormValues(schema, { count: 0 })).toEqual({ count: "0" });
    });

    it("converts number field as string for form", () => {
      const schema: SettingsField[] = [{ name: "rate", kind: "number", label: "Rate" }];

      expect(buildFormValues(schema, { rate: 3.14 })).toEqual({ rate: "3.14" });
    });

    it("handles multiple fields", () => {
      const schema: SettingsField[] = [
        { name: "title", kind: "string", label: "Title" },
        { name: "enabled", kind: "boolean", label: "Enabled" },
        { name: "count", kind: "integer", label: "Count" },
      ];
      const apiValues = { title: "Test", enabled: true, count: 5 };

      const result = buildFormValues(schema, apiValues);

      expect(result).toEqual({ title: "Test", enabled: true, count: "5" });
    });
  });

  describe("buildApiValues()", () => {
    it("converts string field to API", () => {
      const schema: SettingsField[] = [{ name: "title", kind: "string", label: "Title" }];
      const formValues = { title: "Hello" };

      const result = buildApiValues(schema, formValues);

      expect(result).toEqual({ title: "Hello" });
    });

    it("trims string values", () => {
      const schema: SettingsField[] = [{ name: "title", kind: "string", label: "Title" }];
      const formValues = { title: "  padded  " };

      const result = buildApiValues(schema, formValues);

      expect(result).toEqual({ title: "padded" });
    });

    it("omits empty strings from result", () => {
      const schema: SettingsField[] = [{ name: "title", kind: "string", label: "Title" }];
      const formValues = { title: "" };

      const result = buildApiValues(schema, formValues);

      expect(result).toEqual({});
    });

    it("converts boolean field to API", () => {
      const schema: SettingsField[] = [{ name: "enabled", kind: "boolean", label: "Enabled" }];

      expect(buildApiValues(schema, { enabled: true })).toEqual({ enabled: true });
      expect(buildApiValues(schema, { enabled: false })).toEqual({ enabled: false });
    });

    it("converts multi_enum field to API", () => {
      const schema: SettingsField[] = [
        {
          name: "tags",
          kind: "multi_enum",
          label: "Tags",
          options: [
            { label: "A", value: "a" },
            { label: "B", value: "b" },
            { label: "C", value: "c" },
          ],
        },
      ];

      expect(buildApiValues(schema, { tags: ["a", "b"] })).toEqual({ tags: ["a", "b"] });
      expect(buildApiValues(schema, { tags: [] })).toEqual({ tags: [] });
    });

    it("converts integer field from string", () => {
      const schema: SettingsField[] = [{ name: "count", kind: "integer", label: "Count" }];

      expect(buildApiValues(schema, { count: "42" })).toEqual({ count: 42 });
      expect(buildApiValues(schema, { count: "-5" })).toEqual({ count: -5 });
      expect(buildApiValues(schema, { count: "0" })).toEqual({ count: 0 });
    });

    it("omits empty integer field", () => {
      const schema: SettingsField[] = [{ name: "count", kind: "integer", label: "Count" }];

      expect(buildApiValues(schema, { count: "" })).toEqual({});
    });

    it("throws on invalid integer", () => {
      const schema: SettingsField[] = [{ name: "count", kind: "integer", label: "Count" }];

      expect(() => buildApiValues(schema, { count: "abc" })).toThrow("Ogiltigt heltal.");
    });

    it("truncates decimals for integer fields (parseInt behavior)", () => {
      const schema: SettingsField[] = [{ name: "count", kind: "integer", label: "Count" }];

      // parseInt("12.5") returns 12 - this is JavaScript behavior
      expect(buildApiValues(schema, { count: "12.5" })).toEqual({ count: 12 });
    });

    it("converts number field from string", () => {
      const schema: SettingsField[] = [{ name: "rate", kind: "number", label: "Rate" }];

      expect(buildApiValues(schema, { rate: "3.14" })).toEqual({ rate: 3.14 });
      expect(buildApiValues(schema, { rate: "-2.5" })).toEqual({ rate: -2.5 });
      expect(buildApiValues(schema, { rate: "42" })).toEqual({ rate: 42 });
    });

    it("omits empty number field", () => {
      const schema: SettingsField[] = [{ name: "rate", kind: "number", label: "Rate" }];

      expect(buildApiValues(schema, { rate: "" })).toEqual({});
    });

    it("throws on invalid number", () => {
      const schema: SettingsField[] = [{ name: "rate", kind: "number", label: "Rate" }];

      expect(() => buildApiValues(schema, { rate: "abc" })).toThrow("Ogiltigt tal.");
    });

    it("uses default value when field not in formValues", () => {
      const schema: SettingsField[] = [
        { name: "enabled", kind: "boolean", label: "Enabled" },
        { name: "tags", kind: "multi_enum", label: "Tags", options: [{ label: "A", value: "a" }] },
      ];

      const result = buildApiValues(schema, {});

      expect(result).toEqual({ enabled: false, tags: [] });
    });

    it("handles multiple fields", () => {
      const schema: SettingsField[] = [
        { name: "title", kind: "string", label: "Title" },
        { name: "enabled", kind: "boolean", label: "Enabled" },
        { name: "count", kind: "integer", label: "Count" },
      ];
      const formValues = { title: "Test", enabled: true, count: "5" };

      const result = buildApiValues(schema, formValues);

      expect(result).toEqual({ title: "Test", enabled: true, count: 5 });
    });
  });

  describe("roundtrip conversion", () => {
    it("API -> Form -> API preserves values", () => {
      const schema: SettingsField[] = [
        { name: "title", kind: "string", label: "Title" },
        { name: "enabled", kind: "boolean", label: "Enabled" },
        { name: "count", kind: "integer", label: "Count" },
        {
          name: "tags",
          kind: "multi_enum",
          label: "Tags",
          options: [
            { label: "A", value: "a" },
            { label: "B", value: "b" },
            { label: "C", value: "c" },
          ],
        },
      ];
      const apiValues = { title: "Test", enabled: true, count: 42, tags: ["a", "c"] };

      const formValues = buildFormValues(schema, apiValues);
      const backToApi = buildApiValues(schema, formValues);

      expect(backToApi).toEqual(apiValues);
    });
  });
});
