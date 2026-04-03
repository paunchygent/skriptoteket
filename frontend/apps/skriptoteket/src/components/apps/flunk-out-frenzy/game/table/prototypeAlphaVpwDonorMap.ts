/**
 * VPW donor topology map for the Flunk-Out Frenzy prototype table.
 *
 * The board carriers in this module are traced from the donor table's native
 * drag-point chains instead of a locally simplified redraw. That keeps the
 * visible boundary grammar and the compiled wall carriers aligned to the donor
 * table rather than a hybrid of donor and legacy Flunk-Out geometry.
 */

import type { TablePoint, TablePoint3D } from "./tableDefinitionTypes";
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

const WALL_018_POINTS = [
  [949.00995, 266.17642],
  [949.4456, 129.38327],
  [1003.8749, 129.60924],
  [1003.4484, 265.848],
] as const;

const WALL_019_POINTS = [
  [943.99115, 247.19344],
  [944.3592, 130.0],
  [998.81055, 130.2222],
  [998.4487, 247.23589],
] as const;

const WALL_010_POINTS = [
  [952.82715, 1080.2274],
  [983.1234, 1243.799],
  [1006.4996, 1238.5991],
  [976.2514, 1075.1033],
] as const;

const WALL_011_POINTS = [
  [956.02704, 1267.6265],
  [938.6296, 1363.9829],
  [961.1782, 1368.8137],
  [978.55865, 1272.3873],
] as const;

const WALL_024_POINTS = [
  [843.38727, 1551.7461],
  [841.78827, 1476.1539],
  [838.902, 1555.9504],
  [903.3405, 1556.5917],
  [903.4306, 1477.0256],
  [899.17554, 1551.7462],
] as const;

const WALL_APRON1_POINTS = [
  [1081.0, 1920.5254],
  [1032.1781, 1929.2754],
  [1000.0, 1922.3857],
  [1000.0, 1902.9609],
] as const;

const WALL_APRON2_POINTS = [
  [1000.0, 1829.1067],
  [1000.0, 1759.8445],
  [976.23505, 1760.0652],
] as const;

const WALL_002_POINTS = [
  [722.729, 216.52353],
  [736.5052, 226.41463],
  [702.225, 483.55542],
  [696.3801, 487.87167],
  [699.99817, 492.48013],
  [746.89685, 456.16028],
  [783.5492, 412.09113],
  [805.99866, 367.5025],
  [808.6855, 317.4794],
  [793.6221, 269.6463],
  [764.0724, 235.10744],
  [735.0, 217.0],
  [724.97766, 212.20518],
] as const;

const WALL_017_POINTS = [
  [318.49396, 526.3152],
  [334.28067, 571.67975],
  [362.981, 679.81665],
  [365.39453, 679.1051],
  [335.57343, 571.268],
  [321.91263, 525.2617],
  [321.19647, 524.1929],
  [319.81, 524.0166],
  [318.6381, 524.9268],
] as const;

const RAMP_S001_POINTS = [
  [1031.5, 270.0, 0.0],
  [1031.5, 125.0, 0.0],
] as const;

const RAMP_S002_POINTS = [
  [1031.5, 125.0, 0.0],
  [1031.5, 110.099, 0.0],
  [1027.9177, 86.870674, 0.0],
  [1018.7783, 66.707726, 0.0],
  [997.97107, 47.97677, 0.0],
  [971.5704, 38.113785, 0.0],
  [932.0838, 36.083355, 0.0],
  [901.80316, 36.0, 0.0],
] as const;

const RAMP_S3_POINTS = [
  [1031.5, 1575.0, 0.0],
  [1031.4999, 1227.979, 2.14],
  [1031.5, 813.1283, 0.0],
  [1031.5, 508.25128, 30.0],
  [1031.5, 270.0, 0.0],
] as const;

const RAMP_S4_POINTS = [
  [901.7462, 36.18238, 0.0],
  [606.1428, 36.0, 0.0],
  [394.24762, 38.0, 0.0],
  [372.88232, 42.556362, 0.0],
  [345.28152, 55.037945, 0.0],
  [325.63632, 81.6918, 0.0],
  [319.71494, 112.028015, 0.0],
  [329.68787, 148.58394, 0.0],
  [355.14984, 171.76091, 0.0],
  [386.30734, 181.01797, 0.0],
  [419.5, 178.42093, 0.0],
  [453.25488, 162.049, 0.0],
  [484.43073, 145.14818, -20.0],
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
  rightReceiveMouthOuter:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall018.json",
  rightReceiveMouthInner:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall019.json",
  shooterHandoffUpper:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall010.json",
  shooterHandoffLower:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall011.json",
  rightReturnThroatShield:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall024.json",
  rightUpperInnerMetal:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall002.json",
  leftUpperInnerMetal:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Wall017.json",
  shooterWireVertical:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Ramp.RampS3.json",
  shooterWireMouthConnector:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Ramp.RampS001.json",
  shooterWireTopRight:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Ramp.RampS002.json",
  shooterWireTopArch:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Ramp.RampS4.json",
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
  apron1:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Apron1.json",
  apron2:
    ".artifacts/vpw-rom-example-table-extracted/ROM_Example_Table_VPW/gameitems/Wall.Apron2.json",
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

function donorPath3DWithLinearHeightProfile(
  points: readonly (readonly [number, number])[],
  heightBottom: number,
  heightTop: number,
): readonly TablePoint3D[] {
  if (points.length === 0) {
    return [];
  }

  const scaled = points.map(([x, y]) => donorPoint(x, y));
  const cumulativeDistances: number[] = [0];
  for (let index = 1; index < scaled.length; index += 1) {
    const previous = scaled[index - 1];
    const current = scaled[index];
    const distance = Math.hypot(current.x - previous.x, current.y - previous.y);
    cumulativeDistances[index] = cumulativeDistances[index - 1] + distance;
  }

  const totalDistance = cumulativeDistances[cumulativeDistances.length - 1];
  const bottomZ = scaleDonorLength(heightBottom);
  const topZ = scaleDonorLength(heightTop);

  return scaled.map((point, index) => {
    const t = totalDistance <= 0 ? 0 : cumulativeDistances[index] / totalDistance;
    return {
      x: point.x,
      y: point.y,
      z: roundTenth(bottomZ + (topZ - bottomZ) * t),
    };
  });
}

function path3DWithLinearHeightProfile(
  path: readonly TablePoint[],
  zStart: number,
  zEnd: number,
): readonly TablePoint3D[] {
  if (path.length === 0) {
    return [];
  }

  const cumulativeDistances: number[] = [0];
  for (let index = 1; index < path.length; index += 1) {
    const previous = path[index - 1];
    const current = path[index];
    const distance = Math.hypot(current.x - previous.x, current.y - previous.y);
    cumulativeDistances[index] = cumulativeDistances[index - 1] + distance;
  }

  const totalDistance = cumulativeDistances[cumulativeDistances.length - 1];
  return path.map((point, index) => {
    const t = totalDistance <= 0 ? 0 : cumulativeDistances[index] / totalDistance;
    return {
      x: point.x,
      y: point.y,
      z: roundTenth(zStart + (zEnd - zStart) * t),
    };
  });
}

function mergePath3DSegments(
  segments: readonly (readonly TablePoint3D[])[],
): readonly TablePoint3D[] {
  const merged: TablePoint3D[] = [];
  for (const segment of segments) {
    for (const point of segment) {
      const previous = merged[merged.length - 1];
      if (
        previous
        && Math.abs(previous.x - point.x) < 1e-6
        && Math.abs(previous.y - point.y) < 1e-6
        && Math.abs(previous.z - point.z) < 1e-6
      ) {
        continue;
      }
      merged.push(point);
    }
  }
  return merged;
}

function planarPath(points: readonly (readonly [number, number, number])[]): readonly (readonly [number, number])[] {
  return points.map(([x, y]) => [x, y] as const);
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

export const VPW_OUTER_BOUNDARY_RENDER_PATH = closeDonorPath(WALL_263_POINTS);
// Wall263 in VPW is a composite perimeter item: the left/top cabinet boundary
// and a separate upper-right shooter descent live in the same drag-point list.
// Keep physics ownership explicit by limiting "main" to the left/top cabinet
// shell while launcher-right carriers are represented by dedicated donor walls
// and guides (Wall34/Wall011/Wall010/Wall264 + Wall263 shoulder slice).
export const VPW_OUTER_BOUNDARY_MAIN_PATH = donorPath(WALL_263_POINTS.slice(0, 45));
// Keep only the upper curved descent from Wall263 as a physical guide.
// The lower kinked continuation forms a deterministic pinch against the
// launcher-return chain when represented as thick 2D segments, so it remains
// render-only until the seam supports donor-faithful joined-edge geometry.
export const VPW_OUTER_BOUNDARY_RIGHT_DESCENT_PATH = donorPath(WALL_263_POINTS.slice(45, 55));
// Keep only the donor right-shoulder continuation that guides the lower edge
// of the launcher return path toward Wall010.
// Keep the full donor shoulder continuation from points 54..60 as a continuous
// carrier so the shooter gradient stays closed all the way into the lower
// handoff chain.
// The lower Wall263 continuation toward Wall34 is represented by dedicated
// donor wall solids (Wall011/Wall010 chain + apron carriers) and must not be
// reintroduced as an extra physical rail in the shooter corridor.
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

export const VPW_METAL_RAIL_3D_SPECS = Object.freeze({
  shooterVertical: Object.freeze({
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireVertical,
    path: donorPath3DWithLinearHeightProfile(planarPath(RAMP_S3_POINTS), 0, 180),
    radius: scaleDonorLength(3.5),
    heightBottom: scaleDonorLength(0),
    heightTop: scaleDonorLength(180),
  }),
  shooterMouthConnector: Object.freeze({
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireMouthConnector,
    path: donorPath3DWithLinearHeightProfile(planarPath(RAMP_S001_POINTS), 180, 180),
    radius: scaleDonorLength(3.5),
    heightBottom: scaleDonorLength(180),
    heightTop: scaleDonorLength(180),
  }),
  shooterTopRight: Object.freeze({
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireTopRight,
    path: donorPath3DWithLinearHeightProfile(planarPath(RAMP_S002_POINTS), 180, 180),
    radius: scaleDonorLength(3.5),
    heightBottom: scaleDonorLength(180),
    heightTop: scaleDonorLength(180),
  }),
  shooterTopArch: Object.freeze({
    donorSourceId: PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireTopArch,
    path: donorPath3DWithLinearHeightProfile(planarPath(RAMP_S4_POINTS), 180, 100),
    radius: scaleDonorLength(3.5),
    heightBottom: scaleDonorLength(100),
    heightTop: scaleDonorLength(180),
  }),
});

const VPW_LEFT_UPPER_GUIDE_DESCENT_PATH_3D = path3DWithLinearHeightProfile(
  VPW_LEFT_UPPER_GUIDE_DESCENT_PATH,
  scaleDonorLength(100),
  scaleDonorLength(0),
);

export const VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_DONOR_SOURCES = Object.freeze([
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireVertical,
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireMouthConnector,
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireTopRight,
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireTopArch,
] as const);

export const VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_3D_PATH = mergePath3DSegments([
  VPW_METAL_RAIL_3D_SPECS.shooterVertical.path,
  VPW_METAL_RAIL_3D_SPECS.shooterMouthConnector.path,
  VPW_METAL_RAIL_3D_SPECS.shooterTopRight.path,
  VPW_METAL_RAIL_3D_SPECS.shooterTopArch.path,
]);

export const VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_EXIT_ANCHOR_3D = Object.freeze({
  ...VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_3D_PATH[VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_3D_PATH.length - 1],
});

export const VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_DONOR_SOURCES = Object.freeze([
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.leftUpperGuide,
] as const);

export const VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_3D_PATH = mergePath3DSegments([
  VPW_LEFT_UPPER_GUIDE_DESCENT_PATH_3D,
]);

export const VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_ENTRY_ANCHOR_3D = Object.freeze({
  ...VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_3D_PATH[0],
});

export const VPW_LAUNCH_TRAVEL_ROUTE_ENDPOINT_BRIDGE_DONOR_SOURCES = Object.freeze([
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.shooterWireTopArch,
  PROTOTYPE_ALPHA_VPW_DONOR_SOURCES.leftUpperGuide,
] as const);

export const VPW_LAUNCH_TRAVEL_ROUTE_ENDPOINT_BRIDGE_3D_PATH = Object.freeze([
  VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_EXIT_ANCHOR_3D,
  VPW_LAUNCH_TRAVEL_ROUTE_DESCENT_ENTRY_ANCHOR_3D,
] as const);

export const VPW_FULL_BOARD_PATH_TARGET = Object.freeze({
  perimeterAndLanes: Object.freeze({
    outerBoundary: VPW_OUTER_BOUNDARY_RENDER_PATH,
    leftUpperGuide: VPW_LEFT_UPPER_GUIDE_PATH,
    rightUpperGuide: VPW_RIGHT_UPPER_GUIDE_PATH,
    leftOutlane: VPW_LEFT_OUTLANE_PATH,
    leftInlane: VPW_LEFT_INLANE_PATH,
    rightInlane: VPW_RIGHT_INLANE_PATH,
    rightOutlane: VPW_RIGHT_OUTLANE_PATH,
    leftDrain: VPW_LEFT_DRAIN_PATH,
    rightDrain: VPW_RIGHT_DRAIN_PATH,
  }),
  shooterAndReceiveChain: Object.freeze({
    shooterOuter: VPW_SHOOTER_OUTER_POLYGON,
    shooterDivider: VPW_SHOOTER_DIVIDER_POLYGON,
    shooterHandoffUpper: VPW_SHOOTER_HANDOFF_UPPER_POLYGON,
    shooterHandoffLower: VPW_SHOOTER_HANDOFF_LOWER_POLYGON,
    rightReceiveOuter: VPW_RIGHT_RECEIVE_MOUTH_OUTER_POLYGON,
    rightReceiveInner: VPW_RIGHT_RECEIVE_MOUTH_INNER_POLYGON,
    apron1: VPW_APRON_1_POLYGON,
    apron2: VPW_APRON_2_POLYGON,
    wall263Shoulder: VPW_OUTER_BOUNDARY_SHOOTER_CORRIDOR_PATH,
  }),
  overheadMetalRails: Object.freeze({
    shooterVertical: VPW_METAL_RAIL_3D_SPECS.shooterVertical.path,
    shooterMouthConnector: VPW_METAL_RAIL_3D_SPECS.shooterMouthConnector.path,
    shooterTopRight: VPW_METAL_RAIL_3D_SPECS.shooterTopRight.path,
    shooterTopArch: VPW_METAL_RAIL_3D_SPECS.shooterTopArch.path,
    rightUpperInnerMetal: VPW_RIGHT_UPPER_INNER_METAL_PATH,
    leftUpperInnerMetal: VPW_LEFT_UPPER_INNER_METAL_PATH,
  }),
});

export const VPW_GATE_CENTERS = Object.freeze({
  rightReturn: donorPoint(722.30853, 818.7679),
});

export const VPW_GATE_SPECS = Object.freeze({
  rightReturn: Object.freeze({
    center: donorPoint(722.30853, 818.7679),
    width: roundTenth(100 * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
    height: roundTenth(50 * PROTOTYPE_ALPHA_VPW_DONOR_SCALE),
    rotationDeg: 14,
  }),
});

export const VPW_BUMPER_CENTERS = Object.freeze({
  left: donorPoint(390.9, 359.6),
  top: donorPoint(550.8, 479.8),
  right: donorPoint(711.9, 369.9),
});
