/**
 * Compiled prototype-alpha table for Flunk-Out Frenzy.
 *
 * The runtime, physics world, and board renderer all consume the same compiled
 * pinball-table plan rather than a legacy wall-list adapter.
 */

import { compilePinballTable } from "./compilePinballTable";
import { PROTOTYPE_ALPHA_TABLE_SPEC } from "./prototypeAlphaTableSpec";

export const PROTOTYPE_ALPHA_TABLE = compilePinballTable(PROTOTYPE_ALPHA_TABLE_SPEC);

export const PROTOTYPE_ALPHA_LATE_TAGS = PROTOTYPE_ALPHA_TABLE.rollovers.map(
  (rollover) => rollover.tag,
);

export type PrototypeAlphaTable = typeof PROTOTYPE_ALPHA_TABLE;
