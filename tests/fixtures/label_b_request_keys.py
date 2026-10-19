"""Capture-time request keys of the recorded second-pass labeler (``label_b``) replies.

Each ``label_b_<qid>.json`` recording carries the request key it answered in
``label_b_<qid>.request.txt``, followed by one final newline. A replay serves a ``label_b``
recording only to a request whose text ends with that key, so a changed labeler request stays
unmatched instead of receiving a stale reply.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from pathlib import Path


def label_b_request_keys(recordings: Path) -> dict[str, str]:
    """Each label_b recording's capture-time request key, read from its sidecar file."""
    replies = {p.stem for p in recordings.glob("label_b_*.json")}
    keys = {p.name.removesuffix(".request.txt") for p in recordings.glob("label_b_*.request.txt")}
    missing = sorted(replies - keys)
    extra = sorted(keys - replies)
    assert replies == keys, (
        f"{recordings}: label_b request keys must match their recordings; "
        f"missing sidecars for {missing}, unexpected sidecars for {extra}"
    )
    return {
        name: (recordings / f"{name}.request.txt").read_text().removesuffix("\n")
        for name in sorted(replies)
    }


def matching_label_b(keys: Mapping[str, str], text: str, served: Collection[str]) -> str | None:
    """The first unused label_b recording whose capture-time key ends the request ``text``."""
    return next(
        (
            name
            for name, key in keys.items()
            if name not in served and text.endswith(f"### Question q1\n{key}")
        ),
        None,
    )
