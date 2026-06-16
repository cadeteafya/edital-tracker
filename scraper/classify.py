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

# Concursos públicos municipais/estaduais para cargos médicos — NÃO são residência nem título
CONCURSO_PUBLICO_PATTERNS = [
    r"concurso\s+p[uú]blico",
    r"concurso\s+m[eé]dico\b",           # "concurso médico em X" — emprego, não residência
    r"sal[aá]rios?\s+de\s+at[eé]",       # "salários de até R$" — sinal exclusivo de emprego
    r"\d+\s+vagas?\s+para\s+m[eé]dico",
    r"vagas?\s+(?:de\s+|para\s+)?m[eé]dico(?:s)?\b",
    r"abre\s+(?:processo\s+seletivo|concurso)\s+(?:com\s+)?\d+\s+vagas",
    r"inscri[çc][õo]es?\s+para\s+concurso\s+na\s+[áa]rea\s+m[eé]dica",
    r"prefeitura\s+de\s+\w+.{0,40}\bvagas?\b",
    r"\bperito\s+m[eé]dico\b",
    r"\bauditor\s+m[eé]dico\b",
    r"cargo\s+(?:de\s+)?m[eé]dico",
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

    # Descarta qualquer artigo de concurso público — independente de categoria
    # (artigos de concurso às vezes têm category-noticias também)
    if "category-concursos" in categories:
        return Classification("concurso", "categoria concursos")

    blob = _normalize(f"{title} {excerpt}")

    # Bloco explícito de concurso público por conteúdo — roda ANTES dos launch patterns
    # para não deixar "confira o edital" do concurso vazar como edital_launch
    for pat in CONCURSO_PUBLICO_PATTERNS:
        if re.search(pat, blob):
            return Classification("concurso", f"concurso público detectado: {pat}")

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
