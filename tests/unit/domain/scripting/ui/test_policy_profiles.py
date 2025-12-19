from skriptoteket.domain.scripting.ui.contract_v2 import UiActionFieldKind, UiOutputKind
from skriptoteket.domain.scripting.ui.policy import (
    CURATED_UI_POLICY,
    DEFAULT_UI_POLICY,
    UiPolicyProfileId,
)


def test_default_ui_policy_profile_values() -> None:
    assert DEFAULT_UI_POLICY.profile_id is UiPolicyProfileId.DEFAULT
    assert DEFAULT_UI_POLICY.budgets.state_max_bytes == 64 * 1024
    assert DEFAULT_UI_POLICY.budgets.ui_payload_max_bytes == 256 * 1024

    assert DEFAULT_UI_POLICY.caps.max_outputs == 50
    assert DEFAULT_UI_POLICY.caps.table_max_rows == 750
    assert DEFAULT_UI_POLICY.caps.table_max_cols == 40

    assert UiOutputKind.VEGA_LITE not in DEFAULT_UI_POLICY.allowed_output_kinds
    assert UiOutputKind.MARKDOWN in DEFAULT_UI_POLICY.allowed_output_kinds
    assert UiActionFieldKind.BOOLEAN in DEFAULT_UI_POLICY.allowed_action_field_kinds


def test_curated_ui_policy_profile_values() -> None:
    assert CURATED_UI_POLICY.profile_id is UiPolicyProfileId.CURATED
    assert CURATED_UI_POLICY.budgets.state_max_bytes == 256 * 1024
    assert CURATED_UI_POLICY.budgets.ui_payload_max_bytes == 512 * 1024

    assert CURATED_UI_POLICY.caps.max_outputs == 150
    assert CURATED_UI_POLICY.caps.table_max_rows == 2_500
    assert CURATED_UI_POLICY.caps.table_max_cols == 80
    assert CURATED_UI_POLICY.caps.vega_lite_spec_max_bytes == 256 * 1024

    assert UiOutputKind.VEGA_LITE in CURATED_UI_POLICY.allowed_output_kinds

