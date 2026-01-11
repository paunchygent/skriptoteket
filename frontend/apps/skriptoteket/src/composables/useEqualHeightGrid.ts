import { nextTick, onBeforeUnmount, onMounted, ref, watch, type Ref } from "vue";

type EqualHeightGridOptions = {
  selector?: string;
  cssVar?: string;
};

export function useEqualHeightGrid<T>(items: Ref<T[]>, options: EqualHeightGridOptions = {}) {
  const gridRef = ref<HTMLElement | null>(null);
  const selector = options.selector ?? "[data-catalog-card]";
  const cssVar = options.cssVar ?? "--catalog-card-height";
  let observer: ResizeObserver | null = null;
  let rafId: number | null = null;

  function measure(): void {
    const grid = gridRef.value;
    if (!grid) return;

    const cards = Array.from(grid.querySelectorAll<HTMLElement>(selector));
    let maxHeight = 0;
    for (const card of cards) {
      const height = card.getBoundingClientRect().height;
      if (height > maxHeight) {
        maxHeight = height;
      }
    }

    if (maxHeight > 0) {
      grid.style.setProperty(cssVar, `${Math.ceil(maxHeight)}px`);
    } else {
      grid.style.removeProperty(cssVar);
    }
  }

  function scheduleMeasure(): void {
    if (rafId !== null) return;
    rafId = window.requestAnimationFrame(() => {
      rafId = null;
      measure();
    });
  }

  function observeCards(): void {
    const grid = gridRef.value;
    if (!grid) return;

    observer?.disconnect();

    if (typeof ResizeObserver === "undefined") {
      scheduleMeasure();
      return;
    }

    observer = new ResizeObserver(() => scheduleMeasure());
    grid.querySelectorAll<HTMLElement>(selector).forEach((card) => {
      observer?.observe(card);
    });

    scheduleMeasure();
  }

  onMounted(() => {
    void nextTick(() => {
      observeCards();
    });
  });

  watch(items, async () => {
    await nextTick();
    observeCards();
  });

  onBeforeUnmount(() => {
    observer?.disconnect();
    if (rafId !== null) {
      window.cancelAnimationFrame(rafId);
    }
  });

  return { gridRef };
}
