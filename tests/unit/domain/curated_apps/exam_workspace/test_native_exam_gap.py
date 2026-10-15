"""Automatic gap values for the native exam document (ST-SKRIPT-39-04)."""

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeGap
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_gap_fill_item,
)


class TestAutomaticValues:
    def test_automatic_values_keep_only_bounded_disjoint_spellings(self) -> None:
        gap = NativeGap(
            gap_id="gap_001",
            accepted_values=("mobiltelefon",),
            automatic_values=(
                "mobiltelefone",
                "mobiltelefons",
                "mobil",
                "mobiltelefon",
                "Mobiltelefone",
                "mobiltelefonx",
                "mobiltelefony",
                "mobiltelefonz",
            ),
        )

        assert gap.automatic_values == ("mobiltelefone", "mobiltelefons", "mobiltelefonx")

    def test_excluded_values_stay_removed_after_serialization_and_rekeying(self) -> None:
        gap = NativeGap(
            gap_id="gap_001",
            accepted_values=("Stockholm",),
            automatic_values=("Stockholn", "Stokholm"),
            excluded_automatic_values=("stockholn",),
        )
        assert gap.automatic_values == ("Stokholm",)
        payload = gap.model_dump(mode="json")
        payload["accepted_values"] = ["Stockholm", "stockholms"]
        payload["automatic_values"] = ["Stockholn", "Stokholm"]
        reopened = NativeGap.model_validate(payload)
        assert reopened.automatic_values == ("Stokholm",)
        assert reopened.excluded_automatic_values == ("stockholn",)

    def test_automatic_values_without_an_accepted_value_are_dropped(self) -> None:
        gap = NativeGap(gap_id="gap_001", automatic_values=("NE",))

        assert gap.automatic_values == ()

    def test_automatic_values_equal_to_an_accepted_value_case_folded_are_dropped(self) -> None:
        gap = NativeGap(
            gap_id="gap_001",
            accepted_values=("Nominalfras",),
            automatic_values=("nominalfras", "Nominalfas"),
        )

        assert gap.automatic_values == ("Nominalfas",)

    def test_an_accepted_value_under_four_characters_keeps_no_automatic_values(self) -> None:
        gap = NativeGap(gap_id="gap_001", accepted_values=("NF",), automatic_values=("NE",))

        assert gap.automatic_values == ()

    def test_a_changed_accepted_value_drops_its_orphaned_automatic_values(self) -> None:
        item = make_gap_fill_item(accepted=("katt",), automatic=("kat", "ktat", "kattn"))
        edited = NativeExamItem.model_validate(
            {
                **item.model_dump(),
                "gaps": [
                    {
                        **item.gaps[0].model_dump(),
                        "accepted_values": ["hund"],
                    }
                ],
            }
        )

        assert edited.gaps[0].automatic_values == ()

    def test_absent_key_admits_no_automatic_values_without_accepted_values(self) -> None:
        item = make_gap_fill_item(
            origin=NativeAnswerKeyOrigin.ABSENT,
            accepted=(),
            automatic=("NE",),
        )

        assert item.gaps[0].automatic_values == ()
