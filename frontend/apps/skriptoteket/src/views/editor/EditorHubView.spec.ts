import { flushPromises, shallowMount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import EditorHubView from "./EditorHubView.vue";

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  replace: vi.fn(),
  push: vi.fn(),
  bootstrap: vi.fn(),
  hasAtLeastRole: vi.fn(),
  ensureLoaded: vi.fn(),
  query: {} as Record<string, string>,
}));

vi.mock("vue-router", () => ({
  useRoute: () => ({ query: mocks.query }),
  useRouter: () => ({ replace: mocks.replace, push: mocks.push }),
  RouterLink: { template: "<a><slot /></a>" },
}));
vi.mock("../../api/client", () => ({
  apiGet: mocks.apiGet,
  isApiError: (error: unknown) => typeof error === "object" && error !== null && "status" in error,
}));
vi.mock("../../stores/auth", () => ({
  useAuthStore: () => ({
    user: { id: "user-1" },
    bootstrap: mocks.bootstrap,
    hasAtLeastRole: mocks.hasAtLeastRole,
  }),
}));
vi.mock("../../composables/admin/useAdminToolsIndex", () => ({
  useAdminToolsIndex: () => ({
    tools: ref([{ id: "admin-only", title: "Adminverktyg", slug: "admin-slug" }]),
    isLoading: ref(false),
    error: ref(null),
    ensureLoaded: mocks.ensureLoaded,
  }),
}));
vi.mock("../../composables/admin/useCreateDraftToolModal", () => ({
  useCreateDraftToolModal: () => ({
    isOpen: ref(false), title: ref(""), summary: ref(""), error: ref(null),
    isSubmitting: ref(false), open: vi.fn(), close: vi.fn(), submit: vi.fn(),
  }),
}));

const tools = [
  { id: "a", title: "Algebra", slug: "ekvationer", is_published: false },
  { id: "z", title: "Zebra", slug: "djur", is_published: true },
  { id: "o", title: "Övningar", slug: "ovningar", is_published: false },
  { id: "b", title: "Biologi", slug: "celler", is_published: true },
];
const recentsKey = "skriptoteket.editor.recents.v1:user-1";
let wrapper: VueWrapper | undefined;

function setRecents(): void {
  localStorage.setItem(recentsKey, JSON.stringify([
    { toolId: "z", title: "Zebra", slug: "djur", openedAt: 10 },
    { toolId: "b", title: "Biologi", slug: "celler", openedAt: 20 },
  ]));
}

async function mountHub(): Promise<VueWrapper> {
  wrapper = shallowMount(EditorHubView);
  await flushPromises();
  return wrapper;
}

async function search(query: string): Promise<string[]> {
  const input = wrapper!.get('[data-testid="editor-hub-search-input"]');
  await input.trigger("focus");
  await input.setValue(query);
  await flushPromises();
  return wrapper!.findAll("button").filter((button) => button.text().includes("ekvationer")
    || button.text().includes("djur") || button.text().includes("admin-slug"))
    .map((button) => button.findAll("div > div").map((part) => part.text()).join(" "));
}

describe("EditorHubView tool discovery", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mocks.query = { pick: "1" };
    mocks.hasAtLeastRole.mockReturnValue(false);
    mocks.apiGet.mockImplementation((path: string) => path === "/api/v1/my-tools"
      ? Promise.resolve({ tools }) : Promise.resolve({}));
  });

  afterEach(() => wrapper?.unmount());

  it("sorts recent tools newest first, then remaining tools by Swedish title", async () => {
    setRecents();
    const view = await mountHub();
    const items = view.get('[data-testid="editor-hub-my-tools-list"]').findAll("li");
    expect(items.map((item) => item.get("button > div").text())).toEqual([
      "Biologi", "Zebra", "Algebra", "Övningar",
    ]);
  });

  it("filters contributors' tools by normalized title and slug and opens the selected result", async () => {
    await mountHub();
    expect(await search("  ALGEBRA  ")).toEqual(["Algebra ekvationer"]);
    expect(await search("EKVATIONER")).toEqual(["Algebra ekvationer"]);
    await wrapper!.findAll("button").find((button) => button.text() === "Algebraekvationer")!.trigger("click");
    expect(mocks.push).toHaveBeenCalledWith("/admin/tools/a");
    expect((wrapper!.get("input").element as HTMLInputElement).value).toBe("");
    expect(await search("admin-slug")).toEqual([]);
  });

  it("searches the admin index for admins", async () => {
    mocks.hasAtLeastRole.mockReturnValue(true);
    await mountHub();
    expect(await search("admin-slug")).toEqual(["Adminverktyg admin-slug"]);
    expect(mocks.ensureLoaded).toHaveBeenCalledOnce();
    expect(await search("ekvationer")).toEqual([]);
  });

  it("verifies and redirects to the most recent tool without loading my tools", async () => {
    mocks.query = {};
    setRecents();
    await mountHub();
    expect(mocks.apiGet).toHaveBeenCalledExactlyOnceWith("/api/v1/editor/tools/b");
    expect(mocks.replace).toHaveBeenCalledExactlyOnceWith("/admin/tools/b");
  });

  it("pick=1 skips the recent-tool redirect and loads the picker", async () => {
    setRecents();
    await mountHub();
    expect(mocks.replace).not.toHaveBeenCalled();
    expect(mocks.apiGet).toHaveBeenCalledExactlyOnceWith("/api/v1/my-tools");
  });

  it("loads the picker when there are no recent tools", async () => {
    mocks.query = {};
    await mountHub();
    expect(mocks.replace).not.toHaveBeenCalled();
    expect(mocks.apiGet).toHaveBeenCalledExactlyOnceWith("/api/v1/my-tools");
  });

  it.each([403, 404])("removes an inaccessible recent tool on %s and loads the picker", async (status) => {
    mocks.query = {};
    setRecents();
    mocks.apiGet.mockRejectedValueOnce({ status, message: "Unavailable" });
    await mountHub();
    expect(mocks.replace).not.toHaveBeenCalled();
    expect(mocks.apiGet).toHaveBeenLastCalledWith("/api/v1/my-tools");
    expect(JSON.parse(localStorage.getItem(recentsKey)!)).toEqual([
      { toolId: "z", title: "Zebra", slug: "djur", openedAt: 10 },
    ]);
    expect(wrapper!.get('[data-testid="editor-hub-recent-tools-list"]').text()).not.toContain("Biologi");
  });

  it("keeps the recent entry after a transient redirect failure and loads the picker", async () => {
    mocks.query = {};
    setRecents();
    mocks.apiGet.mockRejectedValueOnce(new Error("Offline"));
    await mountHub();
    expect(mocks.replace).not.toHaveBeenCalled();
    expect(mocks.apiGet).toHaveBeenLastCalledWith("/api/v1/my-tools");
    expect(JSON.parse(localStorage.getItem(recentsKey)!)).toHaveLength(2);
  });
});
