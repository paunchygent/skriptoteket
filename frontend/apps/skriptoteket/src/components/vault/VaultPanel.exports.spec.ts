/**
 * Mina filer saved-export grouping (TASK-SKRIPT-39-04-08 M5/M13).
 *
 * One exam is one listed file that carries its saved exports; each saved export has its
 * own download action and the exam row keeps its existing file controls.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import VaultPanel from "./VaultPanel.vue";

type VaultFileInfo = {
  id: string;
  ref: string;
  name: string;
  bytes: number;
  created_at: string | null;
  source_label?: string | null;
  is_missing_on_disk?: boolean;
  exports?: VaultFileInfo[];
};

const apiMocks = vi.hoisted(() => ({
  apiFetchBlob: vi.fn(),
}));

const vaultMocks = vi.hoisted(() => ({
  refs: null as null | {
    state: { value: string };
    sort: { value: string };
    search: { value: string };
    files: { value: VaultFileInfo[] };
    usage: { value: null };
    canLoadMore: { value: boolean };
    isLoading: { value: boolean };
    errorMessage: { value: string | null };
    refresh: ReturnType<typeof vi.fn>;
    loadMore: ReturnType<typeof vi.fn>;
    deleteFile: ReturnType<typeof vi.fn>;
    restoreFile: ReturnType<typeof vi.fn>;
  },
}));

vi.mock("../../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/client")>();
  return {
    ...actual,
    apiFetchBlob: apiMocks.apiFetchBlob,
  };
});

vi.mock("../../composables/vault/useVaultFiles", async () => {
  const { computed, ref } = await import("vue");
  const refs = {
    state: ref("active"),
    sort: ref("newest"),
    search: ref(""),
    files: ref([] as VaultFileInfo[]),
    usage: ref(null as null),
    canLoadMore: computed(() => false),
    isLoading: ref(false),
    errorMessage: ref<string | null>(null),
    refresh: vi.fn().mockResolvedValue(undefined),
    loadMore: vi.fn().mockResolvedValue(undefined),
    deleteFile: vi.fn().mockResolvedValue(undefined),
    restoreFile: vi.fn().mockResolvedValue(undefined),
  };
  vaultMocks.refs = refs;
  return {
    useVaultFiles: () => refs,
  };
});

vi.mock("../../stores/auth", () => ({
  useAuthStore: () => ({
    bootstrapped: true,
    isAuthenticated: true,
  }),
}));

vi.mock("../../stores/toast", () => ({
  useToastStore: () => ({
    success: vi.fn(),
    failure: vi.fn(),
  }),
}));

function examFile(): VaultFileInfo {
  return {
    id: "file-exam",
    ref: "vault:file-exam",
    name: "Prov v.42",
    bytes: 2048,
    created_at: "2026-03-29T12:00:00Z",
    source_label: "Examination",
    is_missing_on_disk: false,
  };
}

function savedExport(id: string, name: string): VaultFileInfo {
  return {
    id,
    ref: `vault:${id}`,
    name,
    bytes: 512,
    created_at: "2026-03-29T12:05:00Z",
    source_label: null,
    is_missing_on_disk: false,
    exports: [],
  };
}

function mountPanel(mode: "manage" | "picker") {
  return mount(VaultPanel, {
    props: { mode },
    global: {
      stubs: {
        UiSearchBar: {
          template: "<div data-test='vault-search-stub' />",
        },
      },
    },
  });
}

describe("VaultPanel saved exports", () => {
  beforeEach(() => {
    if (!vaultMocks.refs) {
      throw new Error("Vault refs were not initialized.");
    }
    vaultMocks.refs.state.value = "active";
    vaultMocks.refs.sort.value = "newest";
    vaultMocks.refs.search.value = "";
    vaultMocks.refs.files.value = [];
    vaultMocks.refs.usage.value = null;
    vaultMocks.refs.isLoading.value = false;
    vaultMocks.refs.errorMessage.value = null;
    vaultMocks.refs.refresh.mockClear();
    vaultMocks.refs.deleteFile.mockClear();
    vaultMocks.refs.restoreFile.mockClear();
    vi.restoreAllMocks();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      writable: true,
      value: vi.fn(() => "blob:mock-url"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      writable: true,
      value: vi.fn(),
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    apiMocks.apiFetchBlob.mockReset();
    apiMocks.apiFetchBlob.mockResolvedValue(new Blob(["x"]));
  });

  it("lists each saved export of an exam under that exam", () => {
    if (!vaultMocks.refs) throw new Error("Vault refs were not initialized.");
    const exam = examFile();
    exam.exports = [
      savedExport("export-qti", "Prov v.42-qti.zip"),
      savedExport("export-pdf", "Prov v.42-examnet.pdf"),
    ];
    vaultMocks.refs.files.value = [exam];

    const wrapper = mountPanel("manage");

    const exportsList = wrapper.find('[aria-label="Sparade exporter"]');
    expect(exportsList.exists()).toBe(true);
    expect(exportsList.text()).toContain("Prov v.42-qti.zip");
    expect(exportsList.text()).toContain("Prov v.42-examnet.pdf");
    expect(exportsList.text()).toContain("Ladda ned");
  });

  it("downloads the clicked saved export and not the exam file", async () => {
    if (!vaultMocks.refs) throw new Error("Vault refs were not initialized.");
    const exam = examFile();
    exam.exports = [
      savedExport("export-qti", "Prov v.42-qti.zip"),
      savedExport("export-pdf", "Prov v.42-examnet.pdf"),
    ];
    vaultMocks.refs.files.value = [exam];

    const wrapper = mountPanel("manage");
    await wrapper
      .find('button[aria-label="Ladda ned Prov v.42-examnet.pdf"]')
      .trigger("click");

    expect(apiMocks.apiFetchBlob).toHaveBeenCalledWith(
      "/api/v1/vault/files/export-pdf/download",
    );
  });

  it("keeps the exam file's own actions and shows no export list without saved exports", async () => {
    if (!vaultMocks.refs) throw new Error("Vault refs were not initialized.");
    vaultMocks.refs.files.value = [examFile()];

    const wrapper = mountPanel("manage");

    expect(wrapper.find('[aria-label="Sparade exporter"]').exists()).toBe(false);

    await wrapper.find('button[aria-label="Filåtgärder för Prov v.42"]').trigger("click");
    const menu = wrapper.find('[role="menu"]');
    expect(menu.exists()).toBe(true);
    expect(menu.text()).toContain("Ladda ned");
    expect(menu.text()).toContain("Ta bort");
  });

  it.each(["manage", "picker"] as const)("names each file menu in %s mode and opens the matching row", async (mode) => {
    if (!vaultMocks.refs) throw new Error("Vault refs were not initialized.");
    const first = examFile();
    const second = savedExport("file-second", 'Svenska & engelska "omprov".docx');
    first.exports = [savedExport("export-qti", "Prov v.42-qti.zip")];
    vaultMocks.refs.files.value = [first, second];

    const wrapper = mountPanel(mode);

    for (const file of [first, second]) {
      const name = `Filåtgärder för ${file.name}`;
      const trigger = wrapper.findAll("button").find((button) => button.attributes("aria-label") === name);
      expect(trigger, `Menu trigger for ${file.name}`).toBeDefined();
      await trigger!.trigger("click");

      const menu = wrapper.get('[role="menu"]');
      expect(menu.attributes("aria-label")).toBe(name);
      expect(trigger!.attributes("aria-controls")).toBe(menu.attributes("id"));
      expect(trigger!.attributes("aria-expanded")).toBe("true");
      await menu.findAll('[role="menuitem"]')[0]!.trigger("click");
      expect(apiMocks.apiFetchBlob).toHaveBeenLastCalledWith(`/api/v1/vault/files/${file.id}/download`);
    }

    if (mode === "manage") {
      await wrapper.get('button[aria-label="Ladda ned Prov v.42-qti.zip"]').trigger("click");
      expect(apiMocks.apiFetchBlob).toHaveBeenLastCalledWith("/api/v1/vault/files/export-qti/download");
    }
  });

  it("does not select the exam file when a saved export row is used", async () => {
    if (!vaultMocks.refs) throw new Error("Vault refs were not initialized.");
    const exam = examFile();
    exam.exports = [savedExport("export-qti", "Prov v.42-qti.zip")];
    vaultMocks.refs.files.value = [exam];

    const wrapper = mountPanel("manage");
    await wrapper.find('[aria-label="Sparade exporter"] li').trigger("click");

    const checkbox = wrapper.find<HTMLInputElement>('input[id="vault-file-select-file-exam"]');
    expect(checkbox.element.checked).toBe(false);
  });

  it("does not offer a saved export as a selectable file in the picker", () => {
    if (!vaultMocks.refs) throw new Error("Vault refs were not initialized.");
    const exam = examFile();
    exam.exports = [savedExport("export-qti", "Prov v.42-qti.zip")];
    vaultMocks.refs.files.value = [exam];

    const wrapper = mountPanel("picker");

    expect(wrapper.find('[aria-label="Sparade exporter"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Prov v.42-qti.zip");
    expect(wrapper.text()).toContain("Prov v.42");
  });
});
