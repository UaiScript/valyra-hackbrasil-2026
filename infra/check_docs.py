"""Confere contexto e links locais sem instalar ferramentas de documentação."""

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    errors = []
    agents = ROOT / "AGENTS.md"
    if len(agents.read_text(encoding="utf-8").splitlines()) > 150:
        errors.append("AGENTS.md ultrapassa 150 linhas")
    for folder in [ROOT, ROOT / "services/api"]:
        if (folder / "CLAUDE.md").read_text(encoding="utf-8").strip() != "@AGENTS.md":
            errors.append(f"CLAUDE.md inválido em {folder}")
    ignored = {"node_modules", ".venv", ".git", ".tools", "dist", "test-results"}
    for file in ROOT.rglob("*.md"):
        if any(part in ignored for part in file.relative_to(ROOT).parts):
            continue
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", file.read_text(encoding="utf-8")):
            if target.startswith(("https:", "http:", "mailto:", "#")):
                continue
            path = unquote(target.split("#", 1)[0].strip("<>"))
            if path and not (file.parent / path).exists():
                errors.append(f"{file.relative_to(ROOT)}: link ausente {path}")
    if errors:
        raise SystemExit("\n".join(errors))
    print("Contexto, limite de linhas, CLAUDE.md e links locais aprovados")


if __name__ == "__main__":
    main()
