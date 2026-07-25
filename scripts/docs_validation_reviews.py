"""Review-document shape, target, and identifier validation."""

from __future__ import annotations

import re
from pathlib import Path

from scripts.docs_validation_types import (
    FRONTMATTER_RE,
    Violation,
    YamlMapping,
    normalize_path,
    string_list,
)

EPIC_ID_RE = re.compile(r"^EPIC-\d{2}$")
STORY_ID_RE = re.compile(r"^ST-\d{2}-\d{2}$")
PR_ID_RE = re.compile(r"^PR-\d{4}$")
REVIEW_REQUIRED_SECTIONS = [
    "TL;DR",
    "Problem Statement",
    "Proposed Solution",
    "Artifacts to Review",
    "Key Decisions",
    "Review Checklist",
    "Review Feedback",
    "Changes Made",
]
REVIEW_PLACEHOLDER_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"@\[(?:reviewer-name)\]"),
        "Review feedback still contains the placeholder reviewer.",
    ),
    (re.compile(r"\bYYYY-MM-DD\b"), "Review doc still contains the placeholder date YYYY-MM-DD."),
    (
        re.compile(r"\[pending \| approved \| changes_requested \| rejected\]"),
        "Review feedback still contains the placeholder verdict options.",
    ),
    (
        re.compile(r'\[List specific changes needed, or "None" if approved\]'),
        "Review feedback still contains the placeholder required-changes prompt.",
    ),
    (
        re.compile(r"\[Non-blocking recommendations\]"),
        "Review feedback still contains the placeholder suggestions prompt.",
    ),
    (
        re.compile(r"\[Author fills this in after addressing feedback\]"),
        "Changes Made still contains the placeholder author note.",
    ),
    (
        re.compile(r"\[What changed\]"),
        "Changes Made still contains the placeholder change description.",
    ),
    (
        re.compile(r"\bDecision\s+[123]\b"),
        "Review doc still contains generic Decision 1/2/3 placeholders.",
    ),
]
GRANDFATHERED_DUPLICATE_PR_IDS = {"PR-0195"}


def _body_without_fenced_code(text: str) -> str:
    match = FRONTMATTER_RE.match(text)
    body = text[match.end() :] if match else text

    lines: list[str] = []
    in_fenced_block = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_fenced_block = not in_fenced_block
            continue
        if not in_fenced_block:
            lines.append(line)
    return "\n".join(lines)


def _review_headings(body: str) -> list[str]:
    headings: list[str] = []
    for line in body.splitlines():
        match = re.match(r"^##\s+(.*\S)\s*$", line)
        if match:
            headings.append(match.group(1).strip())
    return headings


def validate_review_shape(path: Path, text: str) -> list[Violation]:
    """Validate required review sections and reject unresolved placeholders."""
    violations: list[Violation] = []
    normalized = normalize_path(path)
    body = _body_without_fenced_code(text)
    headings = [heading.lower() for heading in _review_headings(body)]

    search_start = 0
    for required in REVIEW_REQUIRED_SECTIONS:
        required_lower = required.lower()
        found_index = None
        for index in range(search_start, len(headings)):
            if headings[index] == required_lower:
                found_index = index
                break
        if found_index is None:
            violations.append(
                Violation(normalized, f"Review doc missing required section heading: '{required}'.")
            )
            continue
        search_start = found_index + 1

    for pattern, message in REVIEW_PLACEHOLDER_PATTERNS:
        if pattern.search(body):
            violations.append(Violation(normalized, message))

    return violations


def validate_review_targets(
    paths: list[Path],
    known_docs: dict[str, tuple[Path, YamlMapping]],
) -> list[Violation]:
    """Validate review primary-target ownership and referenced backlog items."""
    violations: list[Violation] = []
    known_ids = {
        str(frontmatter["id"])
        for _, frontmatter in known_docs.values()
        if isinstance(frontmatter.get("id"), str)
    }

    for path in paths:
        normalized = normalize_path(path)
        known_doc = known_docs.get(normalized)
        if known_doc is None:
            continue

        _, frontmatter = known_doc
        if frontmatter.get("type") != "review":
            continue

        review_id = frontmatter.get("id")
        if not isinstance(review_id, str):
            continue

        linked_epic = frontmatter.get("epic")
        if linked_epic is not None and not isinstance(linked_epic, str):
            violations.append(Violation(normalized, "Frontmatter 'epic' must be a string."))
            linked_epic = None

        linked_stories = string_list(frontmatter.get("stories"))
        if linked_stories is None:
            violations.append(
                Violation(normalized, "Frontmatter 'stories' must be a list of strings.")
            )
            linked_stories = []

        linked_prs = string_list(frontmatter.get("prs"))
        if linked_prs is None:
            violations.append(Violation(normalized, "Frontmatter 'prs' must be a list of strings."))
            linked_prs = []

        linked_adrs = string_list(frontmatter.get("adrs"))
        if linked_adrs is None:
            violations.append(
                Violation(normalized, "Frontmatter 'adrs' must be a list of strings.")
            )

        if not linked_epic and not linked_stories and not linked_prs:
            violations.append(
                Violation(
                    normalized,
                    "Review must target at least one backlog item via 'epic', 'stories', or 'prs'.",
                )
            )
            continue

        if linked_epic:
            if EPIC_ID_RE.match(linked_epic) is None:
                violations.append(Violation(normalized, f"Review epic id invalid: '{linked_epic}'"))
            elif linked_epic not in known_ids:
                violations.append(
                    Violation(normalized, f"Review epic '{linked_epic}' does not exist.")
                )
            expected_id = f"REV-{linked_epic}"
            if review_id != expected_id:
                violations.append(
                    Violation(
                        normalized,
                        f"Review id must match targeted epic: expected '{expected_id}'.",
                    )
                )
            continue

        if linked_stories:
            for story_id in linked_stories:
                if STORY_ID_RE.match(story_id) is None:
                    violations.append(
                        Violation(normalized, f"Review story id invalid: '{story_id}'")
                    )
                elif story_id not in known_ids:
                    violations.append(
                        Violation(normalized, f"Review story '{story_id}' does not exist.")
                    )
            expected_id = f"REV-{linked_stories[0]}"
            if review_id != expected_id:
                violations.append(
                    Violation(
                        normalized,
                        f"Review id must match the first targeted story: expected '{expected_id}'.",
                    )
                )
            continue

        for pr_id in linked_prs:
            if PR_ID_RE.match(pr_id) is None:
                violations.append(Violation(normalized, f"Review PR id invalid: '{pr_id}'"))
            elif pr_id not in known_ids:
                violations.append(Violation(normalized, f"Review PR '{pr_id}' does not exist."))
        expected_id = f"REV-{linked_prs[0]}"
        if review_id != expected_id:
            violations.append(
                Violation(
                    normalized,
                    f"Review id must match the first targeted PR: expected '{expected_id}'.",
                )
            )

    return violations


def validate_unique_frontmatter_ids(
    known_docs: dict[str, tuple[Path, YamlMapping]],
) -> list[Violation]:
    """Validate that non-canceled PR docs do not introduce duplicate ids."""
    violations: list[Violation] = []
    paths_by_id: dict[str, list[str]] = {}
    for normalized, (_, frontmatter) in known_docs.items():
        doc_id = frontmatter.get("id")
        if not isinstance(doc_id, str):
            continue
        if frontmatter.get("type") != "pr":
            continue
        if doc_id in GRANDFATHERED_DUPLICATE_PR_IDS:
            continue
        if frontmatter.get("status") == "canceled":
            continue
        paths_by_id.setdefault(doc_id, []).append(normalized)

    for doc_id, normalized_paths in sorted(paths_by_id.items()):
        if len(normalized_paths) <= 1:
            continue
        joined_paths = ", ".join(sorted(normalized_paths))
        for normalized in normalized_paths:
            violations.append(
                Violation(
                    normalized,
                    f"Duplicate active frontmatter id '{doc_id}' also appears in: {joined_paths}",
                )
            )

    return violations
