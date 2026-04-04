/**
 * Donor-derived 2D playfield geometry for the Flunk-Out Frenzy prototype.
 *
 * This module keeps the board perimeter, lanes, gates, and switch anchors in a
 * compact, provenance-explicit map so the main donor-map barrel can stay small.
 */

import {
  WALL_263_POINTS,
  WALL_264_POINTS,
  WALL_268_POINTS,
} from "./donorBoundaryPaths";
import {
  WALL_010_POINTS,
  WALL_011_POINTS,
  WALL_013_POINTS,
  WALL_015_POINTS,
  WALL_016_POINTS,
  WALL_017_POINTS,
  WALL_018_POINTS,
  WALL_019_POINTS,
  WALL_021_POINTS,
  WALL_024_POINTS,
  WALL_002_POINTS,
  WALL_34_POINTS,
  WALL_76_POINTS,
  WALL_95_POINTS,
  WALL_234_POINTS,
  WALL_APRON1_POINTS,
  WALL_APRON2_POINTS,
} from "./donorShooterPaths";
import {
  closeDonorPath,
  donorPath,
  scaleDonorLength,
  scaleDonorPoint,
} from "./donorScale";

export const VPW_OUTER_BOUNDARY_RENDER_PATH = closeDonorPath(WALL_263_POINTS);
export const VPW_OUTER_BOUNDARY_MAIN_PATH = donorPath(WALL_263_POINTS.slice(0, 45));
export const VPW_OUTER_BOUNDARY_RIGHT_DESCENT_PATH = donorPath(WALL_263_POINTS.slice(45, 55));
export const VPW_OUTER_BOUNDARY_SHOOTER_CORRIDOR_PATH = donorPath(WALL_263_POINTS.slice(54, 61));
export const VPW_LEFT_UPPER_GUIDE_PATH = donorPath(WALL_268_POINTS);
export const VPW_LEFT_UPPER_GUIDE_DESCENT_PATH = donorPath(WALL_268_POINTS.slice(26, 37).reverse());
export const VPW_RIGHT_UPPER_GUIDE_PATH = donorPath(WALL_264_POINTS);
export const VPW_LEFT_OUTLANE_PATH = donorPath(WALL_76_POINTS);
export const VPW_LEFT_INLANE_PATH = donorPath(WALL_016_POINTS);
export const VPW_RIGHT_INLANE_PATH = donorPath(WALL_015_POINTS);
export const VPW_RIGHT_OUTLANE_PATH = donorPath(WALL_234_POINTS);
export const VPW_LEFT_DRAIN_PATH = donorPath(WALL_013_POINTS);
export const VPW_RIGHT_DRAIN_PATH = donorPath(WALL_021_POINTS);
export const VPW_SHOOTER_OUTER_POLYGON = donorPath(WALL_95_POINTS);
export const VPW_SHOOTER_DIVIDER_POLYGON = donorPath(WALL_34_POINTS);
export const VPW_RIGHT_RECEIVE_MOUTH_OUTER_POLYGON = donorPath(WALL_018_POINTS);
export const VPW_RIGHT_RECEIVE_MOUTH_INNER_POLYGON = donorPath(WALL_019_POINTS);
export const VPW_SHOOTER_HANDOFF_UPPER_POLYGON = donorPath(WALL_010_POINTS);
export const VPW_SHOOTER_HANDOFF_LOWER_POLYGON = donorPath(WALL_011_POINTS);
export const VPW_RIGHT_RETURN_THROAT_SHIELD_POLYGON = donorPath(WALL_024_POINTS);
export const VPW_APRON_1_POLYGON = donorPath(WALL_APRON1_POINTS);
export const VPW_APRON_2_POLYGON = donorPath(WALL_APRON2_POINTS);
export const VPW_RIGHT_UPPER_INNER_METAL_PATH = donorPath(WALL_002_POINTS);
export const VPW_LEFT_UPPER_INNER_METAL_PATH = donorPath(WALL_017_POINTS);

export const VPW_SHOOTER_DIVIDER_PATH = VPW_SHOOTER_DIVIDER_POLYGON;
export const VPW_SHOOTER_OUTER_INNER_EDGE = donorPath([
  [1057.0, 22.5],
  [1057.0, 1948.0],
]);

export const VPW_SHOOTER_LANE_LEFT_BOUNDARY_SEGMENTS = Object.freeze({
  upperHandoff: donorPath([
    [939.0524, 1035.5],
    [976.2514, 1075.1033],
  ]),
  wall010: donorPath([
    [976.2514, 1075.1033],
    [1006.4996, 1238.5991],
  ]),
  wall010ToWall011: donorPath([
    [1006.4996, 1238.5991],
    [978.55865, 1272.3873],
  ]),
  wall011: donorPath([
    [978.55865, 1272.3873],
    [961.1782, 1368.8137],
  ]),
  wall011ToDivider: donorPath([
    [961.1782, 1368.8137],
    [1000.0, 1438.0],
  ]),
  divider: donorPath([
    [1000.0, 1438.0],
    [1000.0, 1760.0],
  ]),
  apronToPlunger: donorPath([
    [1000.0, 1759.8445],
    [1000.0, 1829.1067],
    [1002.51404, 1851.5724],
  ]),
});

export const VPW_LEFT_SLING_TRIANGLE = Object.freeze([
  scaleDonorPoint(316.74026, 1485.6082),
  scaleDonorPoint(379.1071, 1663.5806),
  scaleDonorPoint(365.39246, 1667.9783),
] as const);

export const VPW_RIGHT_SLING_TRIANGLE = Object.freeze([
  scaleDonorPoint(812.0981, 1484.1681),
  scaleDonorPoint(807.8043, 1496.3696),
  scaleDonorPoint(744.2882, 1676.8601),
] as const);

export const VPW_FLIPPER_GEOMETRY = Object.freeze({
  length: scaleDonorLength(115),
  thickness: scaleDonorLength(20),
});

export const VPW_FLIPPER_PIVOTS = Object.freeze({
  left: scaleDonorPoint(405.96786, 1833.0863),
  right: scaleDonorPoint(724.0889, 1832.9792),
});

export const VPW_LOWER_SWITCH_CENTERS = Object.freeze({
  leftInlane: scaleDonorPoint(255.11618, 1585.1604),
  leftOutlane: scaleDonorPoint(180.13579, 1723.3805),
  rightInlane: scaleDonorPoint(871.65485, 1584.7524),
  rightOutlane: scaleDonorPoint(939.325, 1652.8694),
});

export const VPW_SHOOTER_SENSOR_CENTER = scaleDonorPoint(1028.5228, 1884.67);
export const VPW_PLUNGER_ROLLOVER_CENTER = scaleDonorPoint(1032.7303, 1890.2291);

export const VPW_GATE_CENTERS = Object.freeze({
  rightReturn: scaleDonorPoint(722.30853, 818.7679),
});

export const VPW_GATE_SPECS = Object.freeze({
  rightReturn: Object.freeze({
    center: scaleDonorPoint(722.30853, 818.7679),
    width: scaleDonorLength(100),
    height: scaleDonorLength(50),
    rotationDeg: 14,
  }),
});

export const VPW_BUMPER_CENTERS = Object.freeze({
  left: scaleDonorPoint(390.9, 359.6),
  top: scaleDonorPoint(550.8, 479.8),
  right: scaleDonorPoint(711.9, 369.9),
});
