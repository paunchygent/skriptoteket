"""Browser-observed responsive review assertions for the real-DXE driver."""

from __future__ import annotations

import re
from dataclasses import dataclass

from playwright.sync_api import FloatRect, Locator, Page, Request, Response, expect
from pydantic import JsonValue

_BOX_TOLERANCE = 2.0


@dataclass(frozen=True)
class ChoiceDraft:
    """Candidate-derived choice draft retained across a local cancel check."""

    values: dict[str, bool]


@dataclass(frozen=True)
class GapDraft:
    """Candidate-derived gap draft retained across a local cancel check."""

    values: dict[str, str]


AdvisoryDraft = ChoiceDraft | GapDraft


def require_box(locator: Locator, *, description: str) -> FloatRect:
    """Return a visible element's layout box or fail with its product role."""

    locator.scroll_into_view_if_needed()
    box = locator.bounding_box()
    if box is None:
        raise AssertionError(f"Expected a layout box for {description}.")
    return box


def assert_contained(outer: Locator, inner: Locator, *, description: str) -> None:
    """Require an action to remain within its visual owner after responsive layout."""

    outer_box = require_box(outer, description=f"{description} owner")
    inner_box = require_box(inner, description=description)
    if (
        inner_box["x"] < outer_box["x"] - _BOX_TOLERANCE
        or inner_box["y"] < outer_box["y"] - _BOX_TOLERANCE
        or inner_box["x"] + inner_box["width"]
        > outer_box["x"] + outer_box["width"] + _BOX_TOLERANCE
        or inner_box["y"] + inner_box["height"]
        > outer_box["y"] + outer_box["height"] + _BOX_TOLERANCE
    ):
        raise AssertionError(f"{description} is outside its owning container.")


def assert_same_box(before: FloatRect, after: FloatRect, *, description: str) -> None:
    """Keep desktop detail geometry stable when only review mode changes."""

    changed: list[str] = []
    for dimension in ("x", "y", "width", "height"):
        if abs(before[dimension] - after[dimension]) > _BOX_TOLERANCE:
            changed.append(dimension)
    if changed:
        raise AssertionError(f"{description} changed during edit mode: {', '.join(changed)}.")


def assert_action_labels(group: Locator, labels: tuple[str, ...]) -> None:
    """Require fixed action-slot ordering rather than matching a loose label."""

    actions = group.get_by_role("button")
    if actions.count() != len(labels):
        raise AssertionError(f"Expected {len(labels)} action slots, found {actions.count()}.")
    actual = tuple(actions.nth(index).inner_text().strip() for index in range(actions.count()))
    if tuple(label.casefold() for label in actual) != tuple(label.casefold() for label in labels):
        raise AssertionError(f"Expected action slots {labels!r}, found {actual!r}.")


def selected_item_id(detail: Locator) -> str:
    """Read the producer-backed item id held by the selected detail."""

    item_id = detail.get_attribute("data-selected-item-id")
    if not item_id:
        raise AssertionError("The selected real-DXE review item has no item identifier.")
    return item_id


def _advisory_detail(detail: Locator) -> Locator:
    advisory = detail.locator('[data-test="exam-converter-advisory-review-detail"]')
    expect(advisory).to_be_visible()
    return advisory


def _choice_draft_state(detail: Locator) -> dict[str, bool]:
    choices = detail.locator('[data-test^="exam-converter-advisory-edit-choice-"]')
    state: dict[str, bool] = {}
    for index in range(choices.count()):
        choice = choices.nth(index)
        data_test = choice.get_attribute("data-test")
        if not data_test:
            raise AssertionError("An advisory choice editor is missing its test identifier.")
        state[data_test] = choice.get_attribute("aria-pressed") == "true"
    if not state:
        raise AssertionError("The real advisory choice editor did not expose choices.")
    return state


def _gap_draft_state(detail: Locator) -> dict[str, str]:
    gaps = detail.locator('input[data-test^="exam-converter-advisory-edit-gap-"]')
    state: dict[str, str] = {}
    for index in range(gaps.count()):
        gap = gaps.nth(index)
        data_test = gap.get_attribute("data-test")
        if not data_test:
            raise AssertionError("An advisory gap editor is missing its test identifier.")
        state[data_test] = gap.input_value()
    if not state:
        raise AssertionError("The real advisory gap editor did not expose gaps.")
    return state


def change_local_advisory_draft(detail: Locator) -> AdvisoryDraft:
    """Change one rendered advisory control without sending a correction intent."""

    choices = detail.locator('[data-test^="exam-converter-advisory-edit-choice-"]')
    if choices.count() > 0:
        initial = _choice_draft_state(detail)
        for index in range(choices.count()):
            choices.nth(index).click()
            if _choice_draft_state(detail) != initial:
                return ChoiceDraft(values=initial)
        raise AssertionError("Could not change the real advisory choice draft locally.")

    gaps = detail.locator('input[data-test^="exam-converter-advisory-edit-gap-"]')
    if gaps.count() > 0:
        initial = _gap_draft_state(detail)
        first_gap = gaps.first
        first_identifier = first_gap.get_attribute("data-test")
        if not first_identifier:
            raise AssertionError("The first advisory gap editor is missing its test identifier.")
        first_gap.fill(f"{initial[first_identifier]} ändrat")
        if _gap_draft_state(detail) == initial:
            raise AssertionError("Could not change the real advisory gap draft locally.")
        return GapDraft(values=initial)

    raise AssertionError("The real advisory item exposed neither choices nor gaps to edit.")


def assert_draft_reset(detail: Locator, expected: AdvisoryDraft) -> None:
    """Require edit re-entry after cancel to reconstruct the candidate draft."""

    actual = (
        _choice_draft_state(detail)
        if isinstance(expected, ChoiceDraft)
        else _gap_draft_state(detail)
    )
    if actual != expected.values:
        raise AssertionError("Cancelling did not restore the candidate-derived advisory draft.")


def assert_persisted_responses(write: Response, projection: Response, *, description: str) -> None:
    """Require the correction write and producer review projection to succeed together."""

    if not write.ok or not projection.ok:
        raise AssertionError(f"{description} did not persist and reproject successfully.")


def assert_prefill_panel(page: Page) -> None:
    """Prove the amber candidate panel's copy and equal, contained neutral actions."""

    prefill = page.locator('[data-test="exam-converter-ai-prefill-panel"]')
    expect(prefill).to_be_visible()
    expect(prefill.get_by_role("heading", name="Föreslagna facit", exact=True)).to_be_visible()
    expect(prefill).to_contain_text(re.compile(r"\d+\s+att granska\."))
    actions = prefill.locator('[data-test="exam-converter-ai-prefill-actions"]')
    review = page.locator('[data-test="exam-converter-open-ai-prefill-action"]')
    accept_all = page.locator('[data-test="exam-converter-accept-all-ai-prefill-action"]')
    expect(review).to_be_visible()
    expect(accept_all).to_be_visible()
    expect(review).to_have_text("Granska")
    expect(accept_all).to_have_text("Godkänn alla")
    review_box = require_box(review, description="the Granska action")
    accept_all_box = require_box(accept_all, description="the Godkänn alla action")
    if abs(review_box["width"] - accept_all_box["width"]) > _BOX_TOLERANCE:
        raise AssertionError("The two amber-panel actions do not have equal widths.")
    assert_contained(prefill, actions, description="the amber-panel action group")
    assert_contained(prefill, review, description="the Granska action")
    assert_contained(prefill, accept_all, description="the Godkänn alla action")
    review_style = review.evaluate(
        "element => { const style = getComputedStyle(element); "
        "return [style.backgroundColor, style.color]; }"
    )
    accept_all_style = accept_all.evaluate(
        "element => { const style = getComputedStyle(element); "
        "return [style.backgroundColor, style.color]; }"
    )
    if review_style != accept_all_style:
        raise AssertionError("The amber-panel actions do not share the neutral presentation.")


def assert_mobile_detail(page: Page, detail: Locator) -> dict[str, JsonValue]:
    """Prove the phone-only review composition before an edit/cancel cycle."""

    page.set_viewport_size({"width": 390, "height": 844})
    advisory = _advisory_detail(detail)
    top_actions = page.locator('[data-test="exam-converter-review-top-actions"]')
    bottom_actions = page.locator('[data-test="exam-converter-review-bottom-actions"]')
    expect(top_actions).to_be_visible()
    expect(bottom_actions).to_be_visible()
    assert_action_labels(top_actions, ("Översikt", "Godkänn", "Ändra"))
    assert_action_labels(bottom_actions, ("Godkänn", "Ändra"))
    for index in range(top_actions.get_by_role("button").count()):
        assert_contained(
            detail, top_actions.get_by_role("button").nth(index), description="a mobile top action"
        )
    for index in range(bottom_actions.get_by_role("button").count()):
        assert_contained(
            detail,
            bottom_actions.get_by_role("button").nth(index),
            description="a mobile bottom action",
        )

    page.locator('[data-test="exam-converter-edit-advisory-answer-key-action"]').click()
    expect(advisory).to_have_attribute("data-editing", "true")
    assert_action_labels(top_actions, ("Översikt", "Spara", "Avbryt"))
    assert_action_labels(bottom_actions, ("Spara", "Avbryt"))
    return {"mobile_actions_contained": True, "mobile_viewport_width": 390}


def cancel_local_edit_and_assert_reset(
    page: Page,
    detail: Locator,
    correction_request_urls: list[str],
    item_id: str,
) -> None:
    """Prove that Cancel discards only local input and neither writes nor reroutes."""

    advisory = _advisory_detail(detail)
    candidate_draft = change_local_advisory_draft(detail)
    requests_before_cancel = len(correction_request_urls)
    page.locator('[data-test="exam-converter-cancel-advisory-edit-action"]').click()
    expect(advisory).to_have_attribute("data-editing", "false")
    if selected_item_id(detail) != item_id:
        raise AssertionError("Cancelling a local advisory edit changed the selected question.")
    if len(correction_request_urls) != requests_before_cancel:
        raise AssertionError(
            "Cancelling a local advisory edit issued a correction-session request."
        )

    page.locator('[data-test="exam-converter-edit-advisory-answer-key-action"]').click()
    expect(advisory).to_have_attribute("data-editing", "true")
    assert_draft_reset(detail, candidate_draft)
    requests_before_second_cancel = len(correction_request_urls)
    page.locator('[data-test="exam-converter-cancel-advisory-edit-action"]').click()
    expect(advisory).to_have_attribute("data-editing", "false")
    if len(correction_request_urls) != requests_before_second_cancel:
        raise AssertionError(
            "The second local advisory cancel issued a correction-session request."
        )


def assert_desktop_geometry(page: Page, detail: Locator) -> dict[str, JsonValue]:
    """Prove desktop keeps action slots and detail geometry stable across edit mode."""

    page.set_viewport_size({"width": 1440, "height": 960})
    advisory = _advisory_detail(detail)
    top_actions = page.locator('[data-test="exam-converter-review-top-actions"]')
    bottom_actions = page.locator('[data-test="exam-converter-review-bottom-actions"]')
    expect(top_actions).to_be_visible()
    expect(bottom_actions).not_to_be_visible()
    assert_action_labels(top_actions, ("Översikt", "Godkänn", "Ändra"))
    detail_box = require_box(detail, description="the desktop selected detail")
    actions_box = require_box(top_actions, description="the desktop top action group")

    page.locator('[data-test="exam-converter-edit-advisory-answer-key-action"]').click()
    expect(advisory).to_have_attribute("data-editing", "true")
    assert_action_labels(top_actions, ("Översikt", "Spara", "Avbryt"))
    assert_same_box(
        detail_box,
        require_box(detail, description="the desktop selected detail in edit mode"),
        description="The desktop selected-detail shell",
    )
    assert_same_box(
        actions_box,
        require_box(top_actions, description="the desktop top action group in edit mode"),
        description="The desktop top action group",
    )
    page.locator('[data-test="exam-converter-cancel-advisory-edit-action"]').click()
    expect(advisory).to_have_attribute("data-editing", "false")
    return {"desktop_bottom_actions_hidden": True, "desktop_viewport_width": 1440}


def capture_correction_request(request: Request, correction_request_urls: list[str]) -> None:
    """Retain only correction-session URLs so local Cancel can prove no write occurred."""

    if re.search(r"/correction-session/intents(?:\?|$)", request.url):
        correction_request_urls.append(request.url)
