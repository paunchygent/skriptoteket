/**
 * VPW donor topology map for the Flunk-Out Frenzy prototype table.
 *
 * The board carriers in this module are traced from the donor table's native
 * drag-point chains instead of a locally simplified redraw. That keeps the
 * visible boundary grammar and the compiled wall carriers aligned to the donor
 * table rather than a hybrid of donor and legacy Flunk-Out geometry.
 */

import type { TablePoint } from "./tableDefinitionTypes";
import { v } from "./pinballTableMath";

const DONOR_BOARD_WIDTH = 1081;
const DONOR_BOARD_HEIGHT = 2162;

const WALL_263_POINTS = [
  [1057.4192, 22.5],
  [23.4192, 22.5],
  [23.4192, 343.0643],
  [23.4192, 1225.0],
  [102.4192, 1225.0],
  [102.4192, 1950.0],
  [153.0559, 1950.0],
  [152.7131, 1520.6652],
  [153.3767, 1488.8502],
  [159.2387, 1455.5753],
  [164.1724, 1440.7512],
  [188.0848, 1376.0435],
  [185.4498, 1374.7314],
  [184.4192, 1377.5],
  [176.4192, 1377.5],
  [143.4192, 1411.3099],
  [123.4192, 1411.4921],
  [123.4192, 1180.0],
  [168.6571, 1046.7655],
  [171.9103, 1053.1973],
  [174.189, 1053.9633],
  [176.6916, 1052.8971],
  [177.3383, 1050.2087],
  [113.4485, 923.8345],
  [101.1036, 883.9068],
  [104.1674, 864.4704],
  [118.6315, 852.7654],
  [144.2077, 853.4264],
  [145.7103, 858.4571],
  [149.7162, 857.0154],
  [98.3007, 709.7277],
  [36.9802, 504.9415],
  [25.8198, 437.153],
  [25.9192, 344.5],
  [31.7248, 307.0742],
  [49.0242, 250.5267],
  [111.3278, 144.7194],
  [220.8144, 62.6761],
  [297.2983, 33.5886],
  [371.7227, 28.0732],
  [412.5236, 27.3327],
  [717.0503, 26.4437],
  [792.204, 29.5919],
  [855.9277, 40.1354],
  [932.493, 78.7084],
  [1000.5584, 145.0418],
  [1031.7272, 202.826],
  [1047.4941, 247.8355],
  [1051.4192, 320.0],
  [1051.9192, 350.0],
  [1049.4192, 390.0],
  [1044.8907, 418.6678],
  [1025.9574, 527.9441],
  [978.9874, 799.871],
  [951.4667, 956.0513],
  [935.7408, 1034.7188],
  [939.0524, 1035.5],
  [947.7321, 1035.5],
  [953.6216, 1035.5],
  [995.4193, 1255.0],
  [970.4193, 1265.0],
  [950.4193, 1376.1609],
  [976.4193, 1436.0],
  [1000.4193, 1436.0],
  [1000.4193, 1225.0],
  [1057.4192, 1225.0],
] as const;

const WALL_268_POINTS = [
  [442.3808, 141.6495],
  [363.2215, 112.1772],
  [357.5214, 111.6623],
  [351.4534, 113.9135],
  [211.2603, 203.8456],
  [162.7091, 242.948],
  [123.3026, 293.6587],
  [101.6732, 344.03],
  [95.9428, 390.7286],
  [99.586, 439.0066],
  [103.153, 438.8072],
  [99.9874, 407.6189],
  [99.9421, 406.3615],
  [102.0891, 406.2289],
  [101.6714, 399.6056],
  [99.6922, 399.6824],
  [99.5877, 381.904],
  [101.8381, 358.0649],
  [139.0145, 346.0901],
  [142.6682, 346.0824],
  [144.8, 348.1721],
  [178.035, 450.8105],
  [224.2265, 580.9482],
  [228.9639, 590.4926],
  [283.755, 685.9193],
  [286.9975, 690.4959],
  [291.455, 694.7176],
  [296.3906, 692.3706],
  [296.31, 684.9047],
  [260.991, 575.1672],
  [231.0, 571.1462],
  [158.1854, 365.627],
  [160.6736, 333.9634],
  [190.89, 255.4356],
  [270.1888, 192.2629],
  [413.9313, 191.366],
  [441.3383, 144.7138],
] as const;

const WALL_264_POINTS = [
  [785.4022, 156.8828],
  [812.5997, 175.3177],
  [840.314, 202.4479],
  [863.9709, 244.7976],
  [877.6456, 289.0],
  [880.2766, 315.0],
  [879.4, 340.0279],
  [875.8356, 362.6266],
  [868.4647, 392.3017],
  [858.0, 416.2741],
  [802.3321, 492.5089],
  [773.2, 528.9531],
  [749.8679, 556.4488],
  [706.5882, 606.4493],
  [708.9155, 608.4291],
  [710.0478, 607.0222],
  [725.0, 620.0],
  [573.0, 779.0],
  [573.0, 792.0],
  [642.0, 806.0],
  [640.4249, 851.8799],
  [657.0, 856.5],
  [725.3517, 628.8761],
  [807.011, 648.3759],
  [759.6701, 889.1252],
  [762.2411, 889.7864],
  [771.7898, 841.8584],
  [777.993, 843.3265],
  [777.6133, 845.67],
  [780.4464, 846.4542],
  [839.8811, 606.6422],
  [890.4392, 411.715],
  [887.4929, 410.3748],
  [885.4071, 418.4483],
  [864.5476, 410.4192],
  [867.8848, 403.1165],
  [879.1814, 363.4665],
  [883.332, 328.6867],
  [883.0164, 303.6319],
  [881.6, 293.3165],
  [950.0, 288.4333],
  [957.4899, 408.2887],
  [955.3111, 485.1387],
  [947.9443, 544.1702],
  [919.7168, 678.4448],
  [893.4334, 804.3245],
  [885.2823, 841.8664],
  [888.718, 842.1659],
  [896.775, 805.9463],
  [922.9595, 678.8531],
  [950.7103, 545.2827],
  [958.4164, 486.0694],
  [960.7, 449.3475],
  [960.8916, 412.8712],
  [975.1542, 412.8712],
  [975.0165, 415.8712],
  [978.0909, 415.8712],
  [979.3795, 390.8312],
  [977.251, 354.691],
  [968.5261, 306.593],
  [945.1037, 253.729],
  [890.1893, 180.6053],
  [830.6359, 133.4076],
  [796.6079, 117.7603],
  [795.1767, 121.0363],
  [807.5183, 126.0401],
  [802.0772, 162.6793],
  [788.1204, 153.1541],
] as const;

const WALL_76_POINTS = [
  [215.8858, 1725.8684],
  [216.4176, 1729.285],
  [220.4524, 1732.3158],
  [374.4533, 1839.4885],
  [377.0588, 1826.4204],
  [380.8818, 1817.5316],
  [391.5078, 1807.1687],
  [400.0067, 1802.1771],
  [255.4803, 1701.4923],
  [253.287, 1699.6006],
  [241.7267, 1687.8815],
  [232.2101, 1669.386],
  [228.3631, 1653.2634],
  [228.1461, 1647.5674],
  [228.0706, 1494.6249],
  [227.3754, 1491.0354],
  [225.0355, 1488.1945],
  [221.5356, 1487.2542],
  [218.0635, 1488.1761],
  [215.6009, 1490.8839],
  [214.7399, 1494.6096],
] as const;

const WALL_016_POINTS = [
  [290.408, 1491.0283],
  [292.3654, 1633.9905],
  [297.6447, 1645.8699],
  [363.2521, 1691.574],
  [365.3528, 1668.0586],
  [309.3695, 1502.279],
] as const;

const WALL_234_POINTS = [
  [910.7537, 1726.3988],
  [910.9524, 1495.5859],
  [910.1156, 1491.4606],
  [907.7961, 1488.5447],
  [904.1116, 1487.985],
  [900.592, 1489.0404],
  [898.6571, 1491.6377],
  [898.1536, 1495.0984],
  [897.7771, 1652.7131],
  [895.7165, 1664.8666],
  [889.0979, 1681.2365],
  [879.375, 1694.6335],
  [872.567, 1700.7935],
  [726.2136, 1803.789],
  [737.436, 1809.607],
  [744.4946, 1816.8997],
  [750.9476, 1829.3629],
  [751.7284, 1841.5824],
  [908.5865, 1731.7947],
  [910.1822, 1729.598],
] as const;

const WALL_015_POINTS = [
  [819.8828, 1501.3933],
  [762.8635, 1668.5781],
  [765.0838, 1692.5839],
  [830.8381, 1647.4343],
  [836.5035, 1635.3235],
  [838.4418, 1489.6583],
] as const;

const WALL_013_POINTS = [
  [403.2655, 1872.2633],
  [400.5919, 1873.6466],
  [400.2824, 1876.8445],
  [520.0548, 1956.4083],
  [523.5012, 1954.9283],
  [523.2908, 1950.9764],
] as const;

const WALL_021_POINTS = [
  [604.0799, 1951.0403],
  [603.8696, 1954.9922],
  [607.316, 1956.4722],
  [727.0883, 1876.9083],
  [726.7787, 1873.7104],
  [724.1052, 1872.3271],
] as const;

const WALL_95_POINTS = [
  [1057.0, 22.5],
  [1057.0, 1948.0],
  [1081.0, 1948.0],
  [1081.0, 22.5],
] as const;

const WALL_34_POINTS = [
  [976.0, 1438.0],
  [976.0, 1760.0],
  [1000.0, 1760.0],
  [1000.0, 1438.0],
] as const;

export const PROTOTYPE_ALPHA_VPW_DONOR_SCALE = 600 / DONOR_BOARD_WIDTH;
export const PROTOTYPE_ALPHA_VPW_DONOR_BOARD = Object.freeze({
  width: 600,
  height: Math.round(DONOR_BOARD_HEIGHT * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
});

export const PROTOTYPE_ALPHA_VPW_DONOR_SOURCES = Object.freeze({
  outerBoundary:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall263.json",
  leftUpperGuide:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall268.json",
  rightUpperGuide:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall264.json",
  leftOutlane:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall76.json",
  leftInlane:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall016.json",
  rightInlane:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall015.json",
  rightOutlane:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall234.json",
  leftDrainGuide:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall013.json",
  rightDrainGuide:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall021.json",
  shooterOuterWall:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall95.json",
  shooterLaneDivider:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall34.json",
  leftSling:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.LeftSlingShot.json",
  rightSling:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.RightSlingShot.json",
  leftFlipper:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Flipper.LeftFlipper.json",
  rightFlipper:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Flipper.RightFlipper.json",
  leftInlaneSwitch:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.sw53.json",
  leftOutlaneSwitch:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.sw54.json",
  rightInlaneSwitch:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.sw56.json",
  rightOutlaneSwitch:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.sw55.json",
  shooterTrigger:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.swplunger.json",
  plungerRollover:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Trigger.sw16.json",
  returnGate:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Gate.GateSW49.json",
  rampGate:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Gate.GateSW51.json",
});

function donorPoint(x: number, y: number): TablePoint {
  return v(
    roundTenth(x * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
    roundTenth(y * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
  );
}

export function scaleDonorPoint(x: number, y: number): TablePoint {
  return donorPoint(x, y);
}

export function scaleDonorLength(value: number): number {
  return roundTenth(value * PROTOTYPE_ALPHA_VPW_DONOR_SCALE);
}

function donorPath(points: readonly (readonly [number, number])[]): readonly TablePoint[] {
  return points.map(([x, y]) => donorPoint(x, y));
}

function closeDonorPath(points: readonly (readonly [number, number])[]): readonly TablePoint[] {
  const path = donorPath(points);
  if (path.length === 0) {
    return path;
  }

  return [...path, path[0]];
}

function roundTenth(value: number): number {
  return Math.round(value * 10) / 10;
}

export const VPW_OUTER_BOUNDARY_PATH = closeDonorPath(WALL_263_POINTS);
export const VPW_LEFT_UPPER_GUIDE_PATH = donorPath(WALL_268_POINTS);
export const VPW_RIGHT_UPPER_GUIDE_PATH = donorPath(WALL_264_POINTS);
export const VPW_LEFT_OUTLANE_PATH = donorPath(WALL_76_POINTS);
export const VPW_LEFT_INLANE_PATH = donorPath(WALL_016_POINTS);
export const VPW_RIGHT_INLANE_PATH = donorPath(WALL_015_POINTS);
export const VPW_RIGHT_OUTLANE_PATH = donorPath(WALL_234_POINTS);
export const VPW_LEFT_DRAIN_PATH = donorPath(WALL_013_POINTS);
export const VPW_RIGHT_DRAIN_PATH = donorPath(WALL_021_POINTS);
export const VPW_SHOOTER_OUTER_PATH = closeDonorPath(WALL_95_POINTS);
export const VPW_SHOOTER_DIVIDER_PATH = closeDonorPath(WALL_34_POINTS);

export const VPW_LEFT_SLING_TRIANGLE = Object.freeze([
  donorPoint(316.74026, 1485.6082),
  donorPoint(379.1071, 1663.5806),
  donorPoint(365.39246, 1667.9783),
] as const);

export const VPW_RIGHT_SLING_TRIANGLE = Object.freeze([
  donorPoint(812.0981, 1484.1681),
  donorPoint(807.8043, 1496.3696),
  donorPoint(744.2882, 1676.8601),
] as const);

export const VPW_FLIPPER_GEOMETRY = Object.freeze({
  length: roundTenth(115 * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
  thickness: roundTenth(20 * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
});

export const VPW_SHOOTER_LANE_BOUNDS = Object.freeze({
  minX: roundTenth(976 * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
  maxX: roundTenth(1057 * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
  minY: roundTenth(22.5 * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
  maxY: roundTenth(1948 * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
});

export const VPW_FLIPPER_PIVOTS = Object.freeze({
  left: donorPoint(405.96786, 1833.0863),
  right: donorPoint(724.0889, 1832.9792),
});

export const VPW_LOWER_SWITCH_CENTERS = Object.freeze({
  leftInlane: donorPoint(255.11618, 1585.1604),
  leftOutlane: donorPoint(180.13579, 1723.3805),
  rightInlane: donorPoint(871.65485, 1584.7524),
  rightOutlane: donorPoint(939.325, 1652.8694),
});

export const VPW_SHOOTER_SENSOR_CENTER = donorPoint(1028.5228, 1884.67);
export const VPW_PLUNGER_ROLLOVER_CENTER = donorPoint(1032.7303, 1890.2291);

export const VPW_GATE_CENTERS = Object.freeze({
  rightReturn: donorPoint(722.30853, 818.7679),
  leftRamp: donorPoint(402.23004, 630.5573),
});

export const VPW_GATE_SPECS = Object.freeze({
  rightReturn: Object.freeze({
    center: donorPoint(722.30853, 818.7679),
    width: roundTenth(100 * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
    height: roundTenth(50 * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
    rotationDeg: 14,
  }),
  leftRamp: Object.freeze({
    center: donorPoint(402.23004, 630.5573),
    width: roundTenth(100 * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
    height: roundTenth(50 * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
    rotationDeg: -16.5,
  }),
});

export const VPW_BUMPER_CENTERS = Object.freeze({
  left: donorPoint(390.9, 359.6),
  top: donorPoint(550.8, 479.8),
  right: donorPoint(711.9, 369.9),
});
