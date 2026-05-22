from __future__ import annotations

import os
import re

PROMPT = (
    "Reescreva o título da notícia em português brasileiro de forma objetiva, "
    "mais curta e direta, preservando o nome da instituição, o ano e o tipo de "
    "seleção (residência médica, prova de título, etc). Retorne SOMENTE o novo "
    "título, sem aspas, sem marcações. Máximo 110 caracteres."
)


def _heuristic_rewrite(title: str) -> str:
    t = re.sub(r"\s+", " ", title).strip()
    replacements = [
        (r"\bconfira o edital\b", ""),
        (r"\bconfira o documento\b", ""),
        (r";\s*confira[^.;]+", ""),
        (r"\bConfira datas e como se inscrever\b", ""),
        (r"\binscri[çc][õo]es e como participar\b", "inscrições abertas"),
        (r"\bAssocia[çc][ãa]o Brasileira de Medicina de Emerg[êe]ncia\b", "ABRAMEDE"),
        (r"\s+,", ","),
        (r"\s+;", ";"),
        (r"\s+\.", "."),
        (r";\s*$", ""),
        (r",\s*$", ""),
    ]
    for pat, rep in replacements:
        t = re.sub(pat, rep, t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" ,;:.")
    return t


def rewrite_title(original: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _heuristic_rewrite(original)
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=PROMPT,
            messages=[{"role": "user", "content": f"Título original: {original}"}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()
        text = text.strip(" \"'`")
        if not text:
            return _heuristic_rewrite(original)
        return text
    except Exception as exc:  # noqa: BLE001
        print(f"  [rewrite] LLM falhou ({exc!r}); usando heurística")
        return _heuristic_rewrite(original)
