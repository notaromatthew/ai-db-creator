#!/usr/bin/env python3
"""Calcola e controlla l'hash dei prompt del backend (task 7.2#1).

Ogni modifica a un prompt cambia il suo hash. Il file `docs/prompt-hashes.json` registra gli hash
approvati: se un prompt cambia senza aggiornare il file, il controllo (e il test) fallisce.

Uso:
    python scripts/prompt_hashes.py            # controlla (codice di uscita 1 se ci sono differenze)
    python scripts/prompt_hashes.py --write    # aggiorna docs/prompt-hashes.json

Dopo `--write` si aggiunge una voce al changelog (docs/15-ai-agent-changelog.md) con i nuovi hash.

Cosa conta come prompt: le costanti di modulo il cui nome contiene "PROMPT" e ogni chiamata a
`ChatPromptTemplate.from_messages(...)` dentro le funzioni. L'hash e' calcolato sull'albero sintattico
(AST) del valore, quindi spazi, commenti e a capo del codice non lo cambiano: lo cambia solo il testo.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HASH_FILE = ROOT / "docs" / "prompt-hashes.json"
SOURCES = (
    "backend/app/core/llm.py",
    "backend/app/services/chat_service.py",
    "backend/app/services/population_service.py",
    "backend/app/services/schema_service.py",
    "backend/app/services/pdf_ocr.py",
)
ALGORITHM = "sha256 dell'AST (ast.dump) del valore del prompt"


def _digest(node: ast.AST) -> str:
    return hashlib.sha256(ast.dump(node, annotate_fields=True, include_attributes=False).encode("utf-8")).hexdigest()


def _is_template_call(node: ast.AST) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "from_messages"
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "ChatPromptTemplate")


def collect_prompts(root: Path = ROOT) -> dict[str, str]:
    """Restituisce {"file::NOME": hash} per tutti i prompt trovati nei file sorgente."""
    found: dict[str, str] = {}
    for relative in SOURCES:
        path = root / relative
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.Assign) and node.value is not None:
                for target in node.targets:
                    if isinstance(target, ast.Name) and "PROMPT" in target.id.upper():
                        found[f"{relative}::{target.id}"] = _digest(node.value)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                    and "PROMPT" in node.target.id.upper() and node.value is not None:
                found[f"{relative}::{node.target.id}"] = _digest(node.value)
        for function in ast.walk(tree):
            if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                counter = 0
                for inner in ast.walk(function):
                    if _is_template_call(inner):
                        counter += 1
                        found[f"{relative}::{function.name}#{counter}"] = _digest(inner)
    return dict(sorted(found.items()))


def load_recorded(path: Path = HASH_FILE) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("prompts", {})


def diff(current: dict[str, str], recorded: dict[str, str]) -> list[str]:
    problems = []
    for key in sorted(set(current) | set(recorded)):
        if key not in recorded:
            problems.append(f"prompt nuovo non registrato: {key}")
        elif key not in current:
            problems.append(f"prompt registrato ma non piu' presente: {key}")
        elif current[key] != recorded[key]:
            problems.append(f"prompt modificato: {key}")
    return problems


def write(current: dict[str, str], path: Path = HASH_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"algorithm": ALGORITHM, "prompts": current}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hash dei prompt del backend.")
    parser.add_argument("--write", action="store_true", help="aggiorna docs/prompt-hashes.json")
    args = parser.parse_args(argv)
    current = collect_prompts()
    if args.write:
        write(current)
        print(f"Scritti {len(current)} hash in {HASH_FILE.relative_to(ROOT)}")
        print("Ricorda: registra la modifica nel changelog (docs/15-ai-agent-changelog.md).")
        return 0
    problems = diff(current, load_recorded())
    if problems:
        print("Gli hash dei prompt non corrispondono a docs/prompt-hashes.json:")
        for problem in problems:
            print(f"  - {problem}")
        print("Se la modifica e' voluta: python scripts/prompt_hashes.py --write e voce nel changelog.")
        return 1
    print(f"Hash dei prompt coerenti ({len(current)} prompt).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
