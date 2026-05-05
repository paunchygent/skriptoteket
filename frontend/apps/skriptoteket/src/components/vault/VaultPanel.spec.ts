import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import VaultPanel from "./VaultPanel.vue";

const vaultMocks = vi.hoisted(() => ({
  refs: null as null | {
    state: { value: string };
    sort: { value: string };
    search: { value: string };
    files: {
      value: Array<{
        id: string;
        ref: string;
        name: string;
        bytes: number;
        created_at: string | null;
        source_label?: string | null;
        is_missing_on_disk?: boolean;
      }>;
    };
    usage: {
      value: null | {
        bytes_total: number;
        max_total_bytes: number;
        max_file_bytes: number;
      };
    };
    canLoadMore: { value: boolean };
    isLoading: { value: boolean };
    errorMessage: { value: string | null };
    refresh: ReturnType<typeof vi.fn>;
    loadMore: ReturnType<typeof vi.fn>;
    deleteFile: ReturnType<typeof vi.fn>;
    restoreFile: ReturnType<typeof vi.fn>;
  },
}));

vi.mock("../../composables/vault/useVaultFiles", async () => {
  const { computed, ref } = await import("vue");
  const refs = {
    state: ref("active"),
    sort: ref("newest"),
    search: ref(""),
    files: ref([] as Array<{ id: string; ref: string; name: string; bytes: number; created_at: string | null; source_label?: string | null; is_missing_on_disk?: boolean }>),
    usage: ref(null as null | {
      bytes_total: number;
      max_total_bytes: number;
      max_file_bytes: number;
    }),
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

describe("VaultPanel", () => {
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
    vaultMocks.refs.loadMore.mockClear();
    vaultMocks.refs.deleteFile.mockClear();
    vaultMocks.refs.restoreFile.mockClear();
  });

  it("keeps rendered files visible while a refresh is in progress", () => {
    if (!vaultMocks.refs) {
      throw new Error("Vault refs were not initialized.");
    }
    vaultMocks.refs.files.value = [
      {
        id: "file-1",
        ref: "vault:file-1",
        name: "lektion.pdf",
        bytes: 128,
        created_at: "2026-03-29T12:00:00Z",
        source_label: "Uppladdad",
        is_missing_on_disk: false,
      },
    ];
    vaultMocks.refs.isLoading.value = true;

    const wrapper = mount(VaultPanel, {
      props: {
        mode: "manage",
      },
      global: {
        stubs: {
          UiSearchBar: {
            template: "<div data-test='vault-search-stub' />",
          },
        },
      },
    });

    expect(wrapper.text()).not.toContain("Laddar Mina filer…");
    expect(wrapper.text()).toContain("lektion.pdf");
    expect(wrapper.find('[aria-busy="true"]').exists()).toBe(true);
  });
});
