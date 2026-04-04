// @vitest-environment node

/**
 * Launcher regression-suite entrypoint for Flunk-Out Frenzy physics world.
 *
 * The detailed behavior and proof cases live in smaller imported modules so
 * targeted runs can keep using this path without breaking the file-size budget.
 */

import "./PhysicsWorld.launcher.behavior.spec-impl";
import "./PhysicsWorld.launcher.proof.spec-impl";
