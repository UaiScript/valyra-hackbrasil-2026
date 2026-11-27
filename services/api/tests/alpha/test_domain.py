"""Regras puras do Alpha: leitura do SGS, publicação estimada, corte e sinais."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from valyra.alpha.domain import (
    SGS_SERIES,
    SgsFormatError,
    estimated_publication,
    format_decimal,
    ipca_signal,
    next_revision,
    parse_sgs,
    selic_signal,
    visible_at,
)

SELIC, _CDI, IPCA = SGS_SERIES


@dataclass
class Row:
    signal_key: str
    revision_id: int
    observation_date: date
    value: Decimal | None
    published_at: datetime


def at(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 11, day, hour, tzinfo=UTC)


def test_parse_sgs_aceita_ponto_e_virgula_e_ordena():
    payload = [
        {"data": "02/10/2026", "valor": "0,055131"},
        {"data": "01/10/2026", "valor": "0.055131"},
    ]
    assert parse_sgs(payload) == [
        (date(2026, 10, 1), Decimal("0.055131")),
        (date(2026, 10, 2), Decimal("0.055131")),
    ]


@pytest.mark.parametrize(
    "payload",
    [{}, [{"data": "2026-10-01", "valor": "1"}], [{"data": "01/10/2026", "valor": "abc"}],
     [{"data": "01/10/2026", "valor": 1.5}], [{"data": "01/10/2026", "valor": "NaN"}]],
)  # fmt: skip
def test_parse_sgs_recusa_formato_inesperado(payload):
    with pytest.raises(SgsFormatError):
        parse_sgs(payload)


def test_publicacao_estimada_erra_para_depois():
    # IPCA de outubro: dia 12 de novembro ao meio-dia em São Paulo (15h UTC).
    assert estimated_publication(IPCA, date(2026, 10, 1)) == datetime(2026, 11, 12, 15, tzinfo=UTC)
    assert estimated_publication(IPCA, date(2026, 12, 1)) == datetime(2027, 1, 12, 15, tzinfo=UTC)
    assert estimated_publication(SELIC, date(2026, 11, 26)) == datetime(
        2026, 11, 27, 15, tzinfo=UTC
    )


def test_corte_escolhe_revisao_publicada_ate_o_instante():
    rows = [
        Row("k:2026-10-01", 1, date(2026, 10, 1), Decimal("0.5"), at(10)),
        Row("k:2026-10-01", 2, date(2026, 10, 1), Decimal("0.6"), at(20)),
        Row("k:2026-11-01", 1, date(2026, 11, 1), Decimal("0.4"), at(25)),
    ]
    before = visible_at(rows, at(15))
    assert {k: r.value for k, r in before.items()} == {"k:2026-10-01": Decimal("0.5")}
    after = visible_at(rows, at(26))
    assert after["k:2026-10-01"].revision_id == 2 and "k:2026-11-01" in after


def test_proxima_revisao_so_quando_o_valor_muda():
    latest = Row("k", 3, date(2026, 10, 1), Decimal("15.00"), at(1))
    assert next_revision(None, Decimal("1")) == 1
    assert next_revision(latest, Decimal("15")) is None
    assert next_revision(latest, Decimal("14.75")) == 4


def test_format_decimal_sem_notacao_cientifica():
    assert format_decimal(Decimal("15.00")) == "15"
    assert format_decimal(Decimal("1E-7")) == "0.0000001"
    assert format_decimal(Decimal("-0.00")) == "0"


def test_sinal_selic_detecta_ultima_mudanca_e_estabilidade():
    rows = [
        Row(f"{SELIC.key}:2026-11-0{d}", 1, date(2026, 11, d), Decimal(v), at(d))
        for d, v in [(1, "15"), (2, "15"), (3, "14.75"), (4, "14.75")]
    ]
    change = selic_signal(SELIC, rows)
    assert change.title == "Selic meta caiu de 15 % ao ano para 14,75 % ao ano"
    assert change.observation_date == date(2026, 11, 3)
    assert change.evidence_keys == (rows[1].signal_key, rows[2].signal_key)
    stable = selic_signal(SELIC, rows[:2])
    assert stable.title == "Selic meta estável em 15 % ao ano"


def test_sinal_ipca_compara_com_mes_anterior():
    rows = [
        Row(f"{IPCA.key}:2026-09-01", 1, date(2026, 9, 1), Decimal("0.48"), at(1)),
        Row(f"{IPCA.key}:2026-10-01", 1, date(2026, 10, 1), Decimal("0.09"), at(2)),
    ]
    signal = ipca_signal(IPCA, rows)
    assert signal.title == "IPCA de outubro de 2026 abaixo do mês anterior"
    assert ipca_signal(IPCA, rows[:1]) is None
