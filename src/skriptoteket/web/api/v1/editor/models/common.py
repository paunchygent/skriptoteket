from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skriptoteket.protocols.llm import VirtualFileId


class EditorEditOpsSelection(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    start: int = Field(alias="from", ge=0)
    end: int = Field(alias="to", ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> "EditorEditOpsSelection":
        if self.end < self.start:
            raise ValueError("Selection end must be >= start")
        return self


class EditorEditOpsCursor(BaseModel):
    model_config = ConfigDict(frozen=True)

    pos: int = Field(ge=0)


class EditorVirtualFiles(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    tool_py: str = Field(alias="tool.py")
    entrypoint_txt: str = Field(alias="entrypoint.txt")
    settings_schema_json: str = Field(alias="settings_schema.json")
    input_schema_json: str = Field(alias="input_schema.json")
    usage_instructions_md: str = Field(alias="usage_instructions.md")

    def as_map(self) -> dict[VirtualFileId, str]:
        return {
            "tool.py": self.tool_py,
            "entrypoint.txt": self.entrypoint_txt,
            "settings_schema.json": self.settings_schema_json,
            "input_schema.json": self.input_schema_json,
            "usage_instructions.md": self.usage_instructions_md,
        }


class EditorEditOpsPatchOp(BaseModel):
    model_config = ConfigDict(frozen=True)

    op: Literal["patch"]
    target_file: VirtualFileId
    patch_lines: list[str] = Field(min_length=1)


EditorEditOpsOp = EditorEditOpsPatchOp
