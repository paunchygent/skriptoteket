import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick, ref } from "vue";

import { useHelp } from "../useHelp";
import TutorialFirstUseGate from "./TutorialFirstUseGate.vue";
import { loadTutorialClipManifest, resetTutorialClipManifestCacheForTests } from "./tutorialClipManifest";
import { DESKTOP_VIEWPORT_KEY } from "./useDesktopViewport";
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

const help = useHelp();
let wrapper: VueWrapper | null = null;
let resolveFetch: ((response: Response) => void) | null = null;

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
) {
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
  const isDesktop = ref(options.desktop ?? true);
  wrapper = mount(TutorialFirstUseGate, {
    props: { hostMode: "public", blocked: options.blocked ?? false },
    attachTo: document.body,
    global: { provide: { [DESKTOP_VIEWPORT_KEY as symbol]: isDesktop } },
  });
  if (!options.deferManifest) {
    await loadTutorialClipManifest();
  }
  return { isDesktop };
}

beforeEach(() => {
  vi.useFakeTimers();
  window.localStorage.clear();
  help.setHelpContext(null);
  help.close({ restoreFocus: false });
});

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  resolveFetch = null;
  help.setHelpContext(null);
  help.close({ restoreFocus: false });
  resetTutorialClipManifestCacheForTests();
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
    await loadTutorialClipManifest();
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
    wrapper = mount(TutorialFirstUseGate, {
      props: { hostMode: "public", blocked: false },
      attachTo: document.body,
      global: { provide: { [DESKTOP_VIEWPORT_KEY as symbol]: ref(true) } },
    });
    await loadTutorialClipManifest();
    help.setHelpContext("planner_overview");
    await settle();

    expect(dialog()).toBeNull();
  });
});
