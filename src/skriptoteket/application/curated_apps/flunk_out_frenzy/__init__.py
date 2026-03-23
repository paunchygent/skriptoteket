"""Application handlers for the Flunk-Out Frenzy curated app."""

from .bootstrap import (
    FLUNK_OUT_FRENZY_RULESET_ID,
    FlunkOutFrenzyBootstrapResult,
    FlunkOutFrenzyFeatureFlags,
    GetFlunkOutFrenzyBootstrapHandler,
)

__all__ = [
    "FLUNK_OUT_FRENZY_RULESET_ID",
    "FlunkOutFrenzyBootstrapResult",
    "FlunkOutFrenzyFeatureFlags",
    "GetFlunkOutFrenzyBootstrapHandler",
]
