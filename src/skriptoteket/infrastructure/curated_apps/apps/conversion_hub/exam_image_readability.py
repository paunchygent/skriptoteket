"""Shared Pillow readability probe for embedded exam images.

Purpose:
    One implementation of "this payload fully decodes, not just its header".
    The DOCX picture normalizer needs the probed format and first-frame size;
    the DigiExam embedded-asset extractor needs the boolean through a domain
    protocol. Both read from here so the Pillow behavior cannot drift apart.

Relationships:
    Used by ``exam_workspace_docx_picture._probe``; implemented for the domain
    by ``PillowEmbeddedImageDecodability`` below.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image

from skriptoteket.protocols.exam_conversion import EmbeddedImageDecodabilityProtocol


@dataclass(frozen=True)
class ProbedImage:
    """A payload's actual Pillow format and first-frame size, not its declared MIME."""

    format: str
    width: int
    height: int
    animated: bool


def probe_image_payload(payload: bytes) -> ProbedImage | None:
    """A payload's actual Pillow format and first-frame size, or None when unreadable."""
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.load()
            return ProbedImage(
                format=image.format or "",
                width=image.width,
                height=image.height,
                animated=bool(getattr(image, "is_animated", False)),
            )
    except (OSError, ValueError, Image.DecompressionBombError):
        return None


class PillowEmbeddedImageDecodability(EmbeddedImageDecodabilityProtocol):
    """Pillow-backed full-decode check for embedded image payloads."""

    def is_fully_decodable(self, payload: bytes) -> bool:
        """True when the full image stream decodes, not just its header."""
        return probe_image_payload(payload) is not None
