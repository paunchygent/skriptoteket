from __future__ import annotations

# =========================
# Constants
# =========================

PROFILE_STANDARD = "standard"
PROFILE_PRINT_BW = "print_bw"
PROFILE_PRINT_COLOR = "print_color"

SCOPE_FIRST = "first"
SCOPE_ALL = "all"


def profile_label(profile: str) -> str:
    return {
        PROFILE_STANDARD: "Standard",
        PROFILE_PRINT_BW: "Print (svartvit)",
        PROFILE_PRINT_COLOR: "Print (färg)",
    }.get(profile, profile)


def profile_desc(profile: str) -> str:
    return {
        PROFILE_STANDARD: "Modern standardstil med tydliga rubriker.",
        PROFILE_PRINT_BW: "Utskriftsvänlig typografi utan färg (svart).",
        PROFILE_PRINT_COLOR: "Utskriftsvänlig typografi med diskreta färgaccenter i rubriker.",
    }.get(profile, "")
