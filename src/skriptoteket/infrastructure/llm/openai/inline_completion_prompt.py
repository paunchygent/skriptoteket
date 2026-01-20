from __future__ import annotations


def _language_for_active_file(active_file: str) -> str | None:
    normalized = (active_file or "").strip().lower()
    if normalized.endswith(".py"):
        return "python"
    if normalized.endswith(".json"):
        return "json"
    if normalized.endswith(".md"):
        return "markdown"
    if normalized.endswith(".txt"):
        return "text"
    return None


def build_delimited_inline_completion_prompt(
    *, prefix: str, suffix: str, active_file: str | None = None
) -> str:
    """Build a prefix/suffix prompt suitable for insert-only inline completions.

    Uses hard tags so the model can reliably distinguish context from insertion text.
    """

    header_parts: list[str] = []
    if active_file:
        header_parts.append(f"<FILE>{active_file}</FILE>")
        language = _language_for_active_file(active_file)
        if language:
            header_parts.append(f"<LANGUAGE>{language}</LANGUAGE>")

    header = "\n".join(header_parts)
    if header:
        header += "\n\n"

    return (
        header + "<PREFIX>\n"
        f"{prefix}\n"
        "</PREFIX>\n\n"
        "<SUFFIX>\n"
        f"{suffix}\n"
        "</SUFFIX>\n\n"
        "<CURSOR>\n"
        "Return only the insertion text."
    )
