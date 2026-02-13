from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def _added_lines(diff_text: str) -> list[str]:
    lines: list[str] = []
    for line in diff_text.splitlines():
        if not line.startswith("+"):
            continue
        if line.startswith("+++"):
            continue
        lines.append(line[1:])
    return lines


def _diff_headers(diff_text: str) -> list[str]:
    headers: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            headers.append(line.strip())
    return headers


def validate_review(text: str) -> ValidationResult:
    result = ValidationResult()
    stripped = text.strip()
    if not stripped:
        result.errors.append("Review output is empty.")
        return result

    if not stripped.startswith("SUMMARY:"):
        result.errors.append("Review output must start with 'SUMMARY:'.")

    for section in ("SCORECARD:", "FINDINGS:", "FIX PLAN:"):
        if section not in text:
            result.errors.append(f"Missing section: {section}")

    for label in (
        "correctness:",
        "security:",
        "performance:",
        "maintainability:",
        "platform_fit:",
        "tests:",
    ):
        if label not in text:
            result.errors.append(f"Missing score line: {label}")

    must_mentions = {
        "network restriction": ["nätverk", "network", "requests", "http"],
        "output_dir / absolute path": ["output_dir", "/tmp", "absolut", "absolute path"],
        "html_sandboxed vs html": ["html_sandboxed", "html"],
        "next_actions list": ["next_actions", "lista", "list"],
        "env parsing": ["os.environ", "SKRIPTOTEKET_INPUTS", "SKRIPTOTEKET_INPUT_MANIFEST"],
        "toolkit helpers": ["skriptoteket_toolkit", "read_inputs", "list_input_files"],
    }

    for label, needles in must_mentions.items():
        if not _contains_any(text, needles):
            result.errors.append(f"Review missing mention of {label}.")

    return result


def validate_diff(
    text: str,
    *,
    require_tool: bool = True,
    require_schema: bool = True,
    allowed_headers: list[str] | None = None,
    required_first_header: str | None = None,
) -> ValidationResult:
    result = ValidationResult()
    stripped = text.strip()
    if not stripped:
        result.errors.append("Diff output is empty.")
        return result

    if stripped == "CANNOT_COMPLY":
        result.errors.append("Diff output is CANNOT_COMPLY.")
        return result

    if required_first_header and not stripped.startswith(required_first_header):
        result.errors.append(f"Diff must start with header: {required_first_header}")

    headers = _diff_headers(text)
    if allowed_headers is not None:
        for header in headers:
            if header not in allowed_headers:
                result.errors.append(f"Unexpected diff header: {header}")

    if require_tool and "diff --git a/tool.py b/tool.py" not in text:
        result.errors.append("Missing diff header: diff --git a/tool.py b/tool.py")
    if require_schema and "diff --git a/input_schema.json b/input_schema.json" not in text:
        result.errors.append(
            "Missing diff header: diff --git a/input_schema.json b/input_schema.json"
        )
    if require_schema and "diff --git a/usage_instructions.md b/usage_instructions.md" not in text:
        result.errors.append(
            "Missing diff header: diff --git a/usage_instructions.md b/usage_instructions.md"
        )

    added = "\n".join(_added_lines(text))

    forbidden_added = [
        "requests.get(",
        "http://",
        "https://",
        "os.environ",
        "SKRIPTOTEKET_INPUTS",
        "SKRIPTOTEKET_INPUT_MANIFEST",
        "/tmp",
    ]
    for token in forbidden_added:
        if token in added:
            result.errors.append(f"Forbidden token in added lines: {token}")

    if require_tool:
        required_added = {
            "skriptoteket_toolkit import": ["skriptoteket_toolkit"],
            "read_inputs usage": ["read_inputs("],
            "list_input_files usage": ["list_input_files("],
            "get_action_parts usage": ["get_action_parts("],
            "save_as_pdf helper": ["save_as_pdf("],
            "pdf_helper import": ["pdf_helper"],
            "html_sandboxed output": ['"kind": "html_sandboxed"', "'kind': 'html_sandboxed'"],
        }
        for label, needles in required_added.items():
            if not _contains_any(added, list(needles)):
                result.errors.append(f"Missing required addition: {label}")

    if require_tool and ('"kind": "html"' in added or "'kind': 'html'" in added):
        result.errors.append("Added html output kind instead of html_sandboxed.")

    if require_tool and "next_actions = [" not in added and '"next_actions": [' not in added:
        result.errors.append("next_actions must be a list in added lines.")

    if require_schema:
        schema_checks = [
            '"kind": "file"',
            '"accept"',
            '"min"',
            '"max"',
        ]
        for token in schema_checks:
            if token not in added:
                result.errors.append(f"input_schema missing required token: {token}")

    if require_schema:
        if not _contains_any(added, ["CSV", "csv"]):
            result.warnings.append("No CSV mention found in added usage instructions.")
        if not _contains_any(added, ["PDF", "pdf"]):
            result.warnings.append("No PDF mention found in added usage instructions.")

    return result
