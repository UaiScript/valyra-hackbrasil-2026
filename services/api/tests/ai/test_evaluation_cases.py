"""Exemplos de avaliação do prompt: aceitação lexical não é aprovação semântica."""

import json
from pathlib import Path

import pytest

from tests.ai.factories import alpha_evidence, context_data, money_evidence
from valyra.ai import llm_client
from valyra.ai.domain import UnsupportedClaimError, build_explain_response
from valyra.ai.schemas import EvidenceContext, LLMPayload

CASES = json.loads((Path(__file__).parent / "fixtures/explanation_evals.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_casos_de_avaliacao_documentam_limites_reais(case):
    ctx = EvidenceContext.model_validate(
        context_data(
            evidences=[] if case.get("context") == "empty" else [money_evidence(), alpha_evidence()]
        )
    )
    reply = LLMPayload(
        answer=case["answer"],
        evidence_ids=case["evidence_ids"],
        uncertainty="alta",
        limitations=["Sem projeção disponível."],
    )
    assert case["human_review"] in {"accept", "reject"}
    assert case["reason"]
    if case["automatic"] == "reject":
        with pytest.raises(UnsupportedClaimError):
            build_explain_response(ctx, reply)
    else:
        build_explain_response(ctx, reply)


def test_prompt_preserva_restricao_de_causalidade_e_ausencia_de_dados():
    # Manter explícitas as instruções que os casos de revisão humana exercitam.
    prompt = llm_client._SYSTEM_INSTRUCTIONS
    assert "não diga que clima, safra ou um sinal macro causou" in prompt
    assert "Ausência de dados não significa saldo zero" in prompt
    assert "Não atribua probabilidade a scores heurísticos" in prompt
