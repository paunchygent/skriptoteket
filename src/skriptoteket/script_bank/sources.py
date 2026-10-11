from __future__ import annotations

from importlib.resources import files as resource_files


def read_script_bank_source(*, source_filename: str) -> tuple[str, dict[str, str]]:
    """Read a tool's entrypoint and, for a tool in its own folder, the folder's other files."""
    scripts_root = resource_files("skriptoteket.script_bank.scripts")
    source_code = (scripts_root / source_filename).read_text(encoding="utf-8")
    tool_dir, _, entry_name = source_filename.rpartition("/")
    if not tool_dir:
        return source_code, {}
    bundle_files = {
        path.name: path.read_text(encoding="utf-8")
        for path in (scripts_root / tool_dir).iterdir()
        if not path.name.startswith(".") and path.is_file() and path.name != entry_name
    }
    return source_code, bundle_files
