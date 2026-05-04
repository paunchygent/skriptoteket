/**
 * Shared planner-toolbar overflow ladder for deterministic desktop cutovers.
 *
 * Relationships:
 * - measures the live planner action bar and freezes the exact width cutoffs
 *   where lower-priority controls must migrate into overflow
 * - consumed by grouping and seating toolbars so authenticated and guest
 *   shells follow one shared collapse doctrine
 * - exports pure helpers so specs can verify just-above / just-below threshold
 *   behavior without relying on browser-only layout side effects
 */

import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  onUpdated,
  ref,
  watch,
  type Ref,
} from "vue";

export type PlannerToolbarOverflowThresholds = Record<string, number>;

export type PlannerToolbarOverflowContribution = {
  id: string;
  selector: string;
};

type UsePlannerToolbarOverflowOptions = {
  getRootElement: () => HTMLElement | null;
  contributions: PlannerToolbarOverflowContribution[];
  isEnabled?: Ref<boolean>;
  alwaysOverflowContributionIds?: Ref<string[]>;
};

function roundUpPx(value: number): number {
  return Math.max(0, Math.ceil(value));
}

function parseGapPx(rootElement: HTMLElement): number {
  const computedStyle = window.getComputedStyle(rootElement);
  const rawGap = computedStyle.columnGap || computedStyle.gap || "0";
  const parsed = Number.parseFloat(rawGap);
  return Number.isFinite(parsed) ? parsed : 0;
}

function measureZoneRequirementPx(rootElement: HTMLElement): number {
  const zones = [...rootElement.querySelectorAll<HTMLElement>("[data-zone]")].filter((zone) => {
    return zone.offsetParent !== null || zone.getBoundingClientRect().width > 0;
  });
  if (zones.length === 0) {
    return 0;
  }

  const gapPx = parseGapPx(rootElement);
  const zoneWidthsPx = zones.reduce((sum, zone) => sum + zone.getBoundingClientRect().width, 0);
  return zoneWidthsPx + gapPx * Math.max(0, zones.length - 1);
}

export function measureContributionWidthPx(
  rootElement: HTMLElement,
  contribution: PlannerToolbarOverflowContribution,
): number {
  const element = rootElement.querySelector<HTMLElement>(contribution.selector);
  if (!element) {
    return 0;
  }

  const zoneElement = element.closest<HTMLElement>("[data-zone]");
  if (!zoneElement) {
    return Math.max(0, element.getBoundingClientRect().width);
  }

  const visibleZoneItems = [...zoneElement.children].filter((candidate): candidate is HTMLElement => {
    return candidate instanceof HTMLElement
      && (candidate.offsetParent !== null || candidate.getBoundingClientRect().width > 0);
  });
  const contributionIndex = visibleZoneItems.findIndex((candidate) => candidate === element);
  const elementRect = element.getBoundingClientRect();
  if (contributionIndex === -1) {
    return Math.max(0, elementRect.width);
  }

  const nextItem = visibleZoneItems[contributionIndex + 1] ?? null;
  if (nextItem) {
    return Math.max(0, nextItem.getBoundingClientRect().left - elementRect.left);
  }

  const previousItem = contributionIndex > 0 ? visibleZoneItems[contributionIndex - 1] : null;
  if (previousItem) {
    return Math.max(0, elementRect.right - previousItem.getBoundingClientRect().right);
  }

  const visibleZones = [...rootElement.querySelectorAll<HTMLElement>("[data-zone]")]
    .filter((candidate) => candidate.offsetParent !== null || candidate.getBoundingClientRect().width > 0);
  const zoneIndex = visibleZones.findIndex((candidate) => candidate === zoneElement);
  const nextZone = zoneIndex >= 0 ? visibleZones[zoneIndex + 1] ?? null : null;
  if (nextZone) {
    return Math.max(0, nextZone.getBoundingClientRect().left - elementRect.left);
  }

  const previousZone = zoneIndex > 0 ? visibleZones[zoneIndex - 1] : null;
  if (previousZone) {
    return Math.max(0, elementRect.right - previousZone.getBoundingClientRect().right);
  }

  return Math.max(0, elementRect.width);
}

export function derivePlannerToolbarOverflowThresholds(args: {
  fullyVisibleRequiredWidthPx: number;
  contributionOrder: string[];
  contributionWidthsPx: Record<string, number>;
}): PlannerToolbarOverflowThresholds {
  const thresholds: PlannerToolbarOverflowThresholds = {};
  let reclaimedWidthPx = 0;
  for (const contributionId of args.contributionOrder) {
    thresholds[contributionId] = Math.max(
      0,
      roundUpPx(args.fullyVisibleRequiredWidthPx) - reclaimedWidthPx,
    );
    reclaimedWidthPx += roundUpPx(args.contributionWidthsPx[contributionId] ?? 0);
  }

  return thresholds;
}

export function resolveOverflowHiddenContributionIds(args: {
  availableWidthPx: number;
  contributionOrder: string[];
  thresholds: PlannerToolbarOverflowThresholds;
}): string[] {
  for (let index = 0; index < args.contributionOrder.length; index += 1) {
    const contributionId = args.contributionOrder[index];
    if (args.availableWidthPx >= (args.thresholds[contributionId] ?? 0)) {
      return args.contributionOrder.slice(0, index);
    }
  }
  return [...args.contributionOrder];
}

function buildStageLabel(hiddenContributionIds: string[]): string {
  if (hiddenContributionIds.length === 0) {
    return "all-visible";
  }
  return `${hiddenContributionIds.join("-")}-overflow`;
}

export function usePlannerToolbarOverflow(options: UsePlannerToolbarOverflowOptions) {
  const hiddenContributionIds = ref<string[]>([]);
  const contributionWidthsPx = ref<Record<string, number>>({});
  const thresholds = ref<PlannerToolbarOverflowThresholds>({});
  const fullyVisibleRequiredWidthPx = ref(0);
  const isEnabled = options.isEnabled ?? computed(() => true);
  const alwaysOverflowContributionIds = options.alwaysOverflowContributionIds ?? computed<string[]>(() => []);
  const contributionOrder = options.contributions.map((contribution) => contribution.id);

  let resizeObserver: ResizeObserver | null = null;
  let scheduledMeasurementId: number | null = null;

  function measureNow(): void {
    scheduledMeasurementId = null;
    if (!isEnabled.value) {
      hiddenContributionIds.value = [];
      fullyVisibleRequiredWidthPx.value = 0;
      return;
    }

    const rootElement = options.getRootElement();
    if (!rootElement) {
      return;
    }

    const nextContributionWidthsPx = { ...contributionWidthsPx.value };
    for (const contribution of options.contributions) {
      const measuredWidthPx = measureContributionWidthPx(rootElement, contribution);
      if (measuredWidthPx > 0) {
        nextContributionWidthsPx[contribution.id] = Math.max(
          nextContributionWidthsPx[contribution.id] ?? 0,
          roundUpPx(measuredWidthPx),
        );
      }
    }
    contributionWidthsPx.value = nextContributionWidthsPx;

    const currentRequiredWidthPx = measureZoneRequirementPx(rootElement);
    const estimatedFullyVisibleWidthPx = currentRequiredWidthPx + hiddenContributionIds.value.reduce((sum, id) => {
      return sum + roundUpPx(nextContributionWidthsPx[id] ?? 0);
    }, 0);
    fullyVisibleRequiredWidthPx.value = Math.max(
      fullyVisibleRequiredWidthPx.value,
      roundUpPx(estimatedFullyVisibleWidthPx),
    );
    thresholds.value = derivePlannerToolbarOverflowThresholds({
      fullyVisibleRequiredWidthPx: fullyVisibleRequiredWidthPx.value,
      contributionOrder,
      contributionWidthsPx: nextContributionWidthsPx,
    });
    const measuredHiddenContributionIds = resolveOverflowHiddenContributionIds({
      availableWidthPx: rootElement.clientWidth,
      contributionOrder,
      thresholds: thresholds.value,
    });
    const forcedHiddenContributionIds = new Set(alwaysOverflowContributionIds.value);
    hiddenContributionIds.value = contributionOrder.filter((id) => {
      return forcedHiddenContributionIds.has(id) || measuredHiddenContributionIds.includes(id);
    });
  }

  function scheduleMeasurement(): void {
    if (scheduledMeasurementId !== null) {
      window.cancelAnimationFrame(scheduledMeasurementId);
    }
    scheduledMeasurementId = window.requestAnimationFrame(() => {
      void nextTick(() => {
        measureNow();
      });
    });
  }

  function disconnectResizeObserver(): void {
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
  }

  watch(
    () => options.getRootElement(),
    (rootElement) => {
      disconnectResizeObserver();
      if (!rootElement || typeof ResizeObserver === "undefined") {
        return;
      }
      resizeObserver = new ResizeObserver(() => {
        scheduleMeasurement();
      });
      resizeObserver.observe(rootElement);
      scheduleMeasurement();
    },
    { immediate: true },
  );

  watch(isEnabled, () => {
    scheduleMeasurement();
  });

  watch(alwaysOverflowContributionIds, () => {
    scheduleMeasurement();
  });

  onMounted(() => {
    scheduleMeasurement();
  });

  onUpdated(() => {
    scheduleMeasurement();
  });

  onBeforeUnmount(() => {
    disconnectResizeObserver();
    if (scheduledMeasurementId !== null) {
      window.cancelAnimationFrame(scheduledMeasurementId);
      scheduledMeasurementId = null;
    }
  });

  return {
    hiddenContributionIds: computed(() => hiddenContributionIds.value),
    stageLabel: computed(() => buildStageLabel(hiddenContributionIds.value)),
    thresholds: computed(() => thresholds.value),
    isInline(contributionId: string): boolean {
      return !hiddenContributionIds.value.includes(contributionId);
    },
  };
}
