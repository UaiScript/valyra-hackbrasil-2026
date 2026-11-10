"""Gera o contrato a partir da aplicação; não acessa PostgreSQL."""

import json

from valyra.core.config import PROJECT_ROOT
from valyra.main import create_app


def main() -> None:
    destination = PROJECT_ROOT / "packages/contracts/openapi.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
