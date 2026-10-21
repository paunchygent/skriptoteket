"""Deterministic Exam.net QTI sample package inputs.

Purpose:
    Provide the probe-derived sample item sets for Exam.net QTI 2.1 package
    and validation-report regression tests, ported from Sir Convert-a-Lot at
    revision 41be61a6.

Relationships:
    - Uses the reusable exam-conversion QTI contracts instead of
      DigiExam-specific parser fixtures.
    - Feeds the ported QTI package and empirical contract-rule tests.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiManualRepresentation,
    ExamNetQtiMatchEntry,
    ExamNetQtiMatchPair,
    ExamNetQtiTextEntryGap,
    ExamNetQtiUnsupportedResource,
)

_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


@dataclass(frozen=True)
class ExamNetQtiSamplePackage:
    """One deterministic QTI sample package input."""

    name: str
    package_filename: str
    report_filename: str
    items: tuple[ExamNetQtiItem, ...]


def examnet_qti_keyed_samples() -> tuple[ExamNetQtiSamplePackage, ...]:
    """Return the deterministic keyed QTI sample package set."""

    return (
        _single_choice_sample(),
        _multiple_response_sample(),
        _gap_fill_sample(),
        _free_text_sample(),
        _image_single_choice_sample(),
        _image_free_text_sample(),
        _matching_proof_gated_sample(),
        _unsupported_resource_omission_sample(),
    )


def examnet_qti_manual_unkeyed_samples() -> tuple[ExamNetQtiSamplePackage, ...]:
    """Return deterministic manual/unkeyed QTI manual/unkeyed sample packages."""

    return (
        _unkeyed_single_choice_sample(),
        _unkeyed_multiple_response_sample(),
        _manual_gap_fill_preservation_sample(),
        _manual_matching_preservation_sample(),
    )


def _single_choice_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "single-choice-mcq",
        _choice_item(
            item_id="item_001",
            sequence=1,
            title="Flerval ett svar",
            prompt="Vilket svar kopplar beläggen tydligast till huvudfrågan?",
            interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
            correct=("choice_002",),
        ),
    )


def _unkeyed_single_choice_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "unkeyed-single-choice-preserved",
        _handbuilt_unkeyed_single_choice_item(),
    )


def _unkeyed_multiple_response_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "unkeyed-multiple-response-preserved",
        _handbuilt_unkeyed_multiple_response_item(),
    )


def _manual_gap_fill_preservation_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "manual-gap-fill-preserved-as-free-text",
        _handbuilt_unkeyed_gap_fill_item(),
    )


def _manual_matching_preservation_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "manual-matching-preserved-as-free-text",
        ExamNetQtiItem(
            item_id="item_001",
            sequence=1,
            title="Matchning utan facit",
            interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
            prompt_lines=(
                "Para ihop varje begrepp med rätt förklaring.",
                "Vänster kolumn:",
                "1. kloroplast",
                "2. mitokondrie",
                "Höger kolumn:",
                "A. fotosyntes",
                "B. ATP-produktion",
                "Ursprunglig svarsyta: 1 = __, 2 = __",
            ),
            max_score=2,
            evaluation_mode=ExamNetQtiEvaluationMode.MANUAL_UNKEYED,
            manual_representation=ExamNetQtiManualRepresentation.FREE_TEXT_PRESERVATION,
            expected_lines=8,
            source_item_type="matching",
        ),
    )


def _handbuilt_unkeyed_single_choice_item() -> ExamNetQtiItem:
    """Hand-built item_002 shape: automatic single choice without an answer key."""

    return ExamNetQtiItem(
        item_id="item_002",
        sequence=2,
        title="Flervalsfråga typ 1",
        interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
        prompt_lines=(
            'Så här ser en flervalsfråga (MCQ) av typen "flera val" i Digiexam.'
            "Det går bara att välja ett alternativ som rätt svar "
            "(Jag valde andra alternativet). "
            "Väljer eleven det får den 2 poäng.",
        ),
        max_score=2,
        evaluation_mode=ExamNetQtiEvaluationMode.AUTOMATIC,
        source_item_type="single_choice",
        choices=(
            ExamNetQtiChoice("choice_001", "Första alternativet"),
            ExamNetQtiChoice("choice_002", "Andra alternativet"),
            ExamNetQtiChoice("choice_003", "Tredje alternativet"),
            ExamNetQtiChoice("choice_004", "Fjärde alternativet"),
            ExamNetQtiChoice(
                "choice_005",
                "Ytterligare ett alternativ. Man kan lägga till hur många man vill",
            ),
        ),
    )


def _handbuilt_unkeyed_multiple_response_item() -> ExamNetQtiItem:
    """Hand-built item_004 shape: automatic multiple response without an answer key."""

    return ExamNetQtiItem(
        item_id="item_004",
        sequence=4,
        title="Flera rätta svar (flervalsfråga)",
        interaction_type=ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
        prompt_lines=(
            'Så här ser en annan flervalsfråga (MCQ) av typen "flera rätta svar" '
            "i Digiexam. Det går att välja flera alternativ som rätt svar "
            "(Jag valde första och andra alternativet). "
            "Väljer eleven de rätta alternativen får 2 päng. Ingen egen anteckning."
            'Det finns tre olika poängregler. Jag valde\xa0"Allt eller inget": '
            "Eleven måste svara alla rätt för att få maxpoängen. "
            "Om eleven missar att svara på något eller svarar felaktigt på något, "
            "tilldelas eleven noll poäng.",
        ),
        max_score=2,
        evaluation_mode=ExamNetQtiEvaluationMode.AUTOMATIC,
        source_item_type="multiple_response",
        choices=(
            ExamNetQtiChoice("choice_001", "Första alternativet"),
            ExamNetQtiChoice("choice_002", "Andra alternativet"),
            ExamNetQtiChoice("choice_003", "Tredje alternativet"),
        ),
    )


def _handbuilt_unkeyed_gap_fill_item() -> ExamNetQtiItem:
    """Hand-built item_007 shape: automatic gap fill with empty accepted values."""

    return ExamNetQtiItem(
        item_id="item_007",
        sequence=7,
        title="Lucktext",
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_lines=(
            "Här är en _____ med tre luckor i texten. "
            "Hela _____ kan göras hur\xa0_____ som helst"
            "Samma regler som flera rätta svar gäller: allt eller inget, rätt minus fel. "
            "Jag valde poäng per svar. Eleven får pluspoäng för varje rätt svar. "
            "Varje rätt svar är värt maxpoängen för frågan delat på antalet potentiellt "
            "rätta alternativ. Inga poäng dras av för fel svar. "
            "Den lägsta poängen som tilldelas är noll.Maxpoäng: 3.\xa0"
            "Luckorna innehåller följande ord: lucktext, texten, lång",
        ),
        max_score=3,
        evaluation_mode=ExamNetQtiEvaluationMode.AUTOMATIC,
        source_item_type="gap_fill",
        text_entry_gaps=tuple(
            ExamNetQtiTextEntryGap(
                response_identifier=f"RESPONSE_gap_{index:03d}",
                label=f"Lucka {index}",
                accepted_values=(),
            )
            for index in range(1, 4)
        ),
    )


def _multiple_response_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "multiple-response-mcq",
        _choice_item(
            item_id="item_001",
            sequence=1,
            title="Flerval flera svar",
            prompt="Vilka drag stärker ett källkritiskt svar?",
            interaction_type=ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
            correct=("choice_001", "choice_002", "choice_004"),
        ),
    )


def _gap_fill_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "gap-fill-text-entry",
        ExamNetQtiItem(
            item_id="item_001",
            sequence=1,
            title="Lucktext",
            interaction_type=ExamNetQtiInteractionType.GAP_FILL,
            prompt_lines=("Cellens energivaluta är _____.",),
            max_score=1,
            text_entry_gaps=(
                ExamNetQtiTextEntryGap(
                    response_identifier="RESPONSE_gap_001",
                    label="Lucka 1",
                    accepted_values=("ATP", "atp"),
                ),
            ),
        ),
    )


def _free_text_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "free-text",
        ExamNetQtiItem(
            item_id="item_001",
            sequence=1,
            title="Fritext",
            interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
            prompt_lines=(
                "Resonera kring hur sociala medier både kan förbättra "
                "tillgången till information och förvränga debatten.",
            ),
            max_score=9,
            free_text_criterion_points=9,
            expected_lines=8,
        ),
    )


def _image_single_choice_sample() -> ExamNetQtiSamplePackage:
    item = _choice_item(
        item_id="item_001",
        sequence=1,
        title="Flerval med bild",
        prompt="Vilken etikett passar bäst till bilden?",
        interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
        correct=("choice_002",),
        image_resources=(_image("image_001", "Exempelbild för flervalsfråga"),),
    )
    return _sample("image-single-choice-mcq", item)


def _image_free_text_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "image-free-text",
        ExamNetQtiItem(
            item_id="item_001",
            sequence=1,
            title="Fritext med bild",
            interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
            prompt_lines=("Beskriv vad bilden visar och motivera din tolkning.",),
            max_score=6,
            free_text_criterion_points=6,
            expected_lines=8,
            image_resources=(_image("image_001", "Exempelbild för fritextfråga"),),
        ),
    )


def _matching_proof_gated_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "matching-proof-gated",
        ExamNetQtiItem(
            item_id="item_001",
            sequence=1,
            title="Matcha ihop",
            interaction_type=ExamNetQtiInteractionType.MATCHING,
            prompt_lines=("Para ihop varje cellstruktur med rätt funktion.",),
            max_score=4,
            match_pairs=(
                ExamNetQtiMatchPair("left_001", "kloroplast", "right_001", "fotosyntes"),
                ExamNetQtiMatchPair("left_002", "mitokondrie", "right_002", "ATP-produktion"),
                ExamNetQtiMatchPair("left_003", "ribosom", "right_003", "proteinsyntes"),
                ExamNetQtiMatchPair(
                    "left_004",
                    "cellkärna",
                    "right_004",
                    "genetisk information",
                ),
            ),
            match_left=(
                ExamNetQtiMatchEntry("left_001", "kloroplast"),
                ExamNetQtiMatchEntry("left_002", "mitokondrie"),
                ExamNetQtiMatchEntry("left_003", "ribosom"),
                ExamNetQtiMatchEntry("left_004", "cellkärna"),
            ),
            match_right=(
                ExamNetQtiMatchEntry("right_001", "fotosyntes"),
                ExamNetQtiMatchEntry("right_002", "ATP-produktion"),
                ExamNetQtiMatchEntry("right_003", "proteinsyntes"),
                ExamNetQtiMatchEntry("right_004", "genetisk information"),
            ),
        ),
    )


def _unsupported_resource_omission_sample() -> ExamNetQtiSamplePackage:
    return _sample(
        "unsupported-resource-omission",
        ExamNetQtiItem(
            item_id="item_001",
            sequence=1,
            title="Fritext med externt ljud",
            interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
            prompt_lines=("Lyssna på lärarens ljudfil och sammanfatta huvudpoängen.",),
            max_score=5,
            free_text_criterion_points=5,
            expected_lines=8,
            unsupported_resources=(
                ExamNetQtiUnsupportedResource(
                    resource_id="audio_001",
                    resource_type="audio",
                    label="teacher-audio.mp3",
                ),
            ),
        ),
    )


def _choice_item(
    *,
    item_id: str,
    sequence: int,
    title: str,
    prompt: str,
    interaction_type: ExamNetQtiInteractionType,
    correct: tuple[str, ...],
    evaluation_mode: ExamNetQtiEvaluationMode = ExamNetQtiEvaluationMode.AUTOMATIC,
    source_item_type: str | None = None,
    image_resources: tuple[ExamNetQtiImageResource, ...] = (),
) -> ExamNetQtiItem:
    return ExamNetQtiItem(
        item_id=item_id,
        sequence=sequence,
        title=title,
        interaction_type=interaction_type,
        prompt_lines=(prompt,),
        max_score=4,
        evaluation_mode=evaluation_mode,
        source_item_type=source_item_type,
        choices=(
            ExamNetQtiChoice("choice_001", "Svaret använder relevanta belägg."),
            ExamNetQtiChoice("choice_002", "Svaret kopplar beläggen till huvudfrågan."),
            ExamNetQtiChoice("choice_003", "Svaret byter ämne mitt i resonemanget."),
            ExamNetQtiChoice("choice_004", "Svaret skiljer fakta från värdering."),
        ),
        correct_choice_identifiers=correct,
        image_resources=image_resources,
    )


def _image(asset_id: str, alt_text: str) -> ExamNetQtiImageResource:
    return ExamNetQtiImageResource(
        asset_id=asset_id,
        filename=f"{asset_id}.png",
        media_type="image/png",
        payload=_ONE_PIXEL_PNG,
        alt_text=alt_text,
        source_reference="keyed-deterministic-sample",
    )


def _sample(name: str, item: ExamNetQtiItem) -> ExamNetQtiSamplePackage:
    return ExamNetQtiSamplePackage(
        name=name,
        package_filename="qti-package.zip",
        report_filename="qti-validation-report.json",
        items=(item,),
    )
