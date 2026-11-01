"""Unit tests for the Klassrumskartan share renderer theme palettes.

Purpose:
    Pin the Ljust, Midnatt and Bläck share palettes to the huleedu design
    tokens, prove the print block forces Ljust, and keep colour literals out
    of the scene and group share CSS.

Relationships:
    - Exercises `SHARE_BASE_CSS`, `SEATING_SHARE_CSS` and `GROUPING_SHARE_CSS`.
    - Covers the share palette contract for the PR-0274 theme work.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_group_renderer import (
    GROUPING_SHARE_CSS,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_renderer import (
    GROUPING_SHARE_RENDERER_VERSION,
    SEATING_SHARE_RENDERER_VERSION,
    SHARE_BASE_CSS,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_scene_renderer import (
    SEATING_SHARE_CSS,
)

_DESIGN_TOKENS_PATH = (
    Path(__file__).resolve().parents[6]
    / "src/skriptoteket/web/static/css/huleedu-design-tokens.css"
)

# Each share variable mirrors one design token; the palette tests pin the
# rendered values to the token values in Ljust, Midnatt and Bläck.
_SHARE_VARIABLE_TOKENS = {
    "--canvas": "--huleedu-paper",
    "--surface": "--huleedu-surface-content",
    "--panel": "--huleedu-panel",
    "--on-strong": "--button-primary-text",
    "--canvas-50": "--huleedu-canvas-50",
    "--navy": "--huleedu-navy",
    "--navy-05": "--huleedu-navy-05",
    "--navy-10": "--huleedu-navy-10",
    "--navy-15": "--huleedu-navy-15",
    "--navy-20": "--huleedu-navy-20",
    "--navy-30": "--huleedu-navy-30",
    "--navy-40": "--huleedu-navy-40",
    "--navy-50": "--huleedu-navy-50",
    "--navy-60": "--huleedu-navy-60",
    "--navy-70": "--huleedu-navy-70",
    "--navy-80": "--huleedu-navy-80",
}


@pytest.mark.unit
def test_share_renderer_versions_are_bumped_for_the_theme_palettes() -> None:
    assert GROUPING_SHARE_RENDERER_VERSION == "klassrumskartan-share-renderer-v2"
    assert SEATING_SHARE_RENDERER_VERSION == "klassrumskartan-seating-share-renderer-v3"


@pytest.mark.unit
def test_share_palettes_match_the_design_token_themes() -> None:
    tokens_css = _DESIGN_TOKENS_PATH.read_text(encoding="utf-8")
    for theme in ("light", "midnight", "dark"):
        share_palette = _palette(SHARE_BASE_CSS, theme=theme)
        token_palette = _palette(tokens_css, theme=theme)
        for share_name, token_name in _SHARE_VARIABLE_TOKENS.items():
            assert share_name in share_palette, f"{theme}: missing share var {share_name}"
            assert token_name in token_palette, f"{theme}: missing token {token_name}"
            share_value = _canonical(_resolve_value(share_palette[share_name], share_palette))
            token_value = _canonical(_resolve_value(token_palette[token_name], token_palette))
            assert share_value == token_value, (
                f"{theme}: {share_name}={share_value} != {token_name}={token_value}"
            )


@pytest.mark.unit
def test_share_system_theme_on_a_dark_device_uses_the_midnatt_palette() -> None:
    midnight_palette = _palette(SHARE_BASE_CSS, theme="midnight")
    system_palette = _palette(SHARE_BASE_CSS, theme="system")
    for share_name in _SHARE_VARIABLE_TOKENS:
        assert share_name in system_palette, f"system: missing share var {share_name}"
        assert _canonical(_resolve_value(system_palette[share_name], system_palette)) == (
            _canonical(_resolve_value(midnight_palette[share_name], midnight_palette))
        )


@pytest.mark.unit
def test_share_print_block_forces_the_ljust_palette() -> None:
    light_palette = _palette(SHARE_BASE_CSS, theme="light")
    print_declarations: dict[str, str] = {}
    for media, selector, declarations in _css_rules(SHARE_BASE_CSS):
        if media == ("print",) and selector.startswith(":root"):
            print_declarations.update(declarations)

    assert print_declarations["color-scheme"] == "light"
    for share_name in _SHARE_VARIABLE_TOKENS:
        assert share_name in print_declarations, f"print: missing share var {share_name}"
        assert _canonical(print_declarations[share_name]) == _canonical(light_palette[share_name])


@pytest.mark.unit
def test_scene_and_group_share_css_hold_no_colour_literals() -> None:
    for css in (SEATING_SHARE_CSS, GROUPING_SHARE_CSS):
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", css)
        assert not re.search(r"\brgba?\(", css)
        assert not re.search(r"\bhsla?\(", css)


def _css_rules(
    css: str, media: tuple[str, ...] = ()
) -> list[tuple[tuple[str, ...], str, dict[str, str]]]:
    """Return (media chain, selector, declarations) for every rule in the sheet."""

    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules: list[tuple[tuple[str, ...], str, dict[str, str]]] = []
    pos = 0
    while pos < len(css):
        brace = css.find("{", pos)
        if brace == -1:
            break
        prelude = css[pos:brace].strip()
        depth = 1
        end = brace + 1
        while depth:
            if css[end] == "{":
                depth += 1
            elif css[end] == "}":
                depth -= 1
            end += 1
        body = css[brace + 1 : end - 1]
        if prelude.startswith("@media"):
            condition = prelude.removeprefix("@media").strip()
            rules.extend(_css_rules(body, media + (condition,)))
        elif not prelude.startswith("@"):
            declarations: dict[str, str] = {}
            for declaration in body.split(";"):
                if ":" not in declaration:
                    continue
                name, value = declaration.split(":", 1)
                declarations[name.strip()] = value.strip()
            for selector in prelude.split(","):
                rules.append((media, selector.strip(), declarations))
        pos = end
    return rules


def _palette(css: str, *, theme: str) -> dict[str, str]:
    """Collect the custom properties one theme applies, in cascade order."""

    palette: dict[str, str] = {}
    for media, selector, declarations in _css_rules(css):
        if media:
            applies = (
                theme == "system"
                and media == ("(prefers-color-scheme: dark)",)
                and (selector == ':root[data-theme="system"]')
            )
        elif theme == "light":
            applies = selector == ":root"
        else:
            applies = selector in {":root", f':root[data-theme="{theme}"]'}
        if applies:
            for name, value in declarations.items():
                if name.startswith("--"):
                    palette[name] = value
    return palette


def _resolve_value(value: str, palette: dict[str, str]) -> str:
    """Expand var() references against the palette until literals remain."""

    seen: set[str] = set()
    while (match := re.search(r"var\((--[\w-]+)\)", value)) is not None:
        name = match.group(1)
        if name in seen or name not in palette:
            break
        seen.add(name)
        value = value[: match.start()] + palette[name] + value[match.end() :]
    return value


def _canonical(value: str) -> str:
    """Normalize a CSS value so numerically equal literals compare equal."""

    collapsed = re.sub(r"\s+", "", value).casefold()
    return re.sub(r"\d*\.\d+|\d+", lambda match: f"{float(match.group(0)):g}", collapsed)
