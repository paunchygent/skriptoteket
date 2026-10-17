import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import PlannerShareLinksPanel from "../../../views/apps/components/PlannerShareLinksPanel.vue";
import { GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY } from "./useTutorialSeenSections";

const manifest = {
  schema_version: 1,
  app: "classroom.group-seating-studio",
  clips: [
    {
      id: "klass",
      section: "planner_overview",
      order: 1,
      title: "Klass",
      duration_seconds: 8,
      video: "klass.mp4",
      poster: "klass.jpg",
    },
    {
      id: "regler",
      section: "planner_rules",
      order: 1,
      title: "Regler",
      duration_seconds: 30,
      video: "regler.mp4",
      poster: "regler.jpg",
    },
  ],
};

const DESKTOP_VIEWPORT_QUERY = "(min-width: 1024px)";

type GateModules = {
  TutorialFirstUseGate: typeof import("./TutorialFirstUseGate.vue").default;
  help: ReturnType<typeof import("../useHelp").useHelp>;
  loadTutorialClipManifest: typeof import("./useTutorialClipManifest").loadTutorialClipManifest;
};

let modules: GateModules;
let help: GateModules["help"];
let wrapper: VueWrapper | null = null;
let resolveFetch: ((response: Response) => void) | null = null;

type ViewportStub = { setDesktop: (desktop: boolean) => void };

/** Stubs `window.matchMedia`; only the desktop query follows the given width. */
function stubViewport(desktop: boolean): ViewportStub {
  let isDesktop = desktop;
  const listeners = new Set<() => void>();
  vi.stubGlobal("matchMedia", (query: string) => ({
    media: query,
    get matches() {
      return query === DESKTOP_VIEWPORT_QUERY && isDesktop;
    },
    onchange: null,
    addEventListener: (_type: string, listener: () => void) => listeners.add(listener),
    removeEventListener: (_type: string, listener: () => void) => listeners.delete(listener),
    addListener: (listener: () => void) => listeners.add(listener),
    removeListener: (listener: () => void) => listeners.delete(listener),
    dispatchEvent: () => true,
  }));
  return {
    setDesktop: (next) => {
      isDesktop = next;
      listeners.forEach((listener) => listener());
    },
  };
}

function dialog(): Element | null {
  return document.body.querySelector("[data-test='tutorial-clip-dialog']");
}

function seenInBrowser(): unknown {
  return JSON.parse(window.localStorage.getItem(GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY) ?? "[]");
}

async function settle(ms = 500): Promise<void> {
  await vi.advanceTimersByTimeAsync(ms);
  await nextTick();
}

async function mountGate(
  options: { desktop?: boolean; blocked?: boolean; deferManifest?: boolean } = {},
): Promise<ViewportStub> {
  if (options.deferManifest) {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise<Response>((resolve) => {
            resolveFetch = resolve;
          }),
      ),
    );
  } else {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(manifest)));
  }
  const viewport = stubViewport(options.desktop ?? true);
  wrapper = mount(modules.TutorialFirstUseGate, {
    props: { hostMode: "public", blocked: options.blocked ?? false },
    attachTo: document.body,
  });
  if (!options.deferManifest) {
    await modules.loadTutorialClipManifest();
  }
  return viewport;
}

beforeEach(async () => {
  // The manifest cache and the help refs are module state for one app load;
  // every test gets a fresh module graph so they start empty.
  vi.resetModules();
  const [gateModule, helpModule, manifestModule] = await Promise.all([
    import("./TutorialFirstUseGate.vue"),
    import("../useHelp"),
    import("./useTutorialClipManifest"),
  ]);
  modules = {
    TutorialFirstUseGate: gateModule.default,
    help: helpModule.useHelp(),
    loadTutorialClipManifest: manifestModule.loadTutorialClipManifest,
  };
  help = modules.help;
  vi.useFakeTimers();
  window.localStorage.clear();
});

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  resolveFetch = null;
  vi.unstubAllGlobals();
  vi.useRealTimers();
  document.body.innerHTML = "";
});

describe("tutorial first-use gate", () => {
  it("opens the section's dialog 500 ms after the planner context is set", async () => {
    await mountGate();
    help.setHelpContext("planner_overview");

    await settle(499);
    expect(dialog()).toBeNull();
    await settle(1);

    expect(dialog()).not.toBeNull();
    expect(document.body.querySelector("[data-test='tutorial-clip-dialog-title']")?.textContent?.trim())
      .toBe("Klass");
  });

  it("waits for a slow manifest instead of dropping the section", async () => {
    help.setHelpContext("planner_overview");
    await mountGate({ deferManifest: true });
    await settle(2000);
    expect(dialog()).toBeNull();

    resolveFetch?.(Response.json(manifest));
    await modules.loadTutorialClipManifest();
    await settle();

    expect(dialog()).not.toBeNull();
  });

  it("closing marks the section seen and it never opens again", async () => {
    await mountGate();
    help.setHelpContext("planner_overview");
    await settle();

    document.body.querySelector<HTMLButtonElement>("[data-test='tutorial-clip-dialog-close']")?.click();
    await nextTick();

    expect(dialog()).toBeNull();
    expect(seenInBrowser()).toEqual(["planner_overview"]);

    help.setHelpContext("planner_grouping");
    await nextTick();
    help.setHelpContext("planner_overview");
    await settle();
    expect(dialog()).toBeNull();
  });

  it("does not open while the open Delade länkar panel is present", async () => {
    stubViewport(true);
    const share = mount(PlannerShareLinksPanel, { attachTo: document.body });
    await share.find("[data-test='planner-share-links-trigger']").trigger("click");
    await nextTick();
    const panel = document.body.querySelector("[data-test='planner-share-links-panel']");
    expect(panel?.getAttribute("role")).toBe("dialog");
    expect(panel?.getAttribute("aria-modal")).toBe("true");

    await mountGate();
    help.setHelpContext("planner_overview");
    await settle(2000);

    expect(dialog()).toBeNull();
    expect(window.localStorage.getItem(GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY)).toBeNull();
    share.unmount();
  });

  it("follows the desktop media query when the window widens within the delay", async () => {
    const viewport = await mountGate({ desktop: false });
    help.setHelpContext("planner_overview");
    await settle(200);
    viewport.setDesktop(true);
    await settle(300);

    expect(dialog()).not.toBeNull();
  });

  it("does not open below 1024 px and marks nothing seen", async () => {
    await mountGate({ desktop: false });
    help.setHelpContext("planner_overview");
    await settle(2000);

    expect(dialog()).toBeNull();
    expect(window.localStorage.getItem(GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY)).toBeNull();
  });

  it("waits while the guest-upgrade gate blocks and opens once it allows", async () => {
    await mountGate({ blocked: true });
    help.setHelpContext("planner_overview");
    await settle(2000);
    expect(dialog()).toBeNull();

    await wrapper?.setProps({ blocked: false });
    await settle();

    expect(dialog()).not.toBeNull();
  });

  it("skips while the Hjälp panel is open and retries only on the next context change", async () => {
    await mountGate();
    help.open();
    help.setHelpContext("planner_overview");
    await settle();
    expect(dialog()).toBeNull();

    help.close({ restoreFocus: false });
    await settle(5000);
    expect(dialog()).toBeNull();

    help.setHelpContext("planner_grouping");
    await nextTick();
    help.setHelpContext("planner_overview");
    await settle();
    expect(dialog()).not.toBeNull();
  });

  it.each([
    ["a modal planner dialog", (el: HTMLElement) => {
      el.setAttribute("role", "dialog");
      el.setAttribute("aria-modal", "true");
    }],
    ["a nonmodal dialog", (el: HTMLElement) => {
      el.setAttribute("role", "dialog");
    }],
    ["a planner overlay backdrop", (el: HTMLElement) => {
      el.className = "planner-overlay-backdrop";
    }],
  ])("skips while %s is present and does not retry by timer", async (_label, decorate) => {
    await mountGate();
    const foreign = document.createElement("div");
    decorate(foreign);
    document.body.appendChild(foreign);

    help.setHelpContext("planner_overview");
    await settle();
    expect(dialog()).toBeNull();

    foreign.remove();
    await settle(5000);
    expect(dialog()).toBeNull();

    help.setHelpContext("planner_rules");
    await settle();
    expect(document.body.querySelector("[data-test='tutorial-clip-dialog-title']")?.textContent?.trim())
      .toBe("Regler");
  });

  it("does not open a section that is already seen", async () => {
    window.localStorage.setItem(
      GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY,
      JSON.stringify(["planner_overview"]),
    );
    await mountGate();
    help.setHelpContext("planner_overview");
    await settle();

    expect(dialog()).toBeNull();
  });

  it("does not open a section without clips", async () => {
    await mountGate();
    help.setHelpContext("planner_seating");
    await settle();

    expect(dialog()).toBeNull();
  });

  it("does not open when the teacher leaves the section within the delay", async () => {
    await mountGate();
    help.setHelpContext("planner_overview");
    await settle(200);
    help.setHelpContext(null);
    await settle(1000);

    expect(dialog()).toBeNull();
  });

  it("does not open when the manifest is missing", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 404 })));
    stubViewport(true);
    wrapper = mount(modules.TutorialFirstUseGate, {
      props: { hostMode: "public", blocked: false },
      attachTo: document.body,
    });
    await modules.loadTutorialClipManifest();
    help.setHelpContext("planner_overview");
    await settle();

    expect(dialog()).toBeNull();
  });
});
