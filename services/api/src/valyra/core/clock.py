"""Fonte única de "hoje" para os cálculos de negócio (ADR-0010, seção 2)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from valyra.core.config import get_settings

# Datas de negócio seguem o calendário de quem usa o produto; timestamps continuam em UTC.
BUSINESS_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def get_today() -> date:
    # DEMO_TODAY fixa a data da demonstração, para o resultado não depender do dia da apresentação.
    demo_today = get_settings().demo_today
    if demo_today is not None:
        return demo_today
    return datetime.now(BUSINESS_TIMEZONE).date()
