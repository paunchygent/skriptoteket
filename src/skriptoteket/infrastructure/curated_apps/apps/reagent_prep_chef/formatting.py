from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def quantize_decimal(value: Decimal, *, places: int) -> Decimal:
    quantum = Decimal(1).scaleb(-places)
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def format_decimal(value: Decimal, *, places: int) -> str:
    quantized = quantize_decimal(value, places=places)
    text = format(quantized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text
