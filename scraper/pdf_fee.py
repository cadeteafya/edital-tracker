"""Fallback da taxa de inscrição: lê o PDF do edital linkado no artigo.

Usado apenas quando o texto do artigo não informa a taxa. O PDF é baixado e
lido inteiramente em memória — nada é gravado em disco.

Regras conservadoras: na dúvida, retorna None (o site exibe "Confirmar").
  - Página com mais de um edital (acesso direto + R+, etc.) → None.
  - Valores diferentes para a taxa (sócio x não sócio, por programa...) → None.
"""
from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

import httpx
import pymupdf
from bs4 import Tag

pymupdf.TOOLS.mupdf_display_errors(False)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 EditalTracker/0.2"
)
MAX_PDF_BYTES = 25 * 1024 * 1024
MAX_PAGES = 30  # a taxa aparece nas primeiras páginas; limita tempo em PDFs de 200 páginas
TIMEOUT_SECONDS = 45.0

# ---------------------------------------------------------------------------
# Botão do edital no artigo
# ---------------------------------------------------------------------------

# Botões que acompanham o edital mas não são um edital
_NOT_EDITAL_BUTTON = re.compile(
    r"retifica|errata|cronograma|comunicado|quadro|resultado|gabarito", re.I
)


def _is_pdf(href: str) -> bool:
    return urlparse(href).path.lower().endswith(".pdf")


def find_edital_pdf(content: Tag) -> str | None:
    """URL do PDF do edital, se houver exatamente um botão de edital no artigo."""
    editais: list[str] = []
    for a in content.select("a.wp-block-button__link[href]"):
        href = a["href"].strip()
        label = a.get_text(" ", strip=True)
        if not _is_pdf(href) or not re.search(r"edital", label, re.I):
            continue
        if _NOT_EDITAL_BUTTON.search(label):
            continue
        if href not in editais:
            editais.append(href)
    return editais[0] if len(editais) == 1 else None


# ---------------------------------------------------------------------------
# Extração da taxa no texto do PDF
# ---------------------------------------------------------------------------

_NUM = r"(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)"
_MONEY = r"R\$\s*" + _NUM
_NO_RS = r"(?:(?!R\$).)"  # qualquer char que não inicie outro R$

# Frases que falam explicitamente do valor da inscrição
_STRONG_PATTERNS = [
    # "taxa de inscrição ... R$ X"
    re.compile(r"taxas?\s+de\s+inscri[çc][ãa]o" + _NO_RS + r"{0,120}?" + _MONEY, re.I),
    # "pagamento da inscrição no valor de R$ X" / "preço público de inscrição ... valor de R$ X"
    re.compile(r"inscri[çc][ãa]o" + _NO_RS + r"{0,60}?\bvalor\b" + _NO_RS + r"{0,30}?" + _MONEY, re.I),
    # "valor de inscrição R$ X" / "O valor da inscrição será de R$ X"
    re.compile(r"valor\s+d[aeo]s?\s+inscri[çc][ãa]o" + _NO_RS + r"{0,40}?" + _MONEY, re.I),
]
# Frases genéricas: "taxa ... R$ X" e "R$ X ... taxa"
_WEAK_PATTERNS = [
    re.compile(r"\btaxa\b" + _NO_RS + r"{0,120}?" + _MONEY, re.I),
    re.compile(_MONEY + _NO_RS + r"{0,50}?\btaxa\b", re.I),
]
# Tabela (padrão CONSESP): coluna "Taxa de Insc. (R$)" seguida da coluna "Duração"
_TABLE_HEADER = re.compile(r"taxa\s+de\s+insc\.?", re.I)
_TABLE_VALUE = re.compile(r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})\s+0?\d\s+anos\b", re.I)
_TABLE_REGION = 4000

# Contextos em que um R$ perto de "taxa" NÃO é a taxa de inscrição principal
REJECT_CTX = re.compile(
    r"renda|sal[aá]rio|per\s*capita|bolsa|remunera|aux[ií]lio|multa|mensalidade"
    r"|treineir|recurs|desconto|reembols|cotista|redu[çc][ãa]o|meia|devolu"
    r"|emiss[ãa]o|segunda\s+via|certificado",
    re.I,
)
# Taxa diferenciada por categoria (provas de título): sócio x não sócio
_TIER_CTX = re.compile(r"s[óo]cios?\b|associad|\bmembros?\b", re.I)

# Outro valor logo após a taxa ("1. R$ 500 para X; 2. R$ 750 para Y") = preço por categoria
_FOLLOW_MONEY = re.compile(_MONEY)
_FOLLOW_WINDOW = 250
# ...exceto quando é só o detalhamento do total ("sendo um depósito de R$ 612")
_FOLLOW_REJECT = re.compile(r"\bsendo\b|dep[óo]sito|parcela", re.I)

MIN_FEE, MAX_FEE = 30.0, 6000.0
MAX_TABLE_FEE = 3000.0  # em tabela, valores altos costumam ser a bolsa (R$ 4.106,09)


def _to_float(raw: str) -> float:
    return float(raw.replace(".", "").replace(",", "."))


def _fmt(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace(" ", " ")
    text = re.sub(r"\.{4,}|…+", " ", text)                  # linhas pontilhadas de sumário/tabela
    text = re.sub(r"R\s+\$", "R$", text)                    # "R $ 500" -> "R$ 500"
    text = re.sub(r"(\d)\s+,\s*(\d{2})\b", r"\1,\2", text)  # "500 ,00" -> "500,00"
    return re.sub(r"\s+", " ", text)


def _candidates(text: str) -> list[tuple[float, str, bool, str]]:
    """(valor, nível, tem_outro_valor_em_seguida, trecho). nível ∈ forte/tabela/fraco."""
    out: list[tuple[float, str, bool, str]] = []

    def add(m: re.Match, level: str, max_fee: float = MAX_FEE) -> None:
        if REJECT_CTX.search(text[max(0, m.start() - 40): m.end()]):
            return
        v = _to_float(m.group(1))
        if not (MIN_FEE <= v <= max_fee):
            return
        multi = False
        if level != "tabela":
            for f in _FOLLOW_MONEY.finditer(text, m.end(), m.end() + _FOLLOW_WINDOW):
                ctx = text[max(0, f.start() - 40): f.end() + 70]
                if _FOLLOW_REJECT.search(ctx) or REJECT_CTX.search(ctx):
                    continue
                fv = _to_float(f.group(1))
                if fv != v and MIN_FEE <= fv <= max_fee:
                    multi = True
                    break
        out.append((v, level, multi, text[max(0, m.start() - 80): m.end() + 80]))

    for rx in _STRONG_PATTERNS:
        for m in rx.finditer(text):
            add(m, "forte")
    for h in _TABLE_HEADER.finditer(text):
        for m in _TABLE_VALUE.finditer(text, h.end(), h.end() + _TABLE_REGION):
            add(m, "tabela", MAX_TABLE_FEE)
    for rx in _WEAK_PATTERNS:
        for m in rx.finditer(text):
            add(m, "fraco")
    return out


def fee_from_text(text: str) -> tuple[str | None, str]:
    """Retorna (taxa, motivo). Usa o nível mais forte disponível; na dúvida, None."""
    cands = _candidates(_normalize(text))
    if any(_TIER_CTX.search(c[3]) for c in cands):
        return None, "valores por categoria (sócio/não sócio)"
    for level in ("forte", "tabela", "fraco"):
        pool = [c for c in cands if c[1] == level]
        if not pool:
            continue
        values = sorted({c[0] for c in pool})
        if len(values) > 1:
            return None, f"valores diferentes {[_fmt(v) for v in values]}"
        if any(c[2] for c in pool):
            return None, "valores por categoria"
        return _fmt(values[0]), level
    return None, "taxa não encontrada no PDF"


def fee_from_pdf(url: str) -> tuple[str | None, str]:
    """Baixa o PDF em memória e extrai a taxa. Nunca levanta exceção."""
    try:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=TIMEOUT_SECONDS,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.content
        if len(data) > MAX_PDF_BYTES:
            return None, f"PDF grande demais ({len(data) // 1024} KB)"
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            text = "\n".join(doc[i].get_text() for i in range(min(MAX_PAGES, doc.page_count)))
    except Exception as exc:  # noqa: BLE001
        return None, f"falha ao ler PDF: {type(exc).__name__}"
    if len(text.strip()) < 200:
        return None, "PDF sem texto (escaneado?)"
    return fee_from_text(text)
