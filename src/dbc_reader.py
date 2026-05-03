"""DBC -> DataFrame conversion using datasus-dbc + dbfread."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from dbfread import DBF

import datasus_dbc

log = logging.getLogger(__name__)


def dbc_to_dataframe(dbc_path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    """Decompress a DATASUS .dbc file and return its records as a DataFrame.

    Only ``columns`` are kept when provided, which dramatically reduces memory
    usage for large SIH files (millions of rows, dozens of fields).
    """
    dbf_path = dbc_path.with_suffix(".dbf")
    if not dbf_path.exists():
        log.debug("Decompressing %s", dbc_path.name)
        datasus_dbc.decompress(str(dbc_path), str(dbf_path))

    table = DBF(str(dbf_path), encoding="latin-1", load=False, raw=False)
    if columns is not None:
        keep = set(columns)
        rows = ({k: v for k, v in rec.items() if k in keep} for rec in table)
    else:
        rows = (rec for rec in table)
    df = pd.DataFrame(rows)
    return df
