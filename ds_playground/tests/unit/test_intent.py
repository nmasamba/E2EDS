"""Intent extraction's deterministic parts: JSON patches applied whole, and the readback (5.3)."""

import pytest

from dsp.application.conversation import classify, leading
from dsp.application.workloads import apply_patch, base_workload, describe
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext

CTX = TrustedContext.local()
ROLE = {
    "field": "account_num",
    "role": "entity_id",
    "data_type": "string",
    "nullable": False,
    "public_output": "authorised_join_only",
}


def test_a29_a_patch_adds_to_lists_replaces_and_removes_or_is_refused_whole() -> None:
    """A29: add at the end or an index, replace, remove; a missing path refuses the whole patch."""
    workload = base_workload(CTX)
    patched = apply_patch(
        workload,
        [
            {"op": "add", "path": "/intent_constraints/field_roles/-", "value": ROLE},
            {
                "op": "add",
                "path": "/intent_constraints/split_group_fields/0",
                "value": "account_num",
            },
            {
                "op": "replace",
                "path": "/intent_constraints/features/soft_objective",
                "value": "minimise_count_among_feasible",
            },
            {"op": "remove", "path": "/intent_constraints/features/hard_max_count", "value": None},
            {"op": "add", "path": "/intent_constraints/features/hard_max_count", "value": 3},
        ],
    )
    roles = patched["intent_constraints"]["field_roles"]
    assert roles[-1] == ROLE
    assert len(roles) == 4
    assert patched["intent_constraints"]["split_group_fields"] == ["account_num"]
    assert (
        patched["intent_constraints"]["features"]["soft_objective"]
        == "minimise_count_among_feasible"
    )
    assert patched["intent_constraints"]["features"]["hard_max_count"] == 3
    assert workload["intent_constraints"]["field_roles"][-1]["field"] == "item_count"  # untouched
    for bad in (
        [{"op": "replace", "path": "/intent_constraints/features/no_such", "value": 1}],
        [{"op": "remove", "path": "/intent_constraints/field_roles/9", "value": None}],
        [{"op": "add", "path": "/intent_constraints/field_roles/x", "value": ROLE}],
        [{"op": "add", "path": "/nowhere/at/all", "value": 1}],
    ):
        with pytest.raises(DspError) as refused:
            apply_patch(workload, bad)
        assert refused.value.code is ErrorCode.INPUT_INVALID
    assert (
        apply_patch(
            workload, [{"op": "add", "path": "/intent_constraints/features/a~1b", "value": 1}]
        )["intent_constraints"]["features"]["a/b"]
        == 1
    )


def test_a29_the_readback_is_the_patch_in_words_and_nothing_more() -> None:
    """A29: the readback names each path and value; long values are cut; removes say so."""
    said = describe(
        [
            {"op": "add", "path": "/intent_constraints/field_roles/-", "value": ROLE},
            {"op": "remove", "path": "/intent_constraints/features/hard_max_count", "value": None},
            {
                "op": "replace",
                "path": "/requested_resources/max_external_charge_minor",
                "value": 10000,
            },
        ]
    )
    head = '/field_roles/- ← {"field": "account_num", "role": "entity_id", "data_type": "string", '
    assert said.startswith(head + '"nullabl...')
    assert (
        "; remove /features/hard_max_count; /requested_resources/max_external_charge_minor ← 10000"
        in said
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Pause now; exclude region before continuing.",
            ("pause", "exclude region before continuing."),
        ),
        ("cancel this run. then start over", ("cancel", "then start over")),
        ("status:\nwhat is running?", ("status", "what is running?")),
        ("pause the music", None),
        ('"pause now"; exclude region', None),
        ("The document says: pause now. Then it goes on.", None),
        ("pause now", None),
        ("pause now;   ", None),
    ],
)
def test_a24_a_leading_control_phrase_is_the_control_first_then_the_rest(
    text: str, expected: tuple[str, str] | None
) -> None:
    """A24: only an exact phrase at the start, then more, is a control plus an instruction."""
    assert leading(text) == expected
    if expected:
        assert classify(text) == expected[0]


def test_r17_the_requirements_own_rules_complete_a_patch_or_refuse_it() -> None:
    """R17, A29: a dropped predictor is excluded; a transform needs review; a row id stays."""
    from dsp.application.workloads import complete

    workload = base_workload(CTX)
    dropped = [
        {
            "op": "replace",
            "path": "/intent_constraints/features/allowed_fields",
            "value": ["item_count"],
        }
    ]
    whole = complete(workload, dropped)
    assert whole[1:] == [
        {
            "op": "replace",
            "path": "/intent_constraints/features/excluded_fields",
            "value": ["order_id", "region"],
        }
    ]
    transform = {
        "operation": "round_to_increment",
        "output_field": "prediction",
        "increment": 10,
        "units": "units",
        "ties": "away_from_zero",
        "raw_value_public": False,
        "privacy_claim": "precision_only",
    }
    added = [{"op": "add", "path": "/intent_constraints/output_transforms/-", "value": transform}]
    assert complete(workload, added)[1:] == [
        {"op": "replace", "path": "/intent_constraints/privacy_status", "value": "requires_review"}
    ]
    reviewed = apply_patch(
        workload,
        [
            {
                "op": "replace",
                "path": "/intent_constraints/privacy_status",
                "value": "requires_review",
            }
        ],
    )
    assert complete(reviewed, added) == added  # already under review: nothing to derive
    both = [
        {
            "op": "replace",
            "path": "/intent_constraints/features/excluded_fields",
            "value": ["order_id", "region"],
        }
    ]
    with pytest.raises(DspError, match="region is both allowed and excluded"):
        complete(workload, both)
    no_row_id = [{"op": "remove", "path": "/intent_constraints/field_roles/0", "value": None}]
    with pytest.raises(DspError, match="a row identifier must remain"):
        complete(workload, no_row_id)
    assert complete(workload, []) == []
