"""Teacher-preserving delivery digests for conversion-owned document fields."""

import hashlib
import json

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeParagraph
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamHeader


def digest_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def choose_delivered_field[T: (str, tuple[NativeParagraph, ...], NativeExamHeader)](
    current: T,
    proposed: T | None,
    delivered_digest: str | None,
) -> tuple[T, str | None]:
    """Replace only the value still identical to the previously delivered revision."""
    if proposed is None:
        return current, delivered_digest
    current_json = (
        [paragraph.model_dump(mode="json") for paragraph in current]
        if isinstance(current, tuple)
        else current.model_dump(mode="json")
        if isinstance(current, NativeExamHeader)
        else current
    )
    if digest_json(current_json) != delivered_digest:
        return current, delivered_digest
    proposed_json = (
        [paragraph.model_dump(mode="json") for paragraph in proposed]
        if isinstance(proposed, tuple)
        else proposed.model_dump(mode="json")
        if isinstance(proposed, NativeExamHeader)
        else proposed
    )
    return proposed, digest_json(proposed_json)
