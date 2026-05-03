"""Rate calculations.

Definitions:
  - Internações em < 1 ano: por 1.000 nascidos vivos (denom = SINASC same year).
  - Óbitos em < 1 ano:      por 1.000 nascidos vivos.
  - Internações 1-4 anos:   por 100.000 habitantes da faixa.
  - Óbitos 1-4 anos:        por 100.000 habitantes da faixa.
  - Total < 5 anos: numerator = soma das duas faixas;
        denom = nascidos vivos + população 1-4 anos é incoerente, então
        usamos população 0-4 anos (estimativa IBGE) como denominador, e
        a taxa é por 100.000 habitantes.

Rate columns produced:
  - taxa_int_menor_1_por_1000NV
  - taxa_obt_menor_1_por_1000NV
  - taxa_int_1a4_por_100k
  - taxa_obt_1a4_por_100k
  - taxa_int_menor_5_por_100k
  - taxa_obt_menor_5_por_100k
"""

from __future__ import annotations

import pandas as pd

KEY = ["ano", "uf_code", "uf_sigla", "regiao"]


def _wide(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Pivot long faixa table -> wide with one column per faixa."""
    if df.empty:
        return pd.DataFrame(columns=KEY + ["menor_1_ano", "1_a_4_anos"])
    w = df.pivot_table(index=KEY, columns="faixa", values=value_col, aggfunc="sum", fill_value=0)
    w = w.reset_index()
    for c in ("menor_1_ano", "1_a_4_anos"):
        if c not in w.columns:
            w[c] = 0
    return w


def build_indicator_table(
    sih: pd.DataFrame,
    sim: pd.DataFrame,
    sinasc: pd.DataFrame,
    pop: pd.DataFrame,
) -> pd.DataFrame:
    """Merge counts + denominators and compute all indicators per (ano x UF)."""
    sih_w = _wide(sih, "internacoes").rename(
        columns={"menor_1_ano": "int_menor_1", "1_a_4_anos": "int_1a4"}
    )
    sim_w = _wide(sim, "obitos").rename(
        columns={"menor_1_ano": "obt_menor_1", "1_a_4_anos": "obt_1a4"}
    )
    pop_w = pop.pivot_table(
        index=["ano", "uf_code"], columns="faixa", values="populacao",
        aggfunc="sum", fill_value=0,
    ).reset_index().rename(columns={
        "menor_1_ano": "pop_menor_1",
        "1_a_4_anos": "pop_1a4",
    })

    df = sih_w.merge(sim_w, on=KEY, how="outer")
    df = df.merge(pop_w, on=["ano", "uf_code"], how="left")
    df = df.merge(sinasc.rename(columns={"nascidos_vivos": "nv"}), on=KEY, how="left")
    df = df.fillna(0)

    df["int_menor_5"] = df["int_menor_1"] + df["int_1a4"]
    df["obt_menor_5"] = df["obt_menor_1"] + df["obt_1a4"]
    df["pop_menor_5"] = df["pop_menor_1"] + df["pop_1a4"]

    def _safe_rate(num, den, mult):
        return (num / den * mult).where(den > 0, other=pd.NA)

    df["taxa_int_menor_1_por_1000NV"] = _safe_rate(df["int_menor_1"], df["nv"], 1000)
    df["taxa_obt_menor_1_por_1000NV"] = _safe_rate(df["obt_menor_1"], df["nv"], 1000)
    df["taxa_int_1a4_por_100k"] = _safe_rate(df["int_1a4"], df["pop_1a4"], 100_000)
    df["taxa_obt_1a4_por_100k"] = _safe_rate(df["obt_1a4"], df["pop_1a4"], 100_000)
    df["taxa_int_menor_5_por_100k"] = _safe_rate(df["int_menor_5"], df["pop_menor_5"], 100_000)
    df["taxa_obt_menor_5_por_100k"] = _safe_rate(df["obt_menor_5"], df["pop_menor_5"], 100_000)

    cols = KEY + [
        "int_menor_1", "int_1a4", "int_menor_5",
        "obt_menor_1", "obt_1a4", "obt_menor_5",
        "nv", "pop_menor_1", "pop_1a4", "pop_menor_5",
        "taxa_int_menor_1_por_1000NV",
        "taxa_obt_menor_1_por_1000NV",
        "taxa_int_1a4_por_100k",
        "taxa_obt_1a4_por_100k",
        "taxa_int_menor_5_por_100k",
        "taxa_obt_menor_5_por_100k",
    ]
    return df[cols].sort_values(["ano", "uf_sigla"]).reset_index(drop=True)


def aggregate_to_region(df_uf: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the UF-level indicator table to the 5 regions + Brasil totals."""
    counts = ["int_menor_1", "int_1a4", "int_menor_5",
              "obt_menor_1", "obt_1a4", "obt_menor_5",
              "nv", "pop_menor_1", "pop_1a4", "pop_menor_5"]

    by_region = df_uf.groupby(["ano", "regiao"])[counts].sum().reset_index()
    by_brasil = df_uf.groupby(["ano"])[counts].sum().reset_index()
    by_brasil["regiao"] = "Brasil"

    out = pd.concat([by_region, by_brasil], ignore_index=True)
    out["taxa_int_menor_1_por_1000NV"] = (out["int_menor_1"] / out["nv"]).where(out["nv"] > 0) * 1000
    out["taxa_obt_menor_1_por_1000NV"] = (out["obt_menor_1"] / out["nv"]).where(out["nv"] > 0) * 1000
    out["taxa_int_1a4_por_100k"] = (out["int_1a4"] / out["pop_1a4"]).where(out["pop_1a4"] > 0) * 100_000
    out["taxa_obt_1a4_por_100k"] = (out["obt_1a4"] / out["pop_1a4"]).where(out["pop_1a4"] > 0) * 100_000
    out["taxa_int_menor_5_por_100k"] = (out["int_menor_5"] / out["pop_menor_5"]).where(out["pop_menor_5"] > 0) * 100_000
    out["taxa_obt_menor_5_por_100k"] = (out["obt_menor_5"] / out["pop_menor_5"]).where(out["pop_menor_5"] > 0) * 100_000
    return out.sort_values(["regiao", "ano"]).reset_index(drop=True)
