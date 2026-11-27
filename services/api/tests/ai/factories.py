"""Fixtures sintéticas compartilhadas dos contratos IA, sem banco ou provedor."""

from valyra.ai.schemas import LLMRequest

ACCOUNT_ID = "00000000-0000-0000-0000-000000000101"
BATCH_ID = "00000000-0000-0000-0000-000000000201"
AS_OF = "2026-11-17T12:00:00Z"
BUILT_AT = "2026-11-17T12:00:01Z"


def money_evidence(**changes):
    data = {
        "evidence_id": "e1",
        "metric_key": "finance.account.reference_balance",
        "label": "Saldo de referência",
        "basis": "reference",
        "source": {
            "kind": "finance_record",
            "record_type": "account",
            "record_id": ACCOUNT_ID,
            "recorded_at": "2026-11-01T12:00:00Z",
        },
        "value": {"kind": "money", "amount_cents": 500000, "currency": "BRL"},
        "period": {"start": "2026-11-01", "end": "2026-11-01"},
    }
    return data | changes


def alpha_evidence(**changes):
    data = {
        "evidence_id": "e2",
        "metric_key": "alpha.crop.yield",
        "label": "Produtividade sintética",
        "basis": "observed",
        "source": {
            "kind": "alpha_signal",
            "source_id": "00000000-0000-0000-0000-000000000301",
            "signal_id": "00000000-0000-0000-0000-000000000401",
            "signal_key": "synthetic:yield",
            "revision_id": 1,
            "source_url": "https://example.org/synthetic/yield",
            "observation_date": "2026-10-01",
            "published_at": "2026-11-10T12:00:00Z",
            "published_at_estimated": False,
            "ingested_at": "2026-11-11T12:00:00Z",
        },
        "value": {"kind": "decimal", "value_decimal": "12.500", "unit": "t/ha"},
        "period": {"start": "2026-10-01", "end": "2026-10-01"},
    }
    return data | changes


def calculation_evidence(**changes):
    data = money_evidence(
        evidence_id="e3",
        metric_key="finance.forecast.minimum_balance",
        basis="projected",
        source={
            "kind": "calculation",
            "module": "finance",
            "method_key": "synthetic_forecast",
            "method_version": "fixture-v1",
            "computed_at": BUILT_AT,
            "input_scope": {
                "account_id": ACCOUNT_ID,
                "period": {"start": "2026-08-01", "end": "2026-11-17"},
                "import_batch_ids": [BATCH_ID],
            },
            "input_evidence_ids": ["e1"],
        },
        period={"start": "2026-11-18", "end": "2026-12-17"},
    )
    return data | changes


def context_data(**changes):
    return {
        "account_id": ACCOUNT_ID,
        "as_of": AS_OF,
        "built_at": BUILT_AT,
        "evidences": [],
        "limitations": [],
    } | changes


def make_request(**changes):
    return LLMRequest(**({"question": "Explique", "context_data": context_data()} | changes))
