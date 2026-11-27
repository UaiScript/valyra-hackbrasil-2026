"""Barreiras do domínio com dados sintéticos, sem consultas a banco ou provedores."""

import pytest
from pydantic import ValidationError

from tests.ai.factories import alpha_evidence, calculation_evidence, context_data, money_evidence
from valyra.ai.domain import (
    EvidenceContextError,
    EvidenceReferenceError,
    UnsupportedClaimError,
    build_explain_response,
)
from valyra.ai.schemas import EvidenceContext, LLMPayload


def context(evidences=None):
    return EvidenceContext.model_validate(
        context_data(evidences=[money_evidence()] if evidences is None else evidences)
    )


def payload(answer, ids=("e1",), *, uncertainty="alta", limitations=None):
    return LLMPayload(
        answer=answer,
        evidence_ids=list(ids),
        uncertainty=uncertainty,
        limitations=["Projeção indisponível."] if limitations is None else limitations,
    )


@pytest.mark.parametrize(
    "answer",
    [
        "O saldo de referência é R$ 5.000,00.",
        "Saldo informado: R$5.000,00.",
        "Saldo de referência: R$\u00a05.000,00.",
        "No corte 2026-11-17, o saldo de referência de 2026-11-01 é R$ 5.000,00.",
        "Um saldo de referência não substitui uma projeção.",
    ],
)
def test_reproducao_de_valor_e_datas_originais(answer):
    result = build_explain_response(context(), payload(answer))
    assert result.answer == answer
    assert result.evidences[0].value.amount_cents == 500000


@pytest.mark.parametrize(
    "answer",
    [
        "O saldo é R$ 999,00.",
        "O saldo é R$ 5.000,01.",
        "O saldo é R$ 5.000,0.",
        "O saldo é R$ 5,000.00.",
        "O saldo é R$ 5.000,000.",
        "O saldo é 500000.",
        "O saldo é 5.000,00.",
        "O saldo é US$ 5.000,00.",
        "O saldo é 5.000,00 BRL.",
        "O saldo é -R$ 5.000,00.",
        "O saldo é +R$ 5.000,00.",
        "O saldo é R$ -5.000,00.",
        "O saldo é R$ 5.000,00%.",
        "O saldo é R$ 5.000,00 kg.",
        "O saldo é R$ 5.000,00 mil.",
        "O saldo é R$ 5.000,00e3.",
        "A projeção será de 30 dias.",
        "A chance é de 90%.",
        "O saldo é R$ 2026-11-17.",
        "A data é 2026-11-17%.",
        "A data é 2026-11-17-99.",
        "A data é 2027-11-17.",
        "A data é 17/11/2026.",
    ],
)
def test_nao_aceita_numero_data_moeda_sinal_escala_ou_unidade_trocados(answer):
    with pytest.raises(UnsupportedClaimError):
        build_explain_response(context(), payload(answer))


@pytest.mark.parametrize("answer", ["Saldo zero.", "São cinco mil reais.", "O saldo dobrou."])
def test_quantidades_por_extenso_nao_sao_conversoes_permitidas(answer):
    with pytest.raises(UnsupportedClaimError):
        build_explain_response(context(), payload(answer))


def test_sinal_negativo_nao_pode_virar_magnitude_positiva():
    ctx = context([money_evidence(value={"kind": "money", "amount_cents": -12990})])
    assert build_explain_response(ctx, payload("Valor informado: R$ -129,90.")).evidences
    with pytest.raises(UnsupportedClaimError):
        build_explain_response(ctx, payload("Valor informado: R$ 129,90."))


@pytest.mark.parametrize("answer", ["O indicador é 12,500 %.", "O indicador é 12,500%. "])
def test_percentual_nao_e_arredondado(answer):
    item = alpha_evidence(value={"kind": "decimal", "value_decimal": "12.500", "unit": "%"})
    assert build_explain_response(context([item]), payload(answer, ("e2",))).evidences


@pytest.mark.parametrize(
    "answer",
    [
        "O indicador é 12,5 %.",
        "O indicador é 0,125 fraction.",
        "O indicador é 12,500 pp.",
        "O indicador é 12,500 reais.",
    ],
)
def test_precisao_e_unidade_do_indicador_devem_ser_preservadas(answer):
    item = alpha_evidence(value={"kind": "decimal", "value_decimal": "12.500", "unit": "%"})
    with pytest.raises(UnsupportedClaimError):
        build_explain_response(context([item]), payload(answer, ("e2",)))


def test_contagem_permite_inteiro_isolado_sem_mudar_moeda_ou_percentual():
    item = money_evidence(value={"kind": "integer", "value_int": 3, "unit": "count"})
    for answer in ("Há 3 registros.", "Contagem: 3 count."):
        assert build_explain_response(context([item]), payload(answer)).evidences
    for answer in ("Saldo de R$ 3.", "Percentual de 3%.", "Identificador e3.", "Contagem: 3k."):
        with pytest.raises(UnsupportedClaimError):
            build_explain_response(context([item]), payload(answer))


def test_somente_evidencias_citadas_e_suas_dependencias_sustentam_numeros():
    ctx = context([money_evidence(), alpha_evidence()])
    with pytest.raises(UnsupportedClaimError):
        build_explain_response(ctx, payload("Produtividade de 12,500 t/ha."))
    assert build_explain_response(ctx, payload("Produtividade de 12,500 t/ha.", ("e2",))).evidences
    ctx = context([money_evidence(), calculation_evidence()])
    result = build_explain_response(ctx, payload("Referência R$ 5.000,00.", ("e3",)))
    assert [item.evidence_id for item in result.evidences] == ["e3", "e1"]


def test_limitation_do_modelo_nao_pode_escapar_da_validacao():
    with pytest.raises(UnsupportedClaimError):
        build_explain_response(
            context(), payload("Referência R$ 5.000,00.", limitations=["Chance de 90%."])
        )


def test_url_citada_e_exata_e_digitos_da_url_nao_viram_metricas():
    item = alpha_evidence()
    item["source"]["source_url"] = "https://example.org/Data/2099/yield"
    ctx = context([item])
    assert build_explain_response(
        ctx, payload("Fonte: https://example.org/Data/2099/yield.", ("e2",))
    ).evidences
    for answer in (
        "Fonte: https://inventada.example/dado.",
        "Fonte: https://example.org/data/2099/yield.",
        "O total é 2099.",
        "Fonte: www.inventada.example.",
        "Fonte: ftp://example.org/dado.",
    ):
        with pytest.raises(UnsupportedClaimError):
            build_explain_response(ctx, payload(answer, ("e2",)))
    with pytest.raises(UnsupportedClaimError):
        build_explain_response(
            context([money_evidence(), item]),
            payload("Fonte: https://example.org/Data/2099/yield."),
        )


def test_texto_numerico_exige_passagem_original_sem_transformar_numero_em_metrica():
    item = alpha_evidence(value={"kind": "text", "value_text": "Foram analisadas 12 regiões."})
    assert build_explain_response(
        context([item]), payload("Foram analisadas 12 regiões.", ("e2",))
    ).evidences
    with pytest.raises(UnsupportedClaimError):
        build_explain_response(context([item]), payload("A conta tem 12 gastos.", ("e2",)))


@pytest.mark.parametrize(
    "answer",
    [
        "Saldo R$ 0,00.",
        "Há 0 gastos.",
        "O saldo é zero.",
        "Chance de 90%.",
        "Fonte https://inventada.example/.",
    ],
)
def test_sem_evidencias_nao_assume_zero_ou_inventa_dados(answer):
    with pytest.raises(UnsupportedClaimError):
        build_explain_response(context([]), payload(answer, ()))


def test_sem_citacoes_exige_alta_incerteza_e_limitacao_mesmo_com_contexto():
    assert build_explain_response(context([]), payload("Faltam evidências.", ())).evidences == []
    with pytest.raises(EvidenceReferenceError):
        build_explain_response(context(), payload("Faltam evidências.", (), uncertainty="baixa"))
    with pytest.raises(EvidenceReferenceError):
        build_explain_response(context(), payload("Faltam evidências.", (), limitations=[]))


def test_contexto_original_e_resposta_nao_sao_mutados():
    ctx = context([money_evidence(), alpha_evidence()])
    raw = payload("Referência R$ 5.000,00.")
    before_ctx, before_payload = ctx.model_dump_json(), raw.model_dump_json()
    response = build_explain_response(ctx, raw)
    assert response.evidences[0] is not ctx.evidences[0]
    assert ctx.model_dump_json() == before_ctx
    assert raw.model_dump_json() == before_payload


def test_mutacao_de_lista_ou_model_copy_nao_burla_citacoes():
    raw = payload("Referência R$ 5.000,00.")
    raw.evidence_ids.append("e1")
    with pytest.raises(EvidenceReferenceError):
        build_explain_response(context(), raw)
    with pytest.raises(EvidenceReferenceError):
        build_explain_response(context(), payload("Resposta", ("inexistente",)))


def test_contexto_e_revalidado_contra_lista_mutada():
    ctx = context()
    ctx.evidences.append(ctx.evidences[0])
    with pytest.raises(EvidenceContextError):
        build_explain_response(ctx, payload("Resposta"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("published_at", "2026-11-18T00:00:00Z"),
        ("ingested_at", "2026-11-18T00:00:00Z"),
        ("source_url", "file:///segredo"),
        ("revision_id", 0),
    ],
)
def test_revalida_fonte_e_datas_injetadas_depois_da_construcao(field, value):
    ctx = context([alpha_evidence()])
    source = ctx.evidences[0].source.model_copy(update={field: value})
    ctx.evidences[0] = ctx.evidences[0].model_copy(update={"source": source})
    with pytest.raises(EvidenceContextError) as caught:
        build_explain_response(ctx, payload("Resposta", ("e2",)))
    assert "segredo" not in str(caught.value)
    assert caught.value.__suppress_context__


def test_modelo_nao_pode_fabricar_evidencia_para_validar_numero_inventado():
    data = {
        "answer": "Saldo R$ 999,00.",
        "evidence_ids": ["e1"],
        "uncertainty": "alta",
        "limitations": [],
        "evidences": [money_evidence(value={"kind": "money", "amount_cents": 99900})],
    }
    with pytest.raises(ValidationError):
        LLMPayload.model_validate(data)
    del data["evidences"]
    with pytest.raises(UnsupportedClaimError):
        build_explain_response(context(), LLMPayload.model_validate(data))


def test_metadados_e_limitacoes_temporais_originais_sao_preservados():
    item = alpha_evidence()
    item["source"]["published_at_estimated"] = True
    item["source"]["ingested_at"] = "2026-11-17T12:00:00.500Z"
    ctx = context([item])
    response = build_explain_response(ctx, payload("Produtividade de 12,500 t/ha.", ("e2",)))
    assert any("ilustrativa" in text for text in response.limitations)
    assert any("após o corte" in text for text in response.limitations)
    assert response.evidences[0].source.signal_id == ctx.evidences[0].source.signal_id


@pytest.mark.parametrize(
    "answer",
    ["Contagem: .3.", "Contagem: ,3.", "Contagem: - 3.", "Contagem: + 3.", "Data: -2026-11-17."],
)
def test_prefixos_nao_podem_mudar_o_significado_do_literal(answer):
    item = money_evidence(value={"kind": "integer", "value_int": 3, "unit": "count"})
    with pytest.raises(UnsupportedClaimError):
        build_explain_response(context([item]), payload(answer))


def test_revalidacao_nao_expoe_warnings_com_dados_de_modelo_adulterado(recwarn):
    ctx = context([alpha_evidence()])
    source = ctx.evidences[0].source.model_copy(update={"source_url": "file:///DADO-RESERVADO"})
    ctx.evidences[0] = ctx.evidences[0].model_copy(update={"source": source})
    with pytest.raises(EvidenceContextError) as caught:
        build_explain_response(ctx, payload("Resposta", ("e2",)))
    assert not recwarn.list
    assert "DADO-RESERVADO" not in str(caught.value)


def test_snapshot_finance_e_corte_sao_revalidados_sem_usar_estado_atual():
    ctx = context()
    source = ctx.evidences[0].source.model_copy(update={"recorded_at": "2026-11-18T00:00:00Z"})
    ctx.evidences[0] = ctx.evidences[0].model_copy(update={"source": source})
    with pytest.raises(EvidenceContextError):
        build_explain_response(ctx, payload("Referência R$ 5.000,00."))
