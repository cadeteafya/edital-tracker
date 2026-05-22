from __future__ import annotations

import re

KNOWN_SOURCES: list[tuple[str, str, list[str]]] = [
    ("Hospital Sírio-Libanês", "Sírio-Libanês", [r"s[íi]rio[- ]liban[êe]s"]),
    ("FEBRASGO", "FEBRASGO", [r"febrasgo", r"tpi-?go"]),
    ("ABRAMEDE — Medicina de Emergência", "ABRAMEDE", [r"abramede", r"medicina de emerg[êe]ncia"]),
    ("AMRIGS", "AMRIGS", [r"amrigs"]),
    ("ENARE", "ENARE", [r"\benare\b"]),
    ("USP — FMUSP", "FMUSP", [r"\bfmusp\b", r"hcfmusp"]),
    ("UNICAMP", "UNICAMP", [r"unicamp"]),
    ("UNIFESP", "UNIFESP", [r"unifesp"]),
    ("AREMG — PSU-MG", "PSU-MG", [r"\baremg\b", r"psu-?mg"]),
    ("SUS-SP", "SUS-SP", [r"sus[- ]sp", r"resid[êe]ncia.*s[ãa]o paulo"]),
    ("Hospital das Clínicas", "Hospital das Clínicas", [r"hospital das cl[íi]nicas"]),
    ("Santa Casa", "Santa Casa", [r"santa casa"]),
    ("Albert Einstein", "Einstein", [r"albert einstein", r"\beinstein\b"]),
    ("IAMSPE", "IAMSPE", [r"iamspe"]),
    ("Beneficência Portuguesa", "Beneficência Portuguesa", [r"benefic[êe]ncia\s+portuguesa"]),
]


def detect_source(title: str, url: str) -> tuple[str, str]:
    blob = f"{title} {url}".lower()
    for name, short, patterns in KNOWN_SOURCES:
        for pat in patterns:
            if re.search(pat, blob):
                return name, short

    m = re.match(r"\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\s,:;]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\s,:;]+){0,3})", title)
    if m:
        short = m.group(1).strip()[:32]
        return short, short

    return "Estratégia MED", "Estratégia MED"


def detect_exam_year(title: str) -> int:
    matches = re.findall(r"\b(20\d{2})\b", title)
    if not matches:
        from datetime import date
        return date.today().year
    return max(int(y) for y in matches)
