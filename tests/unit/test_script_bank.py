from importlib.resources import files as resource_files

from skriptoteket.script_bank.bank import SCRIPT_BANK


def test_script_bank_entries_reference_existing_source_files() -> None:
    scripts_root = resource_files("skriptoteket.script_bank.scripts")

    assert SCRIPT_BANK, "SCRIPT_BANK must contain at least one entry"

    for entry in SCRIPT_BANK:
        source_path = scripts_root / entry.source_filename
        assert source_path.is_file(), f"Missing script-bank source: {entry.source_filename}"
        source = source_path.read_text(encoding="utf-8")
        assert "def run_tool" in source, f"Missing run_tool entrypoint in {entry.source_filename}"
