from __future__ import annotations

import pytest

from skriptoteket.infrastructure.editor.unified_diff_applier import SubprocessUnifiedDiffApplier


@pytest.mark.unit
def test_prepare_strips_code_fences_and_injects_headers() -> None:
    applier = SubprocessUnifiedDiffApplier()

    prepared = applier.prepare(
        target_file="tool.py",
        unified_diff="""
            ```diff
            @@ -1 +1 @@
            -print("hi")
            +print("hello")
            ```
        """,
    )

    assert prepared.target_file == "tool.py"
    assert prepared.normalized_diff.startswith("--- a/tool.py\n+++ b/tool.py\n@@")
    assert "stripped_code_fences" in prepared.normalizations_applied
    assert "stripped_leading_indentation" in prepared.normalizations_applied
    assert "synthesized_file_headers" in prepared.normalizations_applied


@pytest.mark.unit
def test_prepare_rejects_multi_file_diff() -> None:
    applier = SubprocessUnifiedDiffApplier()

    with pytest.raises(ValueError):
        applier.prepare(
            target_file="tool.py",
            unified_diff="""
                --- a/tool.py
                +++ b/tool.py
                @@ -1 +1 @@
                -print("hi")
                +print("hello")
                --- a/other.py
                +++ b/other.py
                @@ -1 +1 @@
                -print("x")
                +print("y")
            """,
        )


@pytest.mark.unit
def test_apply_uses_whitespace_stage() -> None:
    applier = SubprocessUnifiedDiffApplier()

    base_text = "def foo():\n\treturn 1\n"
    prepared = applier.prepare(
        target_file="tool.py",
        unified_diff="""
            --- a/tool.py
            +++ b/tool.py
            @@ -1,2 +1,2 @@
             def foo():
            -    return 1
            +    return 2
        """,
    )

    result = applier.apply(
        target_file="tool.py",
        base_text=base_text,
        prepared=prepared,
        max_fuzz=2,
        max_offset_lines=50,
        enable_whitespace_stage=True,
    )

    assert result.ok is True
    assert result.meta is not None
    assert result.meta.whitespace_ignored is True
    assert result.next_text == "def foo():\n    return 2\n"


@pytest.mark.unit
def test_prepare_repairs_hunk_header_counts() -> None:
    applier = SubprocessUnifiedDiffApplier()

    prepared = applier.prepare(
        target_file="tool.py",
        unified_diff="""
            --- a/tool.py
            +++ b/tool.py
            @@ -1,2 +1,2 @@
            -print("hi")
            +print("hello")
        """,
    )

    assert "rewrote_hunk_header_counts" in prepared.normalizations_applied
    assert "@@ -1,1 +1,1 @@" in prepared.normalized_diff

    result = applier.apply(
        target_file="tool.py",
        base_text='print("hi")\n',
        prepared=prepared,
        max_fuzz=2,
        max_offset_lines=50,
        enable_whitespace_stage=True,
    )

    assert result.ok is True
    assert result.next_text == 'print("hello")\n'


@pytest.mark.unit
def test_prepare_rejects_malformed_hunk_body_lines() -> None:
    applier = SubprocessUnifiedDiffApplier()

    with pytest.raises(ValueError, match="Diffen är felaktigt formaterad"):
        applier.prepare(
            target_file="tool.py",
            unified_diff="""
                --- a/tool.py
                +++ b/tool.py
                @@ -1,1 +1,1 @@
                print("hello")
            """,
        )
