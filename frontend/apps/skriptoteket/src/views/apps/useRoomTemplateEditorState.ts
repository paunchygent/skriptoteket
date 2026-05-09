/**
 * Room-template editor state composable.
 *
 * This composable owns interactive builder state for room-template editing:
 * grid dimensions, tool selection, hover/ghost state, zoom framing, parsed
 * payload data, and placement rules. The modal shell stays focused on submit
 * and delete lifecycle only.
 */

import { computed, type Ref, ref, watch } from "vue";

import type { RoomFixture, RoomFixtureType, RoomTemplate, Seat } from "./classroomPlannerTypes";
import {
  MIN_ROOM_GRID_COLS,
  MIN_ROOM_GRID_ROWS,
  ROOM_GRID_UNIT,
  buildRoomFixtureLabel,
  getRoomFixturePaletteEntry,
  isWallFixtureType,
  normalizeFixturePlacement,
  normalizeRoomGrid,
  resolveWallSideForPointer,
  roomFixturePalette,
  type PointerAnchor,
  type RoomGridDimensions,
  type WallSide,
} from "./roomFixtureLayout";
import {
  buildRoomFixtureFromGridPlacement,
  getRoomFloorLayerStyle,
  getRoomSurfaceMetrics,
  getRoomSurfaceStyle,
} from "./roomFixturePresentation";
import {
  type BuilderTool,
  type FixturePlacement,
  type HoveredCell,
  buildParsedFixtures,
  buildParsedSeats,
  findFloorFixtureAt,
  findSameKindFixtureAt,
  findWallFixtureAt,
  fixtureFits,
  hydrateRoomTemplateEditor,
  isSeatAt,
  reanchorFixturesToGrid,
  seatKey,
  templateFitsGridAfterResize,
} from "./roomTemplateEditorDomain";
import { useRoomViewportZoom } from "./useRoomViewportZoom";

export type RoomTemplateGhostPlacement = {
  row: number;
  col: number;
  width: number;
  height: number;
  wallSide: WallSide | null;
  type: RoomFixtureType | "seat";
  canPlace: boolean;
};

export type RoomTemplateCellClickOptions = {
  suppressHoverPreview?: boolean;
};

export function useRoomTemplateEditorState(template: Ref<RoomTemplate | null | undefined>) {
  const name = ref("");
  const selectedTool = ref<BuilderTool>("seat");
  const seatCells = ref<string[]>([]);
  const fixtures = ref<FixturePlacement[]>([]);
  const gridCols = ref(MIN_ROOM_GRID_COLS);
  const gridRows = ref(MIN_ROOM_GRID_ROWS);
  const hoveredCell = ref<HoveredCell | null>(null);
  const pointerAnchor = ref<PointerAnchor | null>(null);
  const error = ref<string | null>(null);

  const roomGrid = computed<RoomGridDimensions>(() => normalizeRoomGrid({
    cols: gridCols.value,
    rows: gridRows.value,
  }));
  const roomSurfaceStyle = computed(() => getRoomSurfaceStyle(roomGrid.value));
  const roomFloorLayerStyle = computed(() => getRoomFloorLayerStyle(roomGrid.value));
  const roomSurfaceMetrics = computed(() => getRoomSurfaceMetrics(roomGrid.value));
  const {
    scale: builderScale,
    scaledSurfaceStyle: builderScaledSurfaceStyle,
    scalePercent: builderScalePercent,
    setViewportSize: setBuilderViewportSize,
    zoomOut,
    zoomIn,
    resetZoom: resetBuilderZoom,
  } = useRoomViewportZoom(roomSurfaceMetrics, { resetSource: template });

  const canShrinkCols = computed(() => {
    return gridCols.value > MIN_ROOM_GRID_COLS && templateFitsGridAfterResize(
      seatCells.value,
      fixtures.value,
      roomGrid.value,
      {
        cols: gridCols.value - 1,
        rows: gridRows.value,
      },
    );
  });
  const canShrinkRows = computed(() => {
    return gridRows.value > MIN_ROOM_GRID_ROWS && templateFitsGridAfterResize(
      seatCells.value,
      fixtures.value,
      roomGrid.value,
      {
        cols: gridCols.value,
        rows: gridRows.value - 1,
      },
    );
  });

  const parsedSeats = computed<Seat[]>(() => buildParsedSeats(seatCells.value));
  const parsedFixtures = computed<RoomFixture[]>(() => buildParsedFixtures(fixtures.value));

  function currentWallSide(): WallSide | null {
    if (!pointerAnchor.value || !hoveredCell.value) {
      return null;
    }

    return resolveWallSideForPointer(
      pointerAnchor.value,
      hoveredCell.value.row,
      hoveredCell.value.col,
      roomGrid.value,
    );
  }

  function resolveWallSideForPlacement(
    event: MouseEvent | undefined,
    row: number,
    col: number,
  ): WallSide | null {
    const target = event?.currentTarget;
    if (!(target instanceof HTMLElement)) {
      return currentWallSide();
    }

    const rect = target.getBoundingClientRect();
    const clientX = event?.clientX ?? (rect.left + (rect.width / 2));
    const clientY = event?.clientY ?? (rect.top + (rect.height / 2));
    const relativeX = rect.width === 0 ? 0.5 : (clientX - rect.left) / rect.width;
    const relativeY = rect.height === 0 ? 0.5 : (clientY - rect.top) / rect.height;

    return resolveWallSideForPointer(
      {
        x: col * ROOM_GRID_UNIT + (relativeX * ROOM_GRID_UNIT),
        y: row * ROOM_GRID_UNIT + (relativeY * ROOM_GRID_UNIT),
        relativeX,
        relativeY,
      },
      row,
      col,
      roomGrid.value,
    );
  }

  function updateHoverState(event: MouseEvent, row: number, col: number): void {
    hoveredCell.value = { row, col };
    const target = event.currentTarget;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    const rect = target.getBoundingClientRect();
    const relativeX = rect.width === 0 ? 0.5 : (event.clientX - rect.left) / rect.width;
    const relativeY = rect.height === 0 ? 0.5 : (event.clientY - rect.top) / rect.height;
    pointerAnchor.value = {
      x: col * ROOM_GRID_UNIT + (relativeX * ROOM_GRID_UNIT),
      y: row * ROOM_GRID_UNIT + (relativeY * ROOM_GRID_UNIT),
      relativeX,
      relativeY,
    };
  }

  function focusCell(row: number, col: number): void {
    hoveredCell.value = { row, col };
  }

  function clearHoverState(): void {
    hoveredCell.value = null;
    pointerAnchor.value = null;
  }

  function removeFixtureById(fixtureId: string): void {
    fixtures.value = fixtures.value.filter((fixture) => fixture.id !== fixtureId);
  }

  function finishPlacementInteraction(options?: RoomTemplateCellClickOptions): void {
    if (options?.suppressHoverPreview) {
      clearHoverState();
    }
  }

  function toggleGridCell(
    row: number,
    col: number,
    event?: MouseEvent,
    options?: RoomTemplateCellClickOptions,
  ): void {
    error.value = null;
    if (event && !options?.suppressHoverPreview) {
      updateHoverState(event, row, col);
    }

    const occupiedFloorFixture = findFloorFixtureAt(fixtures.value, row, col);
    const occupiedWallFixture = findWallFixtureAt(fixtures.value, row, col);

    if (selectedTool.value === "erase") {
      if (occupiedWallFixture) {
        removeFixtureById(occupiedWallFixture.id);
        finishPlacementInteraction(options);
        return;
      }
      if (occupiedFloorFixture) {
        removeFixtureById(occupiedFloorFixture.id);
        finishPlacementInteraction(options);
        return;
      }
      seatCells.value = seatCells.value.filter((value) => value !== seatKey(row, col));
      finishPlacementInteraction(options);
      return;
    }

    if (selectedTool.value === "seat") {
      if (occupiedFloorFixture || occupiedWallFixture) {
        error.value = "Ta bort möbeln eller väggobjektet först om du vill lägga en plats där.";
        finishPlacementInteraction(options);
        return;
      }
      const key = seatKey(row, col);
      seatCells.value = isSeatAt(seatCells.value, row, col)
        ? seatCells.value.filter((value) => value !== key)
        : [...seatCells.value, key];
      finishPlacementInteraction(options);
      return;
    }

    const paletteItem = getRoomFixturePaletteEntry(selectedTool.value);
    if (!paletteItem) {
      return;
    }

    const sameKindFixture = findSameKindFixtureAt(fixtures.value, selectedTool.value, row, col);
    if (sameKindFixture) {
      removeFixtureById(sameKindFixture.id);
      finishPlacementInteraction(options);
      return;
    }

    const wallSide = isWallFixtureType(selectedTool.value)
      ? resolveWallSideForPlacement(event, row, col)
      : null;
    const placement = normalizeFixturePlacement(selectedTool.value, row, col, roomGrid.value, wallSide);
    if (!placement || !fixtureFits(fixtures.value, seatCells.value, selectedTool.value, row, col, roomGrid.value, wallSide)) {
      error.value = isWallFixtureType(selectedTool.value)
        ? "Det valda objektet måste få plats längs väggen utan att krocka med andra väggobjekt."
        : "Det valda objektet får inte plats där eller krockar med befintlig möblering.";
      finishPlacementInteraction(options);
      return;
    }

    fixtures.value = [
      ...fixtures.value,
      {
        id: `${selectedTool.value}-${crypto.randomUUID().slice(0, 8)}`,
        type: selectedTool.value,
        row: placement.row,
        col: placement.col,
        width: placement.width,
        height: placement.height,
        label: buildRoomFixtureLabel(selectedTool.value),
      },
    ];
    finishPlacementInteraction(options);
  }

  function resizeRoom(axis: "cols" | "rows", delta: 1 | -1): void {
    error.value = null;
    const currentGrid = roomGrid.value;
    if (axis === "cols") {
      if (delta < 0 && !canShrinkCols.value) {
        error.value = "Ta bort eller flytta objekt längst ut till höger innan du gör klassrummet smalare.";
        return;
      }
      const nextGrid = {
        cols: Math.max(MIN_ROOM_GRID_COLS, gridCols.value + delta),
        rows: gridRows.value,
      };
      fixtures.value = reanchorFixturesToGrid(fixtures.value, currentGrid, nextGrid);
      gridCols.value = nextGrid.cols;
      return;
    }

    if (delta < 0 && !canShrinkRows.value) {
      error.value = "Ta bort eller flytta objekt längst ned innan du gör klassrummet lägre.";
      return;
    }
    const nextGrid = {
      cols: gridCols.value,
      rows: Math.max(MIN_ROOM_GRID_ROWS, gridRows.value + delta),
    };
    fixtures.value = reanchorFixturesToGrid(fixtures.value, currentGrid, nextGrid);
    gridRows.value = nextGrid.rows;
  }

  function clearRoomContents(): void {
    seatCells.value = [];
    fixtures.value = [];
    selectedTool.value = "seat";
    clearHoverState();
    error.value = null;
  }

  watch(
    template,
    (nextTemplate) => {
      const hydratedState = hydrateRoomTemplateEditor(nextTemplate);
      name.value = hydratedState.name;
      gridCols.value = hydratedState.gridCols;
      gridRows.value = hydratedState.gridRows;
      seatCells.value = hydratedState.seatCells;
      fixtures.value = hydratedState.fixtures;
      selectedTool.value = "seat";
      clearHoverState();
      error.value = null;
    },
    { immediate: true },
  );

  const ghostPlacement = computed<RoomTemplateGhostPlacement | null>(() => {
    if (!hoveredCell.value || selectedTool.value === "erase") {
      return null;
    }

    if (selectedTool.value === "seat") {
      return {
        row: hoveredCell.value.row,
        col: hoveredCell.value.col,
        width: 1,
        height: 1,
        wallSide: null,
        type: "seat",
        canPlace: !findFloorFixtureAt(fixtures.value, hoveredCell.value.row, hoveredCell.value.col)
          && !findWallFixtureAt(fixtures.value, hoveredCell.value.row, hoveredCell.value.col),
      };
    }

    const wallSide = isWallFixtureType(selectedTool.value) ? currentWallSide() : null;
    const placement = normalizeFixturePlacement(
      selectedTool.value,
      hoveredCell.value.row,
      hoveredCell.value.col,
      roomGrid.value,
      wallSide,
    );
    if (!placement) {
      return null;
    }

    return {
      ...placement,
      type: selectedTool.value,
      canPlace:
        !!findSameKindFixtureAt(
          fixtures.value,
          selectedTool.value,
          hoveredCell.value.row,
          hoveredCell.value.col,
        )
        || fixtureFits(
          fixtures.value,
          seatCells.value,
          selectedTool.value,
          hoveredCell.value.row,
          hoveredCell.value.col,
          roomGrid.value,
          wallSide,
        ),
    };
  });

  const ghostRenderableFixture = computed<RoomFixture | null>(() => {
    if (!ghostPlacement.value || ghostPlacement.value.type === "seat") {
      return null;
    }

    return buildRoomFixtureFromGridPlacement({
      id: `ghost-${ghostPlacement.value.type}`,
      type: ghostPlacement.value.type,
      row: ghostPlacement.value.row,
      col: ghostPlacement.value.col,
      width: ghostPlacement.value.width,
      height: ghostPlacement.value.height,
      label: buildRoomFixtureLabel(ghostPlacement.value.type),
    });
  });

  const isValid = computed(() => {
    return name.value.trim().length > 0;
  });

  return {
    name,
    selectedTool,
    seatCells,
    fixtures,
    hoveredCell,
    error,
    roomGrid,
    roomSurfaceStyle,
    roomFloorLayerStyle,
    roomSurfaceMetrics,
    builderScale,
    builderScaledSurfaceStyle,
    builderScalePercent,
    canShrinkCols,
    canShrinkRows,
    roomFixturePalette,
    parsedSeats,
    parsedFixtures,
    ghostPlacement,
    ghostRenderableFixture,
    isValid,
    updateHoverState,
    focusCell,
    clearHoverState,
    toggleGridCell,
    resizeRoom,
    setBuilderViewportSize,
    zoomOut,
    zoomIn,
    resetBuilderZoom,
    clearRoomContents,
  };
}
