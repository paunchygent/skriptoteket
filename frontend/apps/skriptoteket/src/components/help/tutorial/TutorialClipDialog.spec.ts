import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import type { TutorialClip } from "../../../api/tutorialClips";
import TutorialClipDialog from "./TutorialClipDialog.vue";

const clips: TutorialClip[] = [
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
    id: "klassrum",
    section: "planner_overview",
    order: 2,
    title: "Klassrum",
    duration_seconds: 65,
    video: "klassrum.mp4",
    poster: "klassrum.jpg",
  },
];

let wrapper: VueWrapper | null = null;

function query<T extends Element = HTMLElement>(selector: string): T | null {
  return document.body.querySelector<T>(selector);
}

async function mountDialog(props: Partial<{ open: boolean; initialClipId: string | null }> = {}) {
  const opener = document.createElement("button");
  document.body.appendChild(opener);
  opener.focus();
  wrapper = mount(TutorialClipDialog, {
    props: { clips, initialClipId: null, open: true, ...props },
    attachTo: document.body,
  });
  await nextTick();
  await nextTick();
  return { opener };
}

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  document.body.innerHTML = "";
});

describe("TutorialClipDialog", () => {
  it("renders a labelled modal with poster, no preload and no autoplay", async () => {
    await mountDialog();

    const dialog = query("[role='dialog'][aria-modal='true']");
    const labelledBy = dialog?.getAttribute("aria-labelledby") ?? "";
    expect(document.getElementById(labelledBy)?.textContent?.trim()).toBe("Klass");

    const video = query<HTMLVideoElement>("[data-test='tutorial-clip-video']");
    expect(video?.getAttribute("poster")).toBe("/static/media/klassrumskartan/klass.jpg");
    expect(video?.getAttribute("src")).toBe("/static/media/klassrumskartan/klass.mp4");
    expect(video?.getAttribute("preload")).toBe("none");
    expect(video?.hasAttribute("autoplay")).toBe(false);
    expect(video?.hasAttribute("controls")).toBe(true);
    expect(query("[data-test='tutorial-clip-play']")).not.toBeNull();
  });

  it("moves focus into the dialog and restores it on close", async () => {
    const { opener } = await mountDialog();
    expect(document.activeElement).toBe(query("[data-test='tutorial-clip-play']"));

    await wrapper?.setProps({ open: false });
    await nextTick();

    expect(document.activeElement).toBe(opener);
  });

  it("starts playback only when the play control is pressed", async () => {
    const play = vi
      .spyOn(HTMLMediaElement.prototype, "play")
      .mockImplementation(() => Promise.resolve());
    await mountDialog();
    expect(play).not.toHaveBeenCalled();

    query<HTMLButtonElement>("[data-test='tutorial-clip-play']")?.click();
    await nextTick();

    expect(play).toHaveBeenCalledTimes(1);
    expect(query("[data-test='tutorial-clip-play']")).toBeNull();
    play.mockRestore();
  });

  it("shows the load-error line on a video error while the poster stays", async () => {
    await mountDialog();
    const video = query<HTMLVideoElement>("[data-test='tutorial-clip-video']");

    video?.dispatchEvent(new Event("error"));
    await nextTick();

    const error = query("[data-test='tutorial-clip-error']");
    expect(error?.getAttribute("role")).toBe("alert");
    expect(error?.textContent?.trim()).toBe("Klippet kunde inte laddas just nu.");
    expect(video?.getAttribute("poster")).toBe("/static/media/klassrumskartan/klass.jpg");
  });

  it("closes on Escape without letting the event reach other document listeners", async () => {
    const helpListener = vi.fn();
    document.addEventListener("keydown", helpListener);
    await mountDialog();

    document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));

    expect(wrapper?.emitted("close")).toHaveLength(1);
    expect(helpListener).not.toHaveBeenCalled();
    document.removeEventListener("keydown", helpListener);
  });

  it("closes from the backdrop and the close button", async () => {
    await mountDialog();

    query<HTMLButtonElement>("[data-test='tutorial-clip-dialog-backdrop']")?.click();
    query<HTMLButtonElement>("[data-test='tutorial-clip-dialog-close']")?.click();

    expect(wrapper?.emitted("close")).toHaveLength(2);
  });

  it("lists the section's clips with durations and switches the player", async () => {
    await mountDialog({ initialClipId: "klassrum" });

    const items = Array.from(
      document.body.querySelectorAll<HTMLButtonElement>("[data-test='tutorial-clip-list-item']"),
    );
    expect(
      items.map((item) =>
        Array.from(item.querySelectorAll("span")).map((span) => span.textContent?.trim()),
      ),
    ).toEqual([
      ["Klass", "0:08"],
      ["Klassrum", "1:05"],
    ]);
    expect(items[1]?.getAttribute("aria-current")).toBe("true");

    items[0]?.click();
    await nextTick();

    expect(
      query<HTMLVideoElement>("[data-test='tutorial-clip-video']")?.getAttribute("src"),
    ).toBe("/static/media/klassrumskartan/klass.mp4");
    expect(query("[data-test='tutorial-clip-dialog-title']")?.textContent?.trim()).toBe("Klass");
  });

  it("wraps Tab at both ends of the modal without focusing the backdrop", async () => {
    const { opener } = await mountDialog();
    const close = query<HTMLButtonElement>('[data-test="tutorial-clip-dialog-close"]');
    const items = document.body.querySelectorAll<HTMLButtonElement>(
      '[data-test="tutorial-clip-list-item"]',
    );
    const last = items[items.length - 1];
    expect(close).not.toBeNull();
    expect(last).toBeDefined();

    last?.focus();
    document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));
    expect(document.activeElement).toBe(close);
    close?.focus();
    document.body.dispatchEvent(new KeyboardEvent("keydown", {
      key: "Tab", shiftKey: true, bubbles: true,
    }));
    expect(document.activeElement).toBe(last);

    opener.focus();
    document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));
    expect(document.activeElement).toBe(close);
  });

  it("clears a failed clip when another clip is selected without starting playback", async () => {
    const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
    try {
      await mountDialog();
      query<HTMLVideoElement>('[data-test="tutorial-clip-video"]')?.dispatchEvent(new Event("error"));
      await nextTick();
      expect(query('[data-test="tutorial-clip-error"]')).not.toBeNull();
      expect(query('[data-test="tutorial-clip-play"]')).toBeNull();

      document.body.querySelectorAll<HTMLButtonElement>(
        '[data-test="tutorial-clip-list-item"]',
      )[1]?.click();
      await nextTick();

      expect(query('[data-test="tutorial-clip-error"]')).toBeNull();
      expect(query('[data-test="tutorial-clip-play"]')?.getAttribute("aria-label")).toContain("Klassrum");
      expect(query('[data-test="tutorial-clip-video"]')?.getAttribute("src")).toContain("klassrum.mp4");
      expect(play).not.toHaveBeenCalled();
    } finally {
      play.mockRestore();
    }
  });

  it("renders nothing and ignores Escape while closed", async () => {
    await mountDialog({ open: false });

    expect(query("[data-test='tutorial-clip-dialog']")).toBeNull();
    document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(wrapper?.emitted("close")).toBeUndefined();
  });
});
