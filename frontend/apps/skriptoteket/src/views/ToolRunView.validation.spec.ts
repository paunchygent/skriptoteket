import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { components } from "../api/openapi";
import ToolRunView from "./ToolRunView.vue";

type Metadata = components["schemas"]["ToolMetadataResponse"];
const api = vi.hoisted(() => ({ apiGet: vi.fn(), apiFetch: vi.fn() }));
vi.mock("../api/client", () => ({ ...api, isApiError: () => false }));
vi.mock("../stores/auth", () => ({
  useAuthStore: () => ({ bootstrapped: true, isAuthenticated: false }),
}));
vi.mock("vue-router", () => ({ useRoute: () => ({ params: { slug: "required-files" } }) }));
vi.mock("../composables/tools/useToolSettings", () => ({
  useToolSettings: () => ({
    settingsSchema: ref([]), values: ref({}), hasSchema: ref(false),
    isLoading: ref(false), isSaving: ref(false), errorMessage: ref(null), saveSettings: vi.fn(),
  }),
}));

const wrappers: Array<ReturnType<typeof mount>> = [];
beforeEach(() => {
  api.apiGet.mockReset();
  api.apiFetch.mockReset();
});
afterEach(() => {
  wrappers.forEach((wrapper) => wrapper.unmount());
  wrappers.length = 0;
});

function mountRunner(schema: Metadata["input_schema"]) {
  const metadata: Metadata = {
    id: "required-files-id", slug: "required-files", title: "Filverktyg", summary: null,
    input_schema: schema,
    upload_constraints: { max_file_bytes: 10000, max_files: 3, max_total_bytes: 30000 },
    usage_instructions: null, usage_instructions_seen: false,
  };
  api.apiGet.mockResolvedValueOnce(metadata);
  const wrapper = mount(ToolRunView, {
    global: { stubs: { RouterLink: true, VaultPickerModal: true } },
  });
  wrappers.push(wrapper);
  return wrapper;
}

describe("ToolRunView required file validation", () => {
  it.each(["integer", "number"] as const)("announces the real %s validation error without a request", async (kind) => {
    const wrapper = mountRunner([{ name: "amount", kind, label: "Antal" }]);
    await flushPromises();
    const input = wrapper.get("input");
    await input.setValue("12junk");
    const message = kind === "integer" ? "Ogiltigt heltal." : "Ogiltigt tal.";
    expect(input.attributes("aria-invalid")).toBe("true");
    const description = input.attributes("aria-describedby");
    expect(description).toBeTruthy();
    expect(wrapper.findAll("[id]").find((node) => node.attributes("id") === description)?.text()).toBe(message);
    const run = wrapper.findAll("button").find((button) => button.text() === "Kör")!;
    await run.trigger("click");
    expect(wrapper.get('[role="alert"]').text()).toContain(message);
    expect(api.apiFetch).not.toHaveBeenCalled();
    await input.setValue("12");
    expect(input.attributes("aria-invalid")).not.toBe("true");
    expect(input.attributes("aria-describedby")).toBeUndefined();
  });

  it("blocks a second request while an accepted run is submitting and permits retry after failure", async () => {
    const wrapper = mountRunner([]);
    await flushPromises();
    let rejectRun!: (reason: Error) => void;
    api.apiFetch.mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectRun = reject; }));
    const run = wrapper.findAll("button").find((button) => button.text() === "Kör")!;
    await run.trigger("click");
    expect(run.element.disabled).toBe(true);
    await run.trigger("click");
    expect(api.apiFetch).toHaveBeenCalledTimes(1);
    rejectRun(new Error("Körningen kunde inte starta."));
    await flushPromises();
    expect(run.element.disabled).toBe(false);
    expect(wrapper.get('[role="alert"]').text()).toContain("Körningen kunde inte starta.");
  });

  it.each([1, 2])("lets Kör explain a missing minimum of %i files without starting a request", async (minimum) => {
    const metadata: Metadata = {
      id: "required-files-id", slug: "required-files", title: "Filverktyg", summary: null,
      input_schema: [{ name: "documents", kind: "file", label: "Dokument", min: minimum, max: 3 }],
      upload_constraints: { max_file_bytes: 10000, max_files: 3, max_total_bytes: 30000 },
      usage_instructions: null, usage_instructions_seen: false,
    };
    api.apiGet.mockResolvedValue(metadata);
    const wrapper = mount(ToolRunView, {
      global: { stubs: { RouterLink: true, VaultPickerModal: true } },
    });
    wrappers.push(wrapper);
    await flushPromises();

    const run = wrapper.findAll("button").find((button) => button.text() === "Kör")!;
    expect(run).toBeDefined();
    expect(run.element.disabled).toBe(false);
    await run.trigger("click");
    await flushPromises();

    const message = minimum === 1 ? "Välj minst en fil." : `Välj minst ${minimum} filer.`;
    expect(wrapper.get('[role="alert"]').text()).toContain(message);
    expect(api.apiFetch).not.toHaveBeenCalled();
    expect(api.apiGet).toHaveBeenCalledTimes(1);
  });
});
