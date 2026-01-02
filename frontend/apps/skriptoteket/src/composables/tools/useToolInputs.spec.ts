import { describe, it, expect } from "vitest";
import { ref, nextTick } from "vue";
import { useToolInputs } from "./useToolInputs";

describe("useToolInputs", () => {
  describe("nonFileFields", () => {
    it("returns empty array when no schema", () => {
      const schema = ref(null);
      const selectedFiles = ref<File[]>([]);
      const { nonFileFields } = useToolInputs({ schema, selectedFiles });

      expect(nonFileFields.value).toEqual([]);
    });

    it("excludes file fields", () => {
      const schema = ref([
        { name: "title", kind: "string" as const, label: "Title" },
        { name: "files", kind: "file" as const, label: "Files", accept: [], min: 1, max: 10 },
        { name: "count", kind: "integer" as const, label: "Count" },
      ]);
      const selectedFiles = ref<File[]>([]);
      const { nonFileFields } = useToolInputs({ schema, selectedFiles });

      expect(nonFileFields.value).toHaveLength(2);
      expect(nonFileFields.value.map((f) => f.name)).toEqual(["title", "count"]);
    });
  });

  describe("fileField", () => {
    it("returns null when no schema", () => {
      const schema = ref(null);
      const selectedFiles = ref<File[]>([]);
      const { fileField } = useToolInputs({ schema, selectedFiles });

      expect(fileField.value).toBeNull();
    });

    it("returns null when no file field in schema", () => {
      const schema = ref([{ name: "title", kind: "string" as const, label: "Title" }]);
      const selectedFiles = ref<File[]>([]);
      const { fileField } = useToolInputs({ schema, selectedFiles });

      expect(fileField.value).toBeNull();
    });

    it("returns file field when present", () => {
      const fileFieldDef = {
        name: "files",
        kind: "file" as const,
        label: "Documents",
        accept: [".pdf"],
        min: 1,
        max: 5,
      };
      const schema = ref([fileFieldDef]);
      const selectedFiles = ref<File[]>([]);
      const { fileField } = useToolInputs({ schema, selectedFiles });

      expect(fileField.value).toEqual(fileFieldDef);
    });
  });

  describe("fileAccept", () => {
    it("returns undefined when no file field", () => {
      const schema = ref([{ name: "title", kind: "string" as const, label: "Title" }]);
      const selectedFiles = ref<File[]>([]);
      const { fileAccept } = useToolInputs({ schema, selectedFiles });

      expect(fileAccept.value).toBeUndefined();
    });

    it("returns undefined when accept is empty", () => {
      const schema = ref([
        { name: "files", kind: "file" as const, label: "Files", accept: [], min: 1, max: 1 },
      ]);
      const selectedFiles = ref<File[]>([]);
      const { fileAccept } = useToolInputs({ schema, selectedFiles });

      expect(fileAccept.value).toBeUndefined();
    });

    it("returns comma-joined accept types", () => {
      const schema = ref([
        {
          name: "files",
          kind: "file" as const,
          label: "Files",
          accept: [".pdf", ".docx"],
          min: 1,
          max: 1,
        },
      ]);
      const selectedFiles = ref<File[]>([]);
      const { fileAccept } = useToolInputs({ schema, selectedFiles });

      expect(fileAccept.value).toBe(".pdf,.docx");
    });
  });

  describe("fileMultiple", () => {
    it("returns false when no file field exists", () => {
      const schema = ref(null);
      const selectedFiles = ref<File[]>([]);
      const { fileMultiple } = useToolInputs({ schema, selectedFiles });

      expect(fileMultiple.value).toBe(false);
    });

    it("returns false when max is 1", () => {
      const schema = ref([
        { name: "files", kind: "file" as const, label: "Files", accept: [], min: 1, max: 1 },
      ]);
      const selectedFiles = ref<File[]>([]);
      const { fileMultiple } = useToolInputs({ schema, selectedFiles });

      expect(fileMultiple.value).toBe(false);
    });

    it("returns true when max is greater than 1", () => {
      const schema = ref([
        { name: "files", kind: "file" as const, label: "Files", accept: [], min: 1, max: 5 },
      ]);
      const selectedFiles = ref<File[]>([]);
      const { fileMultiple } = useToolInputs({ schema, selectedFiles });

      expect(fileMultiple.value).toBe(true);
    });
  });

  describe("showFilePicker", () => {
    it("returns false when tool does not accept files", () => {
      const schema = ref([{ name: "title", kind: "string" as const, label: "Title" }]);
      const selectedFiles = ref<File[]>([]);
      const { showFilePicker } = useToolInputs({ schema, selectedFiles });

      expect(showFilePicker.value).toBe(false);
    });

    it("returns true when tool accepts files", () => {
      const schema = ref([
        { name: "files", kind: "file" as const, label: "Files", accept: [], min: 0, max: 1 },
      ]);
      const selectedFiles = ref<File[]>([]);
      const { showFilePicker } = useToolInputs({ schema, selectedFiles });

      expect(showFilePicker.value).toBe(true);
    });
  });

  describe("fileError", () => {
    it("returns null when no schema", () => {
      const schema = ref(null);
      const selectedFiles = ref<File[]>([]);
      const { fileError } = useToolInputs({ schema, selectedFiles });

      expect(fileError.value).toBeNull();
    });

    it("returns error when files provided but no file field in schema", () => {
      const schema = ref([{ name: "title", kind: "string" as const, label: "Title" }]);
      const selectedFiles = ref([new File(["test"], "test.pdf")]);
      const { fileError } = useToolInputs({ schema, selectedFiles });

      expect(fileError.value).toBe("Det här verktyget tar inte emot filer.");
    });

    it("returns error when too few files", () => {
      const schema = ref([
        { name: "files", kind: "file" as const, label: "Files", accept: [], min: 2, max: 5 },
      ]);
      const selectedFiles = ref([new File(["test"], "test.pdf")]);
      const { fileError } = useToolInputs({ schema, selectedFiles });

      expect(fileError.value).toBe("Välj minst 2 filer.");
    });

    it("returns singular error when min is 1", () => {
      const schema = ref([
        { name: "files", kind: "file" as const, label: "Files", accept: [], min: 1, max: 5 },
      ]);
      const selectedFiles = ref<File[]>([]);
      const { fileError } = useToolInputs({ schema, selectedFiles });

      expect(fileError.value).toBe("Välj minst en fil.");
    });

    it("returns error when too many files", () => {
      const schema = ref([
        { name: "files", kind: "file" as const, label: "Files", accept: [], min: 1, max: 2 },
      ]);
      const selectedFiles = ref([
        new File(["a"], "a.pdf"),
        new File(["b"], "b.pdf"),
        new File(["c"], "c.pdf"),
      ]);
      const { fileError } = useToolInputs({ schema, selectedFiles });

      expect(fileError.value).toBe("Du kan välja max 2 filer.");
    });

    it("returns singular error when max is 1", () => {
      const schema = ref([
        { name: "files", kind: "file" as const, label: "Files", accept: [], min: 1, max: 1 },
      ]);
      const selectedFiles = ref([new File(["a"], "a.pdf"), new File(["b"], "b.pdf")]);
      const { fileError } = useToolInputs({ schema, selectedFiles });

      expect(fileError.value).toBe("Du kan välja max 1 fil.");
    });

    it("returns null when file count is valid", () => {
      const schema = ref([
        { name: "files", kind: "file" as const, label: "Files", accept: [], min: 1, max: 3 },
      ]);
      const selectedFiles = ref([new File(["a"], "a.pdf"), new File(["b"], "b.pdf")]);
      const { fileError } = useToolInputs({ schema, selectedFiles });

      expect(fileError.value).toBeNull();
    });
  });

  describe("fieldErrors", () => {
    it("returns empty object when no schema", () => {
      const schema = ref(null);
      const selectedFiles = ref<File[]>([]);
      const { fieldErrors } = useToolInputs({ schema, selectedFiles });

      expect(fieldErrors.value).toEqual({});
    });

    it("validates integer fields", () => {
      const schema = ref([{ name: "count", kind: "integer" as const, label: "Count" }]);
      const selectedFiles = ref<File[]>([]);
      const { values, fieldErrors } = useToolInputs({ schema, selectedFiles });

      values.value.count = "abc";
      expect(fieldErrors.value).toEqual({ count: "Ogiltigt heltal." });

      values.value.count = "42";
      expect(fieldErrors.value).toEqual({});
    });

    it("validates number fields", () => {
      const schema = ref([{ name: "rate", kind: "number" as const, label: "Rate" }]);
      const selectedFiles = ref<File[]>([]);
      const { values, fieldErrors } = useToolInputs({ schema, selectedFiles });

      values.value.rate = "not-a-number";
      expect(fieldErrors.value).toEqual({ rate: "Ogiltigt tal." });

      values.value.rate = "3.14";
      expect(fieldErrors.value).toEqual({});
    });

    it("validates enum fields", () => {
      const schema = ref([
        {
          name: "color",
          kind: "enum" as const,
          label: "Color",
          options: [
            { value: "red", label: "Red" },
            { value: "blue", label: "Blue" },
          ],
        },
      ]);
      const selectedFiles = ref<File[]>([]);
      const { values, fieldErrors } = useToolInputs({ schema, selectedFiles });

      values.value.color = "green";
      expect(fieldErrors.value).toEqual({ color: "Ogiltigt val." });

      values.value.color = "red";
      expect(fieldErrors.value).toEqual({});
    });

    it("skips validation for empty values", () => {
      const schema = ref([
        { name: "count", kind: "integer" as const, label: "Count" },
        { name: "rate", kind: "number" as const, label: "Rate" },
      ]);
      const selectedFiles = ref<File[]>([]);
      const { values, fieldErrors } = useToolInputs({ schema, selectedFiles });

      values.value.count = "";
      values.value.rate = "";
      expect(fieldErrors.value).toEqual({});
    });
  });

  describe("isValid", () => {
    it("returns true when no errors", () => {
      const schema = ref([
        { name: "files", kind: "file" as const, label: "Files", accept: [], min: 1, max: 3 },
        { name: "count", kind: "integer" as const, label: "Count" },
      ]);
      const selectedFiles = ref([new File(["test"], "test.pdf")]);
      const { values, isValid } = useToolInputs({ schema, selectedFiles });

      values.value.count = "42";
      expect(isValid.value).toBe(true);
    });

    it("returns false when file error", () => {
      const schema = ref([
        { name: "files", kind: "file" as const, label: "Files", accept: [], min: 1, max: 1 },
      ]);
      const selectedFiles = ref<File[]>([]);
      const { isValid } = useToolInputs({ schema, selectedFiles });

      expect(isValid.value).toBe(false);
    });

    it("returns false when field error", () => {
      const schema = ref([{ name: "count", kind: "integer" as const, label: "Count" }]);
      const selectedFiles = ref<File[]>([]);
      const { values, isValid } = useToolInputs({ schema, selectedFiles });

      values.value.count = "invalid";
      expect(isValid.value).toBe(false);
    });
  });

  describe("resetValues()", () => {
    it("clears values when no schema", () => {
      const schema = ref(null);
      const selectedFiles = ref<File[]>([]);
      const { values, resetValues } = useToolInputs({ schema, selectedFiles });

      values.value = { foo: "bar" };
      resetValues();

      expect(values.value).toEqual({});
    });

    it("sets default values for all non-file fields", () => {
      const schema = ref([
        { name: "title", kind: "string" as const, label: "Title" },
        { name: "enabled", kind: "boolean" as const, label: "Enabled" },
        { name: "files", kind: "file" as const, label: "Files", accept: [], min: 1, max: 1 },
      ]);
      const selectedFiles = ref<File[]>([]);
      const { values, resetValues } = useToolInputs({ schema, selectedFiles });

      values.value = { title: "Modified", enabled: true };
      resetValues();

      expect(values.value).toEqual({ title: "", enabled: false });
    });
  });

  describe("buildApiValues()", () => {
    it("returns empty object when no schema", () => {
      const schema = ref(null);
      const selectedFiles = ref<File[]>([]);
      const { buildApiValues } = useToolInputs({ schema, selectedFiles });

      expect(buildApiValues()).toEqual({});
    });

    it("converts boolean values", () => {
      const schema = ref([{ name: "enabled", kind: "boolean" as const, label: "Enabled" }]);
      const selectedFiles = ref<File[]>([]);
      const { values, buildApiValues } = useToolInputs({ schema, selectedFiles });

      values.value.enabled = true;
      expect(buildApiValues()).toEqual({ enabled: true });

      values.value.enabled = false;
      expect(buildApiValues()).toEqual({ enabled: false });
    });

    it("converts integer values", () => {
      const schema = ref([{ name: "count", kind: "integer" as const, label: "Count" }]);
      const selectedFiles = ref<File[]>([]);
      const { values, buildApiValues } = useToolInputs({ schema, selectedFiles });

      values.value.count = "42";
      expect(buildApiValues()).toEqual({ count: 42 });
    });

    it("converts number values", () => {
      const schema = ref([{ name: "rate", kind: "number" as const, label: "Rate" }]);
      const selectedFiles = ref<File[]>([]);
      const { values, buildApiValues } = useToolInputs({ schema, selectedFiles });

      values.value.rate = "3.14";
      expect(buildApiValues()).toEqual({ rate: 3.14 });
    });

    it("trims string values", () => {
      const schema = ref([{ name: "title", kind: "string" as const, label: "Title" }]);
      const selectedFiles = ref<File[]>([]);
      const { values, buildApiValues } = useToolInputs({ schema, selectedFiles });

      values.value.title = "  padded  ";
      expect(buildApiValues()).toEqual({ title: "padded" });
    });

    it("omits empty string values", () => {
      const schema = ref([{ name: "title", kind: "string" as const, label: "Title" }]);
      const selectedFiles = ref<File[]>([]);
      const { values, buildApiValues } = useToolInputs({ schema, selectedFiles });

      values.value.title = "";
      expect(buildApiValues()).toEqual({});
    });

    it("throws on invalid integer", () => {
      const schema = ref([{ name: "count", kind: "integer" as const, label: "Count" }]);
      const selectedFiles = ref<File[]>([]);
      const { values, buildApiValues } = useToolInputs({ schema, selectedFiles });

      values.value.count = "invalid";
      expect(() => buildApiValues()).toThrow("Ogiltigt heltal.");
    });

    it("throws on invalid number", () => {
      const schema = ref([{ name: "rate", kind: "number" as const, label: "Rate" }]);
      const selectedFiles = ref<File[]>([]);
      const { values, buildApiValues } = useToolInputs({ schema, selectedFiles });

      values.value.rate = "invalid";
      expect(() => buildApiValues()).toThrow("Ogiltigt tal.");
    });
  });

  describe("watch schema changes", () => {
    it("resets values when schema changes", async () => {
      const schema = ref([{ name: "title", kind: "string" as const, label: "Title" }]);
      const selectedFiles = ref<File[]>([]);
      const { values } = useToolInputs({ schema, selectedFiles });

      values.value.title = "Modified";

      schema.value = [{ name: "newField", kind: "string" as const, label: "New" }];
      await nextTick();

      expect(values.value).toEqual({ newField: "" });
    });
  });
});
