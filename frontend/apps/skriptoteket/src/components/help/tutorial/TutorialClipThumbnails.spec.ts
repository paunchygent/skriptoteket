import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import TutorialClipThumbnails from "./TutorialClipThumbnails.vue";
import { loadTutorialClipManifest, resetTutorialClipManifestCacheForTests } from "./tutorialClipManifest";

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

let wrapper: VueWrapper | null = null;

async function mountWith(response: Response, section = "planner_overview") {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
  wrapper = mount(TutorialClipThumbnails, { props: { section }, attachTo: document.body });
  await loadTutorialClipManifest();
  await nextTick();
  return wrapper;
}

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  resetTutorialClipManifestCacheForTests();
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("TutorialClipThumbnails", () => {
  it("renders nothing when the manifest is missing", async () => {
    const view = await mountWith(new Response("Not found", { status: 404 }));
    expect(view.find("[data-test='tutorial-clip-thumbnails']").exists()).toBe(false);
  });

  it("renders nothing for a section without clips", async () => {
    const view = await mountWith(Response.json(manifest), "planner_seating");
    expect(view.find("[data-test='tutorial-clip-thumbnails']").exists()).toBe(false);
  });

  it("lists the section's clips in a reserved 16:9 box and opens the dialog on that clip", async () => {
    const view = await mountWith(Response.json(manifest));

    const thumbnails = view.findAll("[data-test='tutorial-clip-thumbnail']");
    expect(thumbnails).toHaveLength(1);
    expect(thumbnails[0]?.text()).toContain("0:08");
    expect(thumbnails[0]?.find("img").attributes("src")).toBe(
      "/static/media/klassrumskartan/klass.jpg",
    );
    expect(thumbnails[0]?.find(".aspect-video").exists()).toBe(true);
    expect(document.body.querySelector("[data-test='tutorial-clip-dialog']")).toBeNull();

    await thumbnails[0]?.trigger("click");
    await nextTick();

    expect(document.body.querySelector("[data-test='tutorial-clip-dialog']")).not.toBeNull();
    expect(
      document.body.querySelector("[data-test='tutorial-clip-video']")?.getAttribute("src"),
    ).toBe("/static/media/klassrumskartan/klass.mp4");

    document.body
      .querySelector<HTMLButtonElement>("[data-test='tutorial-clip-dialog-close']")
      ?.click();
    await nextTick();
    expect(document.body.querySelector("[data-test='tutorial-clip-dialog']")).toBeNull();
  });
});
