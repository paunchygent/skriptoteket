/**
 * compilePinballTable regression-suite entrypoint for Flunk-Out Frenzy.
 *
 * The concrete regression cases live in smaller imported modules so targeted
 * runs can keep using this path without violating the file-size budget.
 */

import "./compilePinballTable.donorGeometry.spec-impl";
import "./compilePinballTable.validation.spec-impl";
