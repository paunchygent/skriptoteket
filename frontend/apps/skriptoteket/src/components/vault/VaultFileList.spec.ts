import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { components } from "../../api/openapi";
import VaultFileList from "./VaultFileList.vue";

type VaultFile = components["schemas"]["VaultFileInfo"];
const files: VaultFile[] = [
  { id: "one", ref: "vault:one", name: "lektion.pdf", bytes: 128, created_at: "2026-10-17T10:00:00Z", is_missing_on_disk: false },
  { id: "two", ref: "vault:two", name: "facit.pdf", bytes: 256, created_at: "2026-10-17T10:00:00Z", is_missing_on_disk: true },
];
const defaults = {
  mode: "manage" as const, state: "active" as const, files,
  selectedRefs: [], selectedManageIds: [], isReadOnly: false, isMutating: false,
  openMenuForFileId: null, isRefreshingResults: false, canLoadMore: false, isLoading: false,
};

describe("VaultFileList actions", () => {
  it("names each menu trigger by its own file and opens only the requested file menu", async () => {
    const wrapper = mount(VaultFileList, { props: defaults });
    const first = wrapper.get('[aria-label="Filåtgärder för lektion.pdf"]');
    const second = wrapper.get('[aria-label="Filåtgärder för facit.pdf"]');
    expect(first.attributes("aria-expanded")).toBe("false");
    await second.trigger("click");
    expect(wrapper.emitted("toggle-menu")).toEqual([["two"]]);
    await wrapper.setProps({ openMenuForFileId: "two" });
    const menu = wrapper.get('[role="menu"]');
    expect(menu.attributes("id")).toBe(second.attributes("aria-controls"));
    expect(menu.attributes("aria-label")).toBe("Filåtgärder för facit.pdf");
    expect(wrapper.get('[aria-controls="vault-file-actions-two"]').attributes("aria-expanded")).toBe("true");
    expect(wrapper.get('[aria-controls="vault-file-actions-one"]').attributes("aria-expanded")).toBe("false");
    wrapper.unmount();
  });

  it("blocks missing-file download but still allows deletion, and blocks every action during mutation", async () => {
    const wrapper = mount(VaultFileList, { props: { ...defaults, openMenuForFileId: "two" } });
    const actions = wrapper.findAll('[role="menuitem"]');
    expect((actions[0]!.element as HTMLButtonElement).disabled).toBe(true);
    await actions[0]!.trigger("click");
    expect(wrapper.emitted("download")).toBeUndefined();
    await actions[1]!.trigger("click");
    expect(wrapper.emitted("delete")).toEqual([["two"]]);
    await wrapper.setProps({ isMutating: true });
    expect(wrapper.findAll("button").every(button => (button.element as HTMLButtonElement).disabled)).toBe(true);
    wrapper.unmount();
  });

  it("restores a trashed file without deleting it and blocks duplicate pagination while loading", async () => {
    const wrapper = mount(VaultFileList, { props: { ...defaults, state: "trash", openMenuForFileId: "one", canLoadMore: true } });
    const restore = wrapper.findAll('[role="menuitem"]').find(button => button.text() === "Återställ")!;
    await restore.trigger("click");
    expect(wrapper.emitted("restore")).toEqual([["one"]]);
    expect(wrapper.emitted("delete")).toBeUndefined();
    expect(wrapper.emitted("close-menu")).toHaveLength(1);
    const more = wrapper.findAll("button").find(button => button.text() === "Ladda fler")!;
    await more.trigger("click");
    expect(wrapper.emitted("load-more")).toHaveLength(1);
    await wrapper.setProps({ isLoading: true });
    expect((more.element as HTMLButtonElement).disabled).toBe(true);
    await more.trigger("click");
    expect(wrapper.emitted("load-more")).toHaveLength(1);
    wrapper.unmount();
  });

  it("keeps picker selection checked, prevents missing or trashed selection, and exposes no read-only actions", async () => {
    const wrapper = mount(VaultFileList, { props: { ...defaults, mode: "picker", selectedRefs: ["vault:one"] } });
    const first = wrapper.get<HTMLInputElement>('[aria-label="lektion.pdf"]');
    const missing = wrapper.get<HTMLInputElement>('[aria-label="facit.pdf"]');
    expect(first.element.checked).toBe(true);
    expect(missing.element.disabled).toBe(true);
    await first.setValue(false);
    expect(wrapper.emitted("toggle-selected")).toEqual([["vault:one", false]]);
    await wrapper.setProps({ state: "trash" });
    expect(first.element.disabled).toBe(true);
    await wrapper.setProps({ state: "active", isReadOnly: true, openMenuForFileId: "one" });
    expect(first.element.disabled).toBe(true);
    expect(wrapper.find('[role="menu"]').exists()).toBe(false);
    expect(wrapper.find("button").exists()).toBe(false);
    wrapper.unmount();
  });
});
