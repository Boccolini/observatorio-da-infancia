"""IBGE population estimates by UF and single-year age (under-5).

Strategy:
  - For 2010 census + projections, IBGE publishes population by UF and age
    in SIDRA. The single-year-of-age cuts (0, 1, 2, 3, 4) are available in
    Tabela 7358 (Projeção da População 2018) and historical estimates in
    Tabela 6579.
  - Calling SIDRA for each (UF x year x age) combination is straightforward
    via the JSON API.

API URL pattern:
    https://apisidra.ibge.gov.br/values/t/{tabela}/n3/all/v/{var}/p/{periodos}/c{classifier}/{ages}

For under-5 we request idade simples (classification 287) for ages 0..4.

Notes:
  - SIDRA returns a header row with field descriptors which we discard.
  - When a year is not available in projecoes (eg. 2026+), we fall back to
    the most recent year available.
"""

from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd
import requests

from .config import IBGE_SIDRA_BASE
from .geo import UF_INFO

log = logging.getLogger(__name__)

# Tabela 7358 - Projeção da População 2018 (n3 = UF, v/93 = População residente,
# c287 = Idade simples, c2 = Sexo).  We request total sex (=0).
TABELA_PROJECAO = "7358"
VAR_POPULACAO = "93"
CLASS_IDADE = "287"

# IBGE-SIDRA codes for single-year ages 0..4 in classification 287.
# Mapping: age -> SIDRA category code.
AGES_UNDER_5 = {
    0: "100436",
    1: "100437",
    2: "100438",
    3: "100439",
    4: "100440",
}


def _request_sidra(periodos: list[int]) -> pd.DataFrame:
    periodos_str = ",".join(str(p) for p in periodos)
    ages_str = ",".join(AGES_UNDER_5.values())
    url = (
        f"{IBGE_SIDRA_BASE}/t/{TABELA_PROJECAO}/n3/all"
        f"/v/{VAR_POPULACAO}/p/{periodos_str}"
        f"/c{CLASS_IDADE}/{ages_str}/c2/0"
        f"?formato=json"
    )
    log.info("SIDRA request: %s", url)
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    data = r.json()
    # First record is the header
    header, *rows = data
    df = pd.DataFrame(rows)
    # Map by header - SIDRA returns Portuguese keys (D1N = territory name, D2C = period code, V = value, etc.)
    return df


def _parse_sidra(raw: pd.DataFrame) -> pd.DataFrame:
    age_code_to_year = {v: k for k, v in AGES_UNDER_5.items()}
    rows = []
    for _, r in raw.iterrows():
        try:
            uf_code = f"{int(r['D1C']):02d}"
            ano = int(r["D2C"])
            age_code = r["D3C"]
            value = int(r["V"]) if r["V"] not in ("..", "-", "") else 0
        except (KeyError, ValueError, TypeError):
            continue
        age = age_code_to_year.get(age_code)
        if age is None:
            continue
        rows.append({"ano": ano, "uf_code": uf_code, "idade": age, "populacao": value})
    return pd.DataFrame(rows)


def extract_population(years: Iterable[int]) -> pd.DataFrame:
    """Return long-format population: ano, uf_code, idade, populacao (ages 0..4)."""
    raw = _request_sidra(list(years))
    df = _parse_sidra(raw)
    return df


def aggregate_by_age_group(pop: pd.DataFrame) -> pd.DataFrame:
    """Convert single-age (0..4) into faixa: menor_1_ano, 1_a_4_anos."""
    pop = pop.copy()
    pop["faixa"] = pop["idade"].map(lambda a: "menor_1_ano" if a == 0 else "1_a_4_anos")
    agg = (
        pop.groupby(["ano", "uf_code", "faixa"])["populacao"]
        .sum()
        .reset_index()
    )
    # Add region/sigla
    agg["uf_sigla"] = agg["uf_code"].map(lambda c: UF_INFO[c][0])
    agg["regiao"] = agg["uf_code"].map(lambda c: UF_INFO[c][2])
    return agg
