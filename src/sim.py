"""SIM (Sistema de Informações sobre Mortalidade) extraction.

Files: ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DORES/DO<UF><AAAA>.dbc

Field reference (Declaração de Óbito - DO):
    CAUSABAS    : underlying cause of death (CID-10, 4 char)
    CODMUNRES   : 6-digit IBGE municipality of residence
    IDADE       : 3-digit code where the leading digit indicates the unit:
                    0XX = ignored / non-applicable
                    1XX = minutes,    2XX = hours,    3XX = days
                    4XX = months,     5XX = years,    6XX = years (>100)
                  e.g. 410 = 10 months, 504 = 4 years
    DTOBITO     : death date

We aggregate death counts by year x UF-residence x age group, restricted to
CID-10 A09 as underlying cause.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd

from .config import CID10_PREFIX, DATASUS_BASE
from .dbc_reader import dbc_to_dataframe
from .downloader import download
from .geo import UF_SIGLAS, municipio_to_uf_code, regiao_from_uf_code, sigla_from_uf_code

log = logging.getLogger(__name__)

SIM_BASE = f"{DATASUS_BASE}/SIM/CID10/DORES"
COLUMNS = ["CAUSABAS", "CODMUNRES", "IDADE", "DTOBITO"]


def _file_url(uf_sigla: str, year: int) -> str:
    return f"{SIM_BASE}/DO{uf_sigla}{year:04d}.dbc"


def _classify_age(idade: str | int | float | None) -> str | None:
    if idade is None:
        return None
    try:
        s = f"{int(idade):03d}"
    except (TypeError, ValueError):
        return None
    unit, val = s[0], int(s[1:])
    # 1=min, 2=hour, 3=day, 4=month -> all under 1 year
    if unit in ("1", "2", "3", "4"):
        return "menor_1_ano"
    if unit == "5":
        if val == 0:
            return "menor_1_ano"  # SIM occasionally encodes <1y as 500
        if 1 <= val <= 4:
            return "1_a_4_anos"
    return None


def extract_sim_year(year: int, force: bool = False) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    for sigla in UF_SIGLAS:
        url = _file_url(sigla, year)
        try:
            local = download(url, force=force)
        except RuntimeError as exc:
            log.error("Failed: %s (%s)", url, exc)
            continue
        if local is None:
            continue

        t0 = time.perf_counter()
        df = dbc_to_dataframe(local, columns=COLUMNS)
        if df.empty:
            continue
        df = df[df["CAUSABAS"].astype(str).str.startswith(CID10_PREFIX)].copy()
        if df.empty:
            continue
        df["faixa"] = df["IDADE"].apply(_classify_age)
        df = df.dropna(subset=["faixa"])
        if df.empty:
            continue
        df["uf_code"] = df["CODMUNRES"].apply(municipio_to_uf_code)
        df["uf_sigla"] = df["uf_code"].apply(sigla_from_uf_code)
        df["regiao"] = df["uf_code"].apply(regiao_from_uf_code)
        df["ano"] = year
        pieces.append(df[["ano", "uf_code", "uf_sigla", "regiao", "faixa"]])
        log.info(
            "SIM %s/%d: %d óbitos A09 (parsed in %.1fs)",
            sigla, year, len(df), time.perf_counter() - t0,
        )

    if not pieces:
        return pd.DataFrame(columns=["ano", "uf_code", "uf_sigla", "regiao", "faixa", "obitos"])
    cat = pd.concat(pieces, ignore_index=True)
    return (
        cat.groupby(["ano", "uf_code", "uf_sigla", "regiao", "faixa"])
        .size()
        .reset_index(name="obitos")
    )


def extract_sim(years: list[int], force: bool = False) -> pd.DataFrame:
    out = [extract_sim_year(y, force=force) for y in years]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
