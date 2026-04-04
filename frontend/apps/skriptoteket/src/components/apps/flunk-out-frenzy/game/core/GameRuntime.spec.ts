/**
 * GameRuntime regression-suite entrypoint for Flunk-Out Frenzy.
 *
 * The runtime cases live in smaller imported modules so this stable test path
 * can remain in use while the suite stays within the file-size budget.
 */

import "./GameRuntime.lifecycle.spec-impl";
import "./GameRuntime.telemetry.spec-impl";
