import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.vault_names import rename_vault_filename


@pytest.mark.parametrize(
    ("stem", "extension", "expected"),
    [
        ("  Slutprov  ", ".provdokument.zip", "Slutprov.provdokument.zip"),
        ("Slutprov.provdokument.zip", ".provdokument.zip", "Slutprov.provdokument.zip"),
        (
            "Slutprov.provdokument.zip.provdokument.zip",
            ".provdokument.zip",
            "Slutprov.provdokument.zip",
        ),
        (
            "Slutprov.PROVDOKUMENT.ZIP.provdokument.zip",
            ".provdokument.zip",
            "Slutprov.provdokument.zip",
        ),
        ("Slutprov.  ", ".pdf", "Slutprov..pdf"),
        ("Bilaga.PDF.pdf", ".pdf", "Bilaga.pdf"),
        ("Anteckningar", "", "Anteckningar"),
        ("x" * 251, ".pdf", "x" * 251 + ".pdf"),
    ],
)
def test_stem_is_normalized_without_changing_its_meaning(
    stem: str, extension: str, expected: str
) -> None:
    assert rename_vault_filename(stem=stem, extension=extension) == expected


@pytest.mark.parametrize(
    ("stem", "extension"),
    [
        (".provdokument.zip", ".provdokument.zip"),
        (".PDF.pdf", ".pdf"),
        ("  ", ".pdf"),
        ("../Slutprov", ".pdf"),
        ("mapp/Slutprov", ".pdf"),
        ("mapp\\Slutprov", ".pdf"),
        ("x" * 252, ".pdf"),
    ],
)
def test_invalid_or_empty_stems_are_rejected(stem: str, extension: str) -> None:
    with pytest.raises(DomainError) as caught:
        rename_vault_filename(stem=stem, extension=extension)
    assert caught.value.code is ErrorCode.VALIDATION_ERROR
