from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HazardEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    display_name: str
    hazard_codes: list[str] = Field(default_factory=list)
    ppe: list[str] = Field(default_factory=list)
    disposal: str | None = None
    notes: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)

    @field_validator("key", "display_name")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value is required")
        return normalized

    @field_validator("hazard_codes", "ppe", "notes", "aliases")
    @classmethod
    def _normalize_text_list(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item and item.strip()]
        return normalized

    @field_validator("disposal")
    @classmethod
    def _normalize_disposal(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PrepRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chemical_formula: str = Field(..., min_length=1)
    target_molarity: Decimal = Field(..., gt=0)
    vol_per_group_ml: Decimal = Field(..., gt=0)
    student_count: int = Field(..., gt=0)
    students_per_group: int = Field(2, gt=0)
    safety_factor: Decimal = Field(Decimal("0.10"), ge=0, le=Decimal("0.50"))
    source_type: Literal["solid", "liquid_stock"] = "solid"
    stock_molarity: Decimal | None = None
    solute_purity: Decimal = Field(Decimal("1.0"), gt=0, le=1)

    @field_validator("chemical_formula")
    @classmethod
    def _strip_formula(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("chemical_formula is required")
        return normalized

    @model_validator(mode="after")
    def _validate_stock_logic(self) -> "PrepRequest":
        if self.source_type != "liquid_stock":
            return self
        if self.stock_molarity is None:
            raise ValueError("stock_molarity is required when source_type=liquid_stock")
        if self.stock_molarity <= self.target_molarity:
            raise ValueError("stock_molarity must be greater than target_molarity")
        return self
