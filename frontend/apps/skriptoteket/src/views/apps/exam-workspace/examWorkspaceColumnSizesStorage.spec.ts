/**
 * Exam workspace column sizes browser storage.
 *
 * Expected behavior:
 *   One localStorage key holds the remembered list, drawer and preview widths
 *   in px plus the list-collapsed flag. Reads return {} when the key is
 *   missing, the JSON is invalid, the schema rejects the value, or storage
 *   throws. Writes swallow storage errors, and writing an empty value removes
 *   the key instead of storing `{}`.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  EXAM_WORKSPACE_COLUMN_SIZES_STORAGE_KEY,
  readExamWorkspaceColumnSizes,
  writeExamWorkspaceColumnSizes,
} from "./examWorkspaceColumnSizesStorage";

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("examWorkspaceColumnSizesStorage", () => {
  it("round-trips widths and the collapsed flag", () => {
    writeExamWorkspaceColumnSizes({ list: 280, drawer: 320, preview: 500, listCollapsed: true });

    expect(readExamWorkspaceColumnSizes()).toEqual({
      list: 280,
      drawer: 320,
      preview: 500,
      listCollapsed: true,
    });
    expect(typeof localStorage.getItem(EXAM_WORKSPACE_COLUMN_SIZES_STORAGE_KEY)).toBe("string");
  });

  it("returns {} when the key is missing", () => {
    expect(readExamWorkspaceColumnSizes()).toEqual({});
  });

  it("returns {} for invalid JSON", () => {
    localStorage.setItem(EXAM_WORKSPACE_COLUMN_SIZES_STORAGE_KEY, "{not-json");

    expect(readExamWorkspaceColumnSizes()).toEqual({});
  });

  it("returns {} when an unknown extra field is stored", () => {
    localStorage.setItem(
      EXAM_WORKSPACE_COLUMN_SIZES_STORAGE_KEY,
      JSON.stringify({ list: 280, surprise: 1 }),
    );

    expect(readExamWorkspaceColumnSizes()).toEqual({});
  });

  it("rejects non-positive widths", () => {
    writeExamWorkspaceColumnSizes({ list: -10, drawer: 0 });

    expect(readExamWorkspaceColumnSizes()).toEqual({});
  });

  it("rejects non-finite widths", () => {
    writeExamWorkspaceColumnSizes({ list: Number.NaN, preview: Number.POSITIVE_INFINITY });

    expect(readExamWorkspaceColumnSizes()).toEqual({});
  });

  it("returns {} and does not throw when getItem throws", () => {
    vi.spyOn(localStorage, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });

    expect(() => readExamWorkspaceColumnSizes()).not.toThrow();
    expect(readExamWorkspaceColumnSizes()).toEqual({});
  });

  it("does not throw when setItem throws", () => {
    vi.spyOn(localStorage, "setItem").mockImplementation(() => {
      throw new Error("full");
    });

    expect(() => writeExamWorkspaceColumnSizes({ list: 280 })).not.toThrow();
  });

  it("removes the key when the value is empty", () => {
    writeExamWorkspaceColumnSizes({ list: 300 });
    expect(localStorage.getItem(EXAM_WORKSPACE_COLUMN_SIZES_STORAGE_KEY)).not.toBeNull();

    writeExamWorkspaceColumnSizes({});

    expect(localStorage.getItem(EXAM_WORKSPACE_COLUMN_SIZES_STORAGE_KEY)).toBeNull();
  });
});
