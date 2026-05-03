"""SINASC (Sistema de Informações sobre Nascidos Vivos) extraction.

Files: ftp.datasus.gov.br/dissemin/publicos/SINASC/NOV/DNRES/DN<UF><AAAA>.dbc
We aggregate live-birth counts by year x UF of residence (CODMUNRES).
"""

from __future__ import annotations

import logging
import time

import pandas as pd

from .config import DATASUS_BASE
from .dbc_reader import dbc_to_dataframe
from .downloader import download
from .geo import UF_SIGLAS, municipio_to_uf_code, regiao_from_uf_code, sigla_from_uf_code

log = logging.getLogger(__name__)

SINASC_BASE = f"{DATASUS_BASE}/SINASC/NOV/DNRES"
COLUMNS = ["CODMUNRES"]


def _file_url(uf_sigla: str, year: int) -> str:
    return f"{SINASC_BASE}/DN{uf_sigla}{year:04d}.dbc"


def extract_sinasc_year(year: int, force: bool = False) -> pd.DataFrame:
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
        df["uf_code"] = df["CODMUNRES"].apply(municipio_to_uf_code)
        df["uf_sigla"] = df["uf_code"].apply(sigla_from_uf_code)
        df["regiao"] = df["uf_code"].apply(regiao_from_uf_code)
        df["ano"] = year
        pieces.append(df[["ano", "uf_code", "uf_sigla", "regiao"]])
        log.info(
            "SINASC %s/%d: %d nascidos vivos (parsed in %.1fs)",
            sigla, year, len(df), time.perf_counter() - t0,
        )

    if not pieces:
        return pd.DataFrame(columns=["ano", "uf_code", "uf_sigla", "regiao", "nascidos_vivos"])
    cat = pd.concat(pieces, ignore_index=True)
    return (
        cat.groupby(["ano", "uf_code", "uf_sigla", "regiao"])
        .size()
        .reset_index(name="nascidos_vivos")
    )


def extract_sinasc(years: list[int], force: bool = False) -> pd.DataFrame:
    out = [extract_sinasc_year(y, force=force) for y in years]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
