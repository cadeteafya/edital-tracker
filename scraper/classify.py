from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Kind = Literal["edital_launch", "update", "concurso", "skip"]


@dataclass
class Classification:
    kind: Kind
    reason: str


LAUNCH_PATTERNS = [
    r"divulg(?:a|ou|ada|ado)\s+(?:o\s+)?edital",
    r"public(?:a|ou|ado|ada)\s+(?:o\s+)?edital",
    r"edital\s+(?:est[aá])?\s*divulgad",
    r"edital\s+(?:est[aá])?\s*publicad",
    r"edital\s+(?:est[aá])?\s*lan[çc]ad",
    r"lan[çc](?:a|ou)\s+(?:o\s+)?edital",
    r"saiu\s+o\s+edital",
    r"liber(?:a|ou)\s+(?:o\s+)?edital",
    r"abre\s+inscri[çc][õo]es",
    r"abertas\s+as\s+inscri[çc][õo]es",
    r"recebe\s+inscri[çc][õo]es",
    r"edital\s+(?:do|da|de|para)\b",
    r"edital\s+\d{4}",
]

UPDATE_PATTERNS = [
    r"atualiza[çc][ãa]o",
    r"retifica[çc][ãa]o",
    r"adiamento",
    r"prorroga(?:do|ção|cao)",
    r"confirma\s+(?:a\s+)?data",
    r"previs[ãa]o\s+de\s+edital",
    r"prev[êe]\s+(?:lan[çc]amento|edital)",
]

UPDATE_REFERS_TO_EXISTING = [
    r"retifica[çc][ãa]o\s+do?\s+edital",
    r"edital\s+retificad",
]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def classify(
    title: str,
    *,
    excerpt: str = "",
    categories: list[str] | None = None,
) -> Classification:
    categories = categories or []
    if "category-concursos" in categories and "category-noticias" not in categories:
        return Classification("concurso", "categoria concursos sem notícia")

    blob = _normalize(f"{title} {excerpt}")

    for pat in UPDATE_REFERS_TO_EXISTING:
        if re.search(pat, blob):
            return Classification("update", f"retificação detectada: {pat}")

    for pat in LAUNCH_PATTERNS:
        if re.search(pat, blob):
            return Classification("edital_launch", f"padrão de lançamento: {pat}")

    for pat in UPDATE_PATTERNS:
        if re.search(pat, blob):
            return Classification("update", f"padrão de atualização: {pat}")

    return Classification("skip", "sem padrão reconhecido")
