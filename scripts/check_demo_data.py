"""Valida os contratos dos exemplos sem servidor, dependências ou dados financeiros reais."""

import json
from datetime import date
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parents[1] / 'apps' / 'web' / 'src' / 'data' / 'demo'
REFERENCE_DATE = date(2026, 11, 5)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def check() -> None:
    seen_ids: set[str] = set()
    for profile, prefix in [('personal', 'p-'), ('business', 'b-')]:
        data = json.loads((DEMO_DIR / f'{profile}.json').read_text(encoding='utf-8'))
        # bool é subclasse de int no Python; type estrito impede aceitar true como centavos.
        require(type(data['openingBalanceCents']) is int, f'{profile}: saldo deve usar centavos inteiros')
        for collection in ['transactions', 'commitments', 'radar']:
            require(bool(data[collection]), f'{profile}: lista vazia: {collection}')
            for item in data[collection]:
                identifier = item['id']
                require(identifier.startswith(prefix) and identifier not in seen_ids, f'ID inválido/duplicado: {identifier}')
                seen_ids.add(identifier)
                if collection == 'radar':
                    for key in ['title', 'topic', 'region', 'summary', 'context', 'limitation', 'premise']:
                        require(isinstance(item[key], str) and bool(item[key].strip()), f'{identifier}: campo vazio: {key}')
                    require(item['topic'] in data['interests'], f'{identifier}: tema fora do perfil')
                    continue
                amount = item['amountCents']
                require(type(amount) is int and abs(amount) <= 9_007_199_254_740_991, f'{identifier}: centavos fora do contrato JS')
                item_date = date.fromisoformat(item['date'])
                if collection == 'commitments':
                    require(amount > 0 and item_date > REFERENCE_DATE, f'{identifier}: compromisso deve ser uma saída futura')
                else:
                    require(amount != 0 and date(2026, 11, 1) <= item_date <= REFERENCE_DATE, f'{identifier}: lançamento fora do período demonstrado')
        require(len(data['interests']) == len(set(data['interests'])), f'{profile}: interesses duplicados')
        print(f'OK: {profile} — centavos, datas, IDs e temas consistentes.')


if __name__ == '__main__':
    check()
