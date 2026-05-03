"""SIH-SUS extraction: hospitalizations with primary diagnosis CID-10 A09.

Files: ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/RD<UF><AAMM>.dbc
Field reference (RD - Reduzida AIH):
    DIAG_PRINC : 4-char CID-10 of the principal diagnosis
    MUNIC_RES  : 6-digit IBGE municipality of patient residence
    IDADE      : age value (interpretation depends on COD_IDADE)
    COD_IDADE  : 1=days, 2=months, 3=years, 4=days/decades, 5=centuries
    DT_INTER   : admission date (YYYYMMDD as string)
    MORTE      : 1 = death during the AIH (used for SIH-derived mortality;
                 we use SIM as the canonical death source)

We aggregate AIH counts (one row per AIH) by year x UF-residence x age group.
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

SIH_BASE = f"{DATASUS_BASE}/SIHSUS/200801_/Dados"
COLUMNS = ["DIAG_PRINC", "MUNIC_RES", "IDADE", "COD_IDADE", "DT_INTER", "MORTE"]


def _file_url(uf_sigla: str, year: int, month: int) -> str:
    yy = year % 100
    return f"{SIH_BASE}/RD{uf_sigla}{yy:02d}{month:02d}.dbc"


def _classify_age(idade: int | float | str | None, cod: int | float | str | None) -> str | None:
    """Return one of {'menor_1_ano', '1_a_4_anos', None} - None means out of scope."""
    if idade is None or cod is None:
        return None
    try:
        idade_i = int(idade)
        cod_i = int(cod)
    except (TypeError, ValueError):
        return None

    # COD_IDADE: 0/1/2 = subdivisions of "less than 1 year"
    #   0 = horas, 1 = dias, 2 = meses
    # 3 = anos, 4 = dezenas/centenas (treat as years)
    if cod_i in (0, 1, 2):
        return "menor_1_ano"
    if cod_i == 3:
        if idade_i < 1:
            return "menor_1_ano"
        if 1 <= idade_i <= 4:
            return "1_a_4_anos"
    return None


def extract_sih_year(year: int, force: bool = False) -> pd.DataFrame:
    """Aggregate one calendar year of SIH RD files, filtered to CID A09."""
    pieces: list[pd.DataFrame] = []
    for sigla in UF_SIGLAS:
        for month in range(1, 13):
            url = _file_url(sigla, year, month)
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
            mask = df["DIAG_PRINC"].astype(str).str.startswith(CID10_PREFIX)
            df = df.loc[mask].copy()
            if df.empty:
                continue
            df["faixa"] = [
                _classify_age(i, c) for i, c in zip(df["IDADE"], df["COD_IDADE"])
            ]
            df = df.dropna(subset=["faixa"])
            if df.empty:
                continue
            df["uf_code"] = df["MUNIC_RES"].apply(municipio_to_uf_code)
            df["uf_sigla"] = df["uf_code"].apply(sigla_from_uf_code)
            df["regiao"] = df["uf_code"].apply(regiao_from_uf_code)
            df["ano"] = year
            pieces.append(df[["ano", "uf_code", "uf_sigla", "regiao", "faixa"]])
            log.info(
                "SIH %s/%d-%02d: %d AIH A09 (parsed in %.1fs)",
                sigla, year, month, len(df), time.perf_counter() - t0,
            )

    if not pieces:
        return pd.DataFrame(columns=["ano", "uf_code", "uf_sigla", "regiao", "faixa", "internacoes"])

    cat = pd.concat(pieces, ignore_index=True)
    agg = (
        cat.groupby(["ano", "uf_code", "uf_sigla", "regiao", "faixa"])
        .size()
        .reset_index(name="internacoes")
    )
    return agg


def extract_sih(years: list[int], force: bool = False) -> pd.DataFrame:
    out = [extract_sih_year(y, force=force) for y in years]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
